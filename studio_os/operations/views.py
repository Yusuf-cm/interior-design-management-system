from django.db import transaction
from django.shortcuts import get_object_or_404
from django.db.models import F, Q
from django.utils import timezone
from rest_framework import serializers, status
from rest_framework.exceptions import APIException, PermissionDenied, ValidationError
from rest_framework.generics import ListCreateAPIView, ListAPIView
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Activity, Customer, Lead, Membership, NextAction
from studio_os.domain.policies import DomainError, LeadStatus, transition_lead


def organization_for(request):
    raw = request.headers.get("X-Organization-ID", "")
    try:
        org_id = int(raw)
    except (TypeError, ValueError):
        raise ValidationError({"organization": "Select an organization"})
    membership = Membership.objects.filter(
        organization_id=org_id, user=request.user, active=True
    ).first()
    if not membership:
        raise PermissionDenied("Organization unavailable")
    return membership.organization, membership


class LeadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lead
        fields = ["id", "customer", "brief", "status", "version", "created_at"]
        read_only_fields = ["id", "status", "version", "created_at"]


class LeadListCreateView(ListCreateAPIView):
    serializer_class = LeadSerializer

    def get_queryset(self):
        org, membership = organization_for(self.request)
        if membership.role == Membership.Role.FIELD:
            raise PermissionDenied("Inquiry directory unavailable")
        return Lead.objects.filter(organization=org).order_by("-created_at")

    @transaction.atomic
    def perform_create(self, serializer):
        org, membership = organization_for(self.request)
        if membership.role == Membership.Role.FIELD:
            raise PermissionDenied("Field staff cannot create leads")
        customer = serializer.validated_data["customer"]
        if customer.organization_id != org.id:
            raise PermissionDenied("Customer unavailable")
        lead = serializer.save(organization=org)
        Activity.objects.create(organization=org, actor=self.request.user, lead=lead, kind="LEAD_CREATED")
        NextAction.objects.create(
            organization=org, lead=lead, assignee=self.request.user,
            title="Respond to new inquiry", due_at=timezone.now(),
        )


class ActionSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source="lead.customer.name", read_only=True)

    class Meta:
        model = NextAction
        fields = ["id", "lead", "customer_name", "title", "due_at", "done", "cancelled", "assignee", "version"]


class DailyQueueView(ListAPIView):
    serializer_class = ActionSerializer

    def get_queryset(self):
        org, membership = organization_for(self.request)
        qs = NextAction.objects.filter(organization=org, done=False, cancelled=False).select_related("lead__customer")
        if membership.role == Membership.Role.FIELD:
            qs = qs.filter(assignee=self.request.user)
        # Today's queue includes overdue and undated work, not future reminders.
        tomorrow = timezone.localtime(timezone.now()).replace(hour=0, minute=0, second=0, microsecond=0) + timezone.timedelta(days=1)
        return qs.filter(Q(due_at__lt=tomorrow) | Q(due_at__isnull=True)).order_by(
            F("due_at").asc(nulls_last=True), "created_at", "pk",
        )



class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = ["id", "name", "email", "phone", "created_at"]
        read_only_fields = ["id", "created_at"]


class CustomerListCreateView(ListCreateAPIView):
    """Tenant-scoped customer directory; company ownership is never client-supplied."""
    serializer_class = CustomerSerializer

    def get_queryset(self):
        org, membership = organization_for(self.request)
        if membership.role == Membership.Role.FIELD:
            raise PermissionDenied("Customer directory unavailable")
        return Customer.objects.filter(organization=org).order_by("-created_at")

    @transaction.atomic
    def perform_create(self, serializer):
        org, membership = organization_for(self.request)
        if membership.role == Membership.Role.FIELD:
            raise PermissionDenied("Field staff cannot create customers")
        serializer.save(organization=org)



class LeadDetailView(APIView):
    def get(self, request, pk):
        org, membership = organization_for(request)
        if membership.role == Membership.Role.FIELD:
            raise PermissionDenied("Inquiry details unavailable")
        lead = get_object_or_404(Lead, pk=pk, organization=org)
        return Response({
            **LeadSerializer(lead).data,
            "actions": ActionSerializer(lead.actions.filter(organization=org), many=True).data,
            "activities": list(Activity.objects.filter(organization=org, lead=lead)
                               .order_by("created_at").values("id", "kind", "details", "created_at")),
        })


class CompletionSerializer(serializers.Serializer):
    expected_version = serializers.IntegerField(min_value=1)
    note = serializers.CharField(max_length=4000)
    follow_up_title = serializers.CharField(max_length=180, required=False)
    follow_up_due_at = serializers.DateTimeField(required=False)

    def validate(self, attrs):
        if ("follow_up_title" in attrs) != ("follow_up_due_at" in attrs):
            raise serializers.ValidationError("Supply both follow-up title and due date")
        if attrs.get("follow_up_due_at") and attrs["follow_up_due_at"] <= timezone.now():
            raise serializers.ValidationError("Follow-up must be in the future")
        return attrs


class ActionCompleteView(APIView):
    @transaction.atomic
    def post(self, request, pk):
        org, membership = organization_for(request)
        actions = NextAction.objects.filter(organization=org)
        if membership.role == Membership.Role.FIELD:
            actions = actions.filter(assignee=request.user)
        action = lock_action(actions, pk, org)
        # Repeated completion is harmless and never creates duplicate follow-ups.
        if action.done:
            return Response(ActionSerializer(action).data)
        if action.cancelled:
            raise Conflict("This action was cancelled")
        serializer = CompletionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        update_versioned(action, data["expected_version"], done=True)
        Activity.objects.create(
            organization=org, actor=request.user, lead=action.lead,
            kind="ACTION_COMPLETED", details={"action_id": action.pk, "note": data["note"]},
        )
        if "follow_up_title" in data:
            require_open_lead(action.lead)
            if not Membership.objects.filter(
                organization=org, user_id=action.assignee_id, active=True,
            ).exists():
                raise ValidationError({"assignee": "Reassign this action to active staff before scheduling a follow-up"})
            NextAction.objects.create(
                organization=org, lead=action.lead, assignee=action.assignee,
                title=data["follow_up_title"], due_at=data["follow_up_due_at"],
            )
        return Response(ActionSerializer(action).data)


class Conflict(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "Record changed; refresh before trying again"
    default_code = "conflict"


def lock_action(queryset, pk, org):
    # All action mutations lock their lead first, matching status changes and creation.
    reference = get_object_or_404(queryset, pk=pk)
    get_object_or_404(Lead.objects.select_for_update(), pk=reference.lead_id, organization=org)
    return get_object_or_404(queryset.select_for_update(), pk=pk)


def update_versioned(record, expected_version, **changes):
    """Compare-and-swap also detects stale writes without database row-lock support."""
    changed = type(record).objects.filter(pk=record.pk, version=expected_version).update(
        **changes, version=F("version") + 1,
    )
    if not changed:
        raise Conflict()
    record.refresh_from_db()


def require_open_lead(lead):
    if lead.status in {Lead.Status.LOST, Lead.Status.WON}:
        raise Conflict("Closed inquiries cannot receive new follow-up actions")


def require_office_member(membership):
    if membership.role == Membership.Role.FIELD:
        raise PermissionDenied("Inquiry management unavailable")


class LeadTransitionSerializer(serializers.Serializer):
    expected_version = serializers.IntegerField(min_value=1)
    status = serializers.ChoiceField(choices=[
        Lead.Status.CONTACTED, Lead.Status.QUALIFIED, Lead.Status.DORMANT, Lead.Status.LOST,
    ])
    note = serializers.CharField(max_length=4000)


class LeadTransitionView(APIView):
    @transaction.atomic
    def post(self, request, pk):
        org, membership = organization_for(request)
        require_office_member(membership)
        lead = get_object_or_404(Lead.objects.select_for_update(), organization=org, pk=pk)
        serializer = LeadTransitionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        if lead.version != data["expected_version"]:
            raise Conflict()
        previous = lead.status
        try:
            target = transition_lead(LeadStatus(previous), LeadStatus(data["status"]))
        except DomainError as exc:
            raise ValidationError({"status": str(exc)})
        update_versioned(lead, data["expected_version"], status=target.value)
        cancelled = 0
        if lead.status == Lead.Status.LOST:
            cancelled = lead.actions.filter(organization=org, done=False, cancelled=False).update(
                cancelled=True, version=F("version") + 1,
            )
        Activity.objects.create(
            organization=org, actor=request.user, lead=lead, kind="LEAD_STATUS_CHANGED",
            details={"before": previous, "after": lead.status, "note": data["note"],
                     "cancelled_actions": cancelled},
        )
        return Response(LeadSerializer(lead).data)


class ActionPlanSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=180)
    due_at = serializers.DateTimeField(allow_null=True)
    assignee = serializers.IntegerField(min_value=1, required=False)

    def validate_assignee(self, value):
        if not Membership.objects.filter(
            organization=self.context["organization"], user_id=value, active=True,
        ).exists():
            raise serializers.ValidationError("Assignee unavailable")
        return value


class ActionCreateView(APIView):
    @transaction.atomic
    def post(self, request, pk):
        org, membership = organization_for(request)
        require_office_member(membership)
        lead = get_object_or_404(Lead.objects.select_for_update(), organization=org, pk=pk)
        require_open_lead(lead)
        serializer = ActionPlanSerializer(data=request.data, context={"organization": org})
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        assignee_id = data.get("assignee", request.user.pk)
        if assignee_id != request.user.pk and membership.role not in {
            Membership.Role.OWNER, Membership.Role.COORDINATOR,
        }:
            raise PermissionDenied("Only owners and coordinators can assign other staff")
        action = NextAction.objects.create(
            organization=org, lead=lead, title=data["title"], due_at=data["due_at"],
            assignee_id=assignee_id,
        )
        Activity.objects.create(
            organization=org, actor=request.user, lead=lead, kind="ACTION_CREATED",
            details={"action_id": action.pk, "assignee": assignee_id,
                     "title": action.title, "due_at": action.due_at.isoformat() if action.due_at else None},
        )
        return Response(ActionSerializer(action).data, status=status.HTTP_201_CREATED)


class ActionUpdateSerializer(ActionPlanSerializer):
    expected_version = serializers.IntegerField(min_value=1)
    note = serializers.CharField(max_length=4000)


class ActionUpdateView(APIView):
    @transaction.atomic
    def patch(self, request, pk):
        org, membership = organization_for(request)
        if membership.role not in {Membership.Role.OWNER, Membership.Role.COORDINATOR}:
            raise PermissionDenied("Only owners and coordinators can change planned actions")
        action = lock_action(NextAction.objects.filter(organization=org), pk, org)
        if action.done or action.cancelled:
            raise Conflict("Completed or cancelled actions cannot be rescheduled")
        serializer = ActionUpdateSerializer(
            data=request.data, partial=True, context={"organization": org},
        )
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        # partial=True allows omitted editable fields, but not concurrency/audit controls.
        for key in ("expected_version", "note"):
            if key not in data:
                raise ValidationError({key: "This field is required"})
        changes = {key: data[key] for key in ("title", "due_at") if key in data}
        if "assignee" in data:
            changes["assignee_id"] = data["assignee"]
        if not changes:
            raise ValidationError("Supply a title, due date or assignee to change")
        before = ActionSerializer(action).data
        update_versioned(action, data["expected_version"], **changes)
        Activity.objects.create(
            organization=org, actor=request.user, lead=action.lead, kind="ACTION_UPDATED",
            details={"action_id": action.pk, "before": before,
                     "after": ActionSerializer(action).data, "note": data["note"]},
        )
        return Response(ActionSerializer(action).data)
