"""Internal execution planning from recorded approval; no purchasing or contractor hiring."""
from django.db import transaction
from django.db.models import F
from django.shortcuts import get_object_or_404
from rest_framework import serializers, status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Activity, Lead, Membership, NextAction, Project, Quote, QuoteEvent, WorkItem, ScopeChange
from .views import Conflict, organization_for, update_versioned
from .workflow_tasks import plan_task, settle_task


def is_manager(member):
    return member.role in {Membership.Role.OWNER, Membership.Role.COORDINATOR}


def require_manager(member):
    if not is_manager(member):
        raise PermissionDenied("Owners and coordinators manage project plans")


def active_assignee(org, user_id, *, office=False):
    if user_id is None:
        return None
    members = Membership.objects.filter(organization=org, user_id=user_id, active=True, user__is_active=True)
    if office:
        members = members.filter(role__in=[Membership.Role.OWNER, Membership.Role.COORDINATOR])
    member = members.select_related("user").first()
    if not member:
        raise ValidationError({"assignee": "Choose active staff from this studio"})
    return member.user


class WorkItemSerializer(serializers.ModelSerializer):
    assignee_name = serializers.SerializerMethodField()

    class Meta:
        model = WorkItem
        fields = ["id", "project", "title", "description", "assignee", "assignee_name", "due_at",
                  "status", "blocker_reason", "version", "created_at"]
        read_only_fields = fields

    def get_assignee_name(self, obj):
        return (obj.assignee.get_full_name() or obj.assignee.username) if obj.assignee else "Unassigned"


class ProjectSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source="lead.customer.name", read_only=True)
    open_items = serializers.SerializerMethodField()
    blocked_items = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = ["id", "title", "customer_name", "status", "owner", "start_date", "target_date",
                  "open_items", "blocked_items", "version", "created_at"]
        read_only_fields = fields

    def visible_items(self, obj):
        items = obj.work_items.filter(organization=obj.organization)
        if self.context["membership"].role == Membership.Role.FIELD:
            items = items.filter(assignee=self.context["user"])
        return items

    def get_open_items(self, obj):
        return self.visible_items(obj).exclude(status__in=[WorkItem.Status.DONE, WorkItem.Status.CANCELLED]).count()

    def get_blocked_items(self, obj):
        return self.visible_items(obj).filter(status=WorkItem.Status.BLOCKED).count()


def project_data(project, request, membership, *, detail=False):
    data = ProjectSerializer(project, context={"membership": membership, "user": request.user}).data
    items = WorkItem.objects.filter(organization=project.organization, project=project).select_related("assignee")
    if membership.role == Membership.Role.FIELD:
        items = items.filter(assignee=request.user)
    else:
        revision = project.accepted_revision
        data["lead"] = project.lead_id
        data["accepted_revision"] = revision.pk
        data["quote"] = revision.quote_id
        data["scope"] = revision.scope_snapshot
        data["currency"] = revision.currency
        data["accepted_total"] = str(revision.total)
        if detail:
            data["scope_changes"] = ScopeChangeSerializer(project.scope_changes.filter(organization=project.organization).order_by("pk"), many=True).data
    if detail:
        data["work_items"] = WorkItemSerializer(items.order_by("due_at", "pk"), many=True).data
        if membership.role != Membership.Role.FIELD:
            data["history"] = list(Activity.objects.filter(
                organization=project.organization, details__project_id=project.pk
            ).order_by("created_at", "pk").values("id", "kind", "details", "created_at"))
    return data


def project_queryset(org, member, user):
    projects = Project.objects.filter(organization=org).select_related("lead__customer", "accepted_revision")
    if member.role == Membership.Role.FIELD:
        projects = projects.filter(work_items__organization=org, work_items__assignee=user).distinct()
    return projects


def project_for(request, pk, *, lock=False):
    org, member = organization_for(request)
    qs = project_queryset(org, member, request.user)
    # Keep row locks off outer joins/distinct. Scope first, then lock the project row.
    reference = get_object_or_404(qs, pk=pk)
    project = get_object_or_404(Project.objects.select_for_update(), pk=reference.pk, organization=org) if lock else reference
    return org, member, project


def audit(request, project, kind, note, **details):
    Activity.objects.create(
        organization=project.organization, actor=request.user, lead=project.lead, kind=kind,
        details={"project_id": project.pk, "note": note, **details})


class ProjectPlanInput(serializers.Serializer):
    expected_version = serializers.IntegerField(min_value=1)
    title = serializers.CharField(max_length=180)
    owner = serializers.IntegerField(min_value=1)
    start_date = serializers.DateField(allow_null=True, required=False)
    target_date = serializers.DateField(allow_null=True, required=False)
    note = serializers.CharField(max_length=4000)

    def validate(self, data):
        start, end = data.get("start_date"), data.get("target_date")
        if start and end and end < start:
            raise serializers.ValidationError("Target date must not precede the planned start")
        return data


class ProjectCreateView(APIView):
    @transaction.atomic
    def post(self, request, pk):
        org, member = organization_for(request)
        if member.role != Membership.Role.OWNER:
            raise PermissionDenied("Only owners can convert recorded customer approval into a project")
        reference = get_object_or_404(Quote, pk=pk, organization=org)
        lead = get_object_or_404(Lead.objects.select_for_update(), pk=reference.assessment.consultation.lead_id, organization=org)
        quote = get_object_or_404(Quote.objects.select_for_update(), pk=pk, organization=org)
        if quote.status != Quote.Status.ACCEPTED or lead.status != Lead.Status.WON:
            raise Conflict("Record customer approval of this revision before project planning")
        if not QuoteEvent.objects.filter(organization=org, revision_id=quote.current_revision_id,
                                         kind=QuoteEvent.Kind.ACCEPTED).exists():
            raise Conflict("The accepted revision has no recorded customer approval")
        existing = Project.objects.filter(organization=org, accepted_revision_id=quote.current_revision_id).first()
        if existing:
            return Response(project_data(existing, request, member, detail=True))
        if Project.objects.filter(lead=lead).exists():
            raise Conflict("This inquiry already has a project")
        serializer = ProjectPlanInput(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        if data["expected_version"] != quote.version:
            raise Conflict()
        project_owner = active_assignee(org, data["owner"], office=True)
        project = Project.objects.create(
            organization=org, lead=lead, accepted_revision=quote.current_revision,
            title=data["title"], owner=project_owner, start_date=data.get("start_date"), target_date=data.get("target_date"))
        settle_task(org, f"quote:{quote.pk}:project")
        plan_task(org, lead, f"project:{project.pk}:plan", "Plan project work", project_owner)
        audit(request, project, "PROJECT_PLANNED", data["note"], accepted_revision_id=quote.current_revision_id)
        return Response(project_data(project, request, member, detail=True), status=status.HTTP_201_CREATED)


class ProjectListView(APIView):
    def get(self, request):
        org, member = organization_for(request)
        projects = project_queryset(org, member, request.user).order_by("-created_at", "-pk")
        return Response([project_data(project, request, member) for project in projects])


class ProjectDetailView(APIView):
    def get(self, request, pk):
        _, member, project = project_for(request, pk)
        return Response(project_data(project, request, member, detail=True))


class ProjectCommandInput(serializers.Serializer):
    expected_version = serializers.IntegerField(min_value=1)
    command = serializers.ChoiceField(choices=["start", "pause", "resume", "cancel"])
    note = serializers.CharField(max_length=4000)


class ProjectCommandView(APIView):
    @transaction.atomic
    def post(self, request, pk):
        org, member, project = project_for(request, pk, lock=True)
        require_manager(member)
        serializer = ProjectCommandInput(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        command = data["command"]
        targets = {"start": ({"PLANNED"}, "ACTIVE"), "pause": ({"ACTIVE"}, "PAUSED"),
                   "resume": ({"PAUSED"}, "ACTIVE"), "cancel": ({"PLANNED", "ACTIVE", "PAUSED"}, "CANCELLED")}
        allowed, target = targets[command]
        if project.version != data["expected_version"]:
            raise Conflict()
        if project.status not in allowed:
            raise Conflict("This project cannot make that transition")
        previous = project.status
        update_versioned(project, data["expected_version"], status=target)
        settle_task(org, f"project:{project.pk}:plan", cancelled=command=="cancel")
        if command == "pause":
            plan_task(org, project.lead, f"project:{project.pk}:pause", "Review paused project", project.owner)
        else:
            settle_task(org, f"project:{project.pk}:pause", cancelled=command=="cancel")
        if command == "cancel":
            pending = ScopeChange.objects.filter(organization=org, project=project, status="PROPOSED")
            for change in pending:
                update_versioned(change, change.version, status="WITHDRAWN", decision_reference="Project cancelled")
                settle_task(org, f"project:{project.pk}:change-{change.pk}", cancelled=True)
                audit(request, project, "SCOPE_CHANGE_DECIDED", data["note"], scope_change_id=change.pk,
                      after="WITHDRAWN", reference="Project cancelled")
            items = WorkItem.objects.filter(organization=org, project=project).exclude(
                status__in=[WorkItem.Status.DONE, WorkItem.Status.CANCELLED])
            items.update(status=WorkItem.Status.CANCELLED, version=F("version")+1)
            NextAction.objects.filter(organization=org, work_item__project=project, done=False, cancelled=False).update(
                cancelled=True, version=F("version")+1)
        audit(request, project, "PROJECT_STATUS_CHANGED", data["note"], before=previous, after=target)
        return Response(project_data(project, request, member, detail=True))


def sync_work_action(work):
    origin = f"work:{work.pk}:execute"
    if work.status in {WorkItem.Status.DONE, WorkItem.Status.CANCELLED}:
        settle_task(work.organization, origin, cancelled=work.status==WorkItem.Status.CANCELLED)
    else:
        task = plan_task(work.organization, work.project.lead, origin,
                         (("Blocked: " if work.status==WorkItem.Status.BLOCKED else "")+work.title)[:180],
                         work.assignee, due_at=work.due_at)
        NextAction.objects.filter(pk=task.pk).update(work_item=work)


class WorkInput(serializers.Serializer):
    title = serializers.CharField(max_length=180)
    description = serializers.CharField(max_length=12000, allow_blank=True, required=False, default="")
    assignee = serializers.IntegerField(min_value=1, allow_null=True)
    due_at = serializers.DateTimeField(allow_null=True)
    note = serializers.CharField(max_length=4000)


class WorkCreateView(APIView):
    @transaction.atomic
    def post(self, request, pk):
        org, member, project = project_for(request, pk, lock=True)
        require_manager(member)
        if project.status == Project.Status.CANCELLED:
            raise Conflict("Cancelled projects cannot receive new work")
        serializer = WorkInput(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        assignee = active_assignee(org, data["assignee"])
        work = WorkItem.objects.create(
            organization=org, project=project, title=data["title"], description=data["description"],
            assignee=assignee, due_at=data["due_at"])
        sync_work_action(work)
        audit(request, project, "WORK_ITEM_CREATED", data["note"], work_item_id=work.pk, title=work.title)
        return Response(WorkItemSerializer(work).data, status=status.HTTP_201_CREATED)


def work_for(request, pk, *, lock=False, assigned_only=False):
    org, member = organization_for(request)
    qs = WorkItem.objects.filter(organization=org).select_related("project", "assignee")
    if member.role == Membership.Role.FIELD or (assigned_only and not is_manager(member)):
        qs = qs.filter(assignee=request.user)
    reference = get_object_or_404(qs, pk=pk)
    project = get_object_or_404(Project.objects.select_for_update(), pk=reference.project_id, organization=org) if lock else reference.project
    work = get_object_or_404(qs.select_for_update(of=("self",)), pk=pk) if lock else reference
    return org, member, project, work


class WorkEditInput(WorkInput):
    expected_version = serializers.IntegerField(min_value=1)


class WorkDetailView(APIView):
    def get(self, request, pk):
        _, member, project, work = work_for(request, pk)
        return Response({"work_item": WorkItemSerializer(work).data,
                         "project": project_data(project, request, member)})

    @transaction.atomic
    def patch(self, request, pk):
        org, member, project, work = work_for(request, pk, lock=True)
        require_manager(member)
        if project.status == Project.Status.CANCELLED or work.status in {WorkItem.Status.DONE, WorkItem.Status.CANCELLED}:
            raise Conflict("Reopen unfinished planning before changing this work")
        serializer = WorkEditInput(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        for key in ("expected_version", "note"):
            if key not in data:
                raise ValidationError({key: "This field is required"})
        changes = {key:data[key] for key in ("title", "description", "due_at") if key in data}
        if "assignee" in data:
            changes["assignee"] = active_assignee(org, data["assignee"])
        if not changes:
            raise ValidationError("Supply work details to change")
        before = WorkItemSerializer(work).data
        update_versioned(work, data["expected_version"], **changes)
        sync_work_action(work)
        audit(request, project, "WORK_ITEM_UPDATED", data["note"], work_item_id=work.pk,
              before=before, after=WorkItemSerializer(work).data)
        return Response(WorkItemSerializer(work).data)


class WorkCommandInput(serializers.Serializer):
    expected_version = serializers.IntegerField(min_value=1)
    command = serializers.ChoiceField(choices=["start", "block", "unblock", "done", "cancel", "reopen"])
    note = serializers.CharField(max_length=4000)


class WorkCommandView(APIView):
    @transaction.atomic
    def post(self, request, pk):
        org, member, project, work = work_for(request, pk, lock=True, assigned_only=True)
        serializer = WorkCommandInput(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        command = data["command"]
        if command in {"cancel", "reopen"}:
            require_manager(member)
        if project.status == Project.Status.CANCELLED:
            raise Conflict("Cancelled project work cannot progress")
        if command in {"start", "unblock", "done"} and project.status != Project.Status.ACTIVE:
            raise Conflict("Activate or resume the project before progressing work")
        targets = {"start": ({"TODO"}, "IN_PROGRESS"), "block": ({"TODO", "IN_PROGRESS"}, "BLOCKED"),
                   "unblock": ({"BLOCKED"}, "IN_PROGRESS"), "done": ({"IN_PROGRESS"}, "DONE"),
                   "cancel": ({"TODO", "IN_PROGRESS", "BLOCKED"}, "CANCELLED"),
                   "reopen": ({"DONE", "CANCELLED"}, "TODO")}
        allowed, target = targets[command]
        if work.version != data["expected_version"]:
            raise Conflict()
        if work.status not in allowed:
            raise Conflict("This work item cannot make that transition")
        previous = work.status
        update_versioned(work, data["expected_version"], status=target,
                         blocker_reason=data["note"] if command=="block" else "")
        sync_work_action(work)
        audit(request, project, "WORK_ITEM_STATUS_CHANGED", data["note"], work_item_id=work.pk,
              before=previous, after=target)
        return Response(WorkItemSerializer(work).data)


class ScopeChangeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScopeChange
        fields = ["id", "project", "title", "description", "estimated_delta", "schedule_days",
                  "status", "decision_reference", "version", "created_at"]
        read_only_fields = fields


class ScopeChangeInput(serializers.Serializer):
    title = serializers.CharField(max_length=180)
    description = serializers.CharField(max_length=12000)
    estimated_delta = serializers.DecimalField(max_digits=18, decimal_places=2)
    schedule_days = serializers.IntegerField(min_value=-3650, max_value=3650)
    note = serializers.CharField(max_length=4000)


class ScopeChangeCreateView(APIView):
    @transaction.atomic
    def post(self, request, pk):
        org, member, project = project_for(request, pk, lock=True)
        require_manager(member)
        if project.status == Project.Status.CANCELLED:
            raise Conflict("Cancelled projects cannot receive scope changes")
        serializer = ScopeChangeInput(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        note = data.pop("note")
        change = ScopeChange.objects.create(organization=org, project=project, **data)
        plan_task(org, project.lead, f"project:{project.pk}:change-{change.pk}",
                  "Review scope change: " + change.title[:150], project.owner)
        audit(request, project, "SCOPE_CHANGE_PROPOSED", note, scope_change_id=change.pk,
              proposal=ScopeChangeSerializer(change).data)
        return Response(ScopeChangeSerializer(change).data, status=status.HTTP_201_CREATED)


class ScopeDecisionInput(serializers.Serializer):
    expected_version = serializers.IntegerField(min_value=1)
    command = serializers.ChoiceField(choices=["approve", "reject", "withdraw"])
    reference = serializers.CharField(max_length=500)
    note = serializers.CharField(max_length=4000)


class ScopeChangeDecisionView(APIView):
    @transaction.atomic
    def post(self, request, pk, change_pk):
        org, member, project = project_for(request, pk, lock=True)
        if member.role != Membership.Role.OWNER:
            raise PermissionDenied("Only owners record scope-change decisions")
        change = get_object_or_404(ScopeChange.objects.select_for_update(), pk=change_pk,
                                  project=project, organization=org)
        serializer = ScopeDecisionInput(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        if project.status == Project.Status.CANCELLED or change.status != ScopeChange.Status.PROPOSED:
            raise Conflict("This scope change is no longer open for review")
        target = {"approve":"APPROVED", "reject":"REJECTED", "withdraw":"WITHDRAWN"}[data["command"]]
        update_versioned(change, data["expected_version"], status=target, decision_reference=data["reference"])
        settle_task(org, f"project:{project.pk}:change-{change.pk}", cancelled=target!="APPROVED")
        audit(request, project, "SCOPE_CHANGE_DECIDED", data["note"], scope_change_id=change.pk,
              after=target, reference=data["reference"])
        return Response(ScopeChangeSerializer(change).data)
