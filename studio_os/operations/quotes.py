"""Quotation drafts and recorded customer decisions; no delivery or agreement signing."""
from decimal import Decimal
from django.db import transaction
from django.db.models import F, Q
from django.utils import timezone
from django.shortcuts import get_object_or_404
from rest_framework import serializers, status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView
from studio_os.domain.policies import DomainError
from studio_os.domain.pricing import calculate_estimate
from .models import Activity, Assessment, Lead, Membership, Project, Quote, QuoteRevision, QuoteEvent
from .views import Conflict, organization_for, require_office_member, require_open_lead, update_versioned
from .workflow_tasks import plan_task, settle_task


class QuoteLineSerializer(serializers.Serializer):
    description = serializers.CharField(max_length=300)
    quantity = serializers.DecimalField(max_digits=12, decimal_places=3, min_value=Decimal("0.001"))
    unit_price = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0"))


class QuoteInputSerializer(serializers.Serializer):
    expected_assessment_version = serializers.IntegerField(min_value=1)
    items = QuoteLineSerializer(many=True, min_length=1, max_length=100)
    discount = serializers.DecimalField(max_digits=18, decimal_places=2,
                                        min_value=Decimal("0"), default=Decimal("0"))
    tax_rate = serializers.DecimalField(max_digits=7, decimal_places=6, min_value=Decimal("0"),
                                        max_value=Decimal("1"), default=Decimal("0"))

    def validate(self, data):
        try:
            data["calculated"] = calculate_estimate(data["items"], data["discount"], data["tax_rate"])
        except DomainError as exc:
            raise serializers.ValidationError(str(exc))
        return data


class RevisionInputSerializer(QuoteInputSerializer):
    expected_version = serializers.IntegerField(min_value=1)
    note = serializers.CharField(max_length=4000)


class QuoteRevisionSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuoteRevision
        fields = ["id", "number", "assessment_version", "scope_snapshot", "notes_snapshot", "measurements_snapshot",
                  "provisional_reason_snapshot", "currency", "items", "subtotal", "discount",
                  "tax_rate", "tax", "total", "created_at"]
        read_only_fields = fields


class QuoteSerializer(serializers.ModelSerializer):
    current_revision = QuoteRevisionSerializer(read_only=True)
    source_current = serializers.SerializerMethodField()
    customer_name = serializers.CharField(source="assessment.consultation.lead.customer.name", read_only=True)
    lead = serializers.IntegerField(source="assessment.consultation.lead_id", read_only=True)
    project_id = serializers.SerializerMethodField()
    customer_follow_up = serializers.SerializerMethodField()

    class Meta:
        model = Quote
        fields = ["id", "assessment", "lead", "customer_name", "currency", "status", "version", "source_current",
                  "current_revision", "project_id", "customer_follow_up", "created_at"]
        read_only_fields = fields

    def get_customer_follow_up(self, obj):
        from .models import NextAction
        action = NextAction.objects.filter(organization=obj.organization, origin_key=f"quote:{obj.pk}:reply",
            done=False, cancelled=False).first()
        if action is None:
            return None
        return {"id": action.pk, "due_at": action.due_at.isoformat() if action.due_at else None,
                "version": action.version, "assignee_id": action.assignee_id}

    def get_project_id(self, obj):
        return Project.objects.filter(organization=obj.organization, accepted_revision_id=obj.current_revision_id).values_list("pk", flat=True).first()

    def get_source_current(self, obj):
        return (obj.assessment.status == Assessment.Status.READY and obj.current_revision is not None
                and obj.current_revision.assessment_version == obj.assessment.version)


def ready_source(assessment, expected_version):
    if assessment.status != Assessment.Status.READY:
        raise Conflict("Assessment must be ready before drafting or reviewing an estimate")
    if assessment.version != expected_version:
        raise Conflict("Assessment changed; review the current observations first")


def record_revision(quote, assessment, number, calculated):
    return QuoteRevision.objects.create(
        organization=quote.organization, quote=quote, number=number,
        assessment_version=assessment.version, scope_snapshot=assessment.scope, notes_snapshot=assessment.notes,
        measurements_snapshot=assessment.measurements,
        provisional_reason_snapshot=assessment.provisional_reason, currency=quote.currency,
        **calculated,
    )


def audit(request, quote, kind, note, before=None):
    Activity.objects.create(
        organization=quote.organization, actor=request.user, lead=quote.assessment.consultation.lead,
        kind=kind, details={"quote_id": quote.pk, "revision_id": quote.current_revision_id,
                           "note": note, "before": before, "after": QuoteSerializer(quote).data},
    )


def locked_quote(request, pk):
    org, membership = organization_for(request)
    require_office_member(membership)
    reference = get_object_or_404(Quote, pk=pk, organization=org)
    lead = get_object_or_404(Lead.objects.select_for_update(),
                             pk=reference.assessment.consultation.lead_id, organization=org)
    assessment = get_object_or_404(Assessment.objects.select_for_update(),
                                   pk=reference.assessment_id, organization=org)
    quote = get_object_or_404(Quote.objects.select_for_update(), pk=pk, organization=org)
    quote.assessment = assessment
    require_open_lead(lead)
    return org, membership, lead, assessment, quote


class QuoteCreateView(APIView):
    @transaction.atomic
    def post(self, request, pk):
        org, membership = organization_for(request)
        require_office_member(membership)
        ref = get_object_or_404(Assessment, organization=org, pk=pk)
        lead = get_object_or_404(Lead.objects.select_for_update(), pk=ref.consultation.lead_id, organization=org)
        assessment = get_object_or_404(Assessment.objects.select_for_update(), organization=org, pk=pk)
        require_open_lead(lead)
        serializer = QuoteInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        ready_source(assessment, data["expected_assessment_version"])
        if Quote.objects.filter(assessment=assessment).exists():
            raise Conflict("An estimate already exists; create a new revision")
        quote = Quote.objects.create(organization=org, assessment=assessment, currency=org.currency)
        revision = record_revision(quote, assessment, 1, data["calculated"])
        quote.current_revision = revision
        quote.save(update_fields=["current_revision"])
        settle_task(org, f"assessment:{assessment.pk}:estimate")
        audit(request, quote, "QUOTE_DRAFTED", "Internal quotation draft created")
        return Response(QuoteSerializer(quote).data, status=status.HTTP_201_CREATED)


class QuoteDetailView(APIView):
    def get(self, request, pk):
        org, membership = organization_for(request)
        require_office_member(membership)
        quote = get_object_or_404(Quote.objects.select_related("assessment", "current_revision"),
                                  pk=pk, organization=org)
        return Response({**QuoteSerializer(quote).data,
                         "events": QuoteEventSerializer(QuoteEvent.objects.filter(
                             organization=org, revision__quote=quote).order_by("created_at"), many=True).data,
                         "revisions": QuoteRevisionSerializer(
                             quote.revisions.filter(organization=org).order_by("number"), many=True).data})


class QuoteRevisionView(APIView):
    @transaction.atomic
    def post(self, request, pk):
        org, _, _, assessment, quote = locked_quote(request, pk)
        if quote.status in {Quote.Status.SENT, Quote.Status.ACCEPTED}:
            raise Conflict("Record a customer revision request before revising a shared quotation")
        serializer = RevisionInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        ready_source(assessment, data["expected_assessment_version"])
        if quote.version != data["expected_version"]:
            raise Conflict()
        before = QuoteSerializer(quote).data
        revision = record_revision(quote, assessment, quote.current_revision.number + 1, data["calculated"])
        update_versioned(quote, data["expected_version"], current_revision_id=revision.pk, status=Quote.Status.DRAFT)
        settle_task(org, f"quote:{quote.pk}:review", cancelled=True)
        settle_task(org, f"quote:{quote.pk}:share", cancelled=True)
        settle_task(org, f"quote:{quote.pk}:reply", cancelled=True)
        settle_task(org, f"assessment:{assessment.pk}:estimate")
        audit(request, quote, "QUOTE_REVISED", data["note"], before)
        return Response(QuoteSerializer(quote).data, status=status.HTTP_201_CREATED)


class ReviewSerializer(serializers.Serializer):
    expected_version = serializers.IntegerField(min_value=1)
    command = serializers.ChoiceField(choices=["submit", "approve", "return_to_draft"])
    note = serializers.CharField(max_length=4000)


class QuoteReviewView(APIView):
    @transaction.atomic
    def post(self, request, pk):
        org, membership, lead, assessment, quote = locked_quote(request, pk)
        serializer = ReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        if quote.version != data["expected_version"]:
            raise Conflict()
        before = QuoteSerializer(quote).data
        command = data["command"]
        if command == "return_to_draft":
            if quote.status not in {Quote.Status.REVIEW, Quote.Status.APPROVED}:
                raise Conflict("Quotation is already a draft")
            target = Quote.Status.DRAFT
            settle_task(org, f"quote:{quote.pk}:review", cancelled=True)
            settle_task(org, f"quote:{quote.pk}:share", cancelled=True)
        else:
            ready_source(assessment, quote.current_revision.assessment_version)
            if command == "submit":
                if quote.status != Quote.Status.DRAFT:
                    raise Conflict("Only drafts can be submitted for review")
                owner = Membership.objects.filter(
                    organization=org, active=True, role=Membership.Role.OWNER, user__is_active=True,
                ).select_related("user").order_by("pk").first()
                if not owner:
                    raise Conflict("Assign an active owner before submitting for review")
                target = Quote.Status.REVIEW
                plan_task(org, lead, f"quote:{quote.pk}:review", "Review quotation draft", owner.user)
            else:
                if membership.role != Membership.Role.OWNER:
                    raise PermissionDenied("Only owners can approve sharing")
                if quote.status != Quote.Status.REVIEW:
                    raise Conflict("Submit the draft for review before approval")
                target = Quote.Status.APPROVED
                settle_task(org, f"quote:{quote.pk}:review")
                plan_task(org, lead, f"quote:{quote.pk}:share", "Share approved quotation manually", request.user)
        update_versioned(quote, data["expected_version"], status=target)
        audit(request, quote, "QUOTE_" + command.upper(), data["note"], before)
        return Response(QuoteSerializer(quote).data)


class QuoteListView(APIView):
    def get(self, request):
        org, membership = organization_for(request)
        require_office_member(membership)
        quotes = Quote.objects.filter(organization=org).select_related(
            "assessment__consultation__lead__customer", "current_revision").order_by("-created_at", "-pk")
        status_filter = request.query_params.get("status")
        if status_filter:
            if status_filter not in Quote.Status.values:
                raise ValidationError({"status": "Choose a valid quotation status"})
            quotes = quotes.filter(status=status_filter)
        return Response(QuoteSerializer(quotes, many=True).data)


class QuoteEventSerializer(serializers.ModelSerializer):
    revision_number = serializers.IntegerField(source="revision.number", read_only=True)

    class Meta:
        model = QuoteEvent
        fields = ["id", "revision_number", "kind", "reference", "note", "occurred_at", "created_at"]
        read_only_fields = fields


class QuoteEventInput(serializers.Serializer):
    expected_version = serializers.IntegerField(min_value=1)
    kind = serializers.ChoiceField(choices=[QuoteEvent.Kind.SHARED, QuoteEvent.Kind.ACCEPTED,
        QuoteEvent.Kind.REJECTED, QuoteEvent.Kind.REVISION_REQUESTED])
    reference = serializers.CharField(max_length=500)
    note = serializers.CharField(max_length=4000)
    occurred_at = serializers.DateTimeField()
    follow_up_due_at = serializers.DateTimeField(required=False)

    def validate(self, data):
        from django.utils import timezone
        if data["occurred_at"] > timezone.now():
            raise serializers.ValidationError("Record events that have already happened")
        if data["kind"] == QuoteEvent.Kind.SHARED:
            if "follow_up_due_at" not in data or data["follow_up_due_at"] <= timezone.now():
                raise serializers.ValidationError("Choose a future customer follow-up time")
        elif "follow_up_due_at" in data:
            raise serializers.ValidationError("Follow-up time is only accepted for manual sharing")
        return data


class QuoteEventView(APIView):
    @transaction.atomic
    def post(self, request, pk):
        from studio_os.domain.policies import LeadStatus, transition_lead
        org, membership, lead, assessment, quote = locked_quote(request, pk)
        if membership.role != Membership.Role.OWNER:
            raise PermissionDenied("Only owners can record customer decisions and manual sharing")
        serializer = QuoteEventInput(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        if quote.version != data["expected_version"]:
            raise Conflict()
        ready_source(assessment, quote.current_revision.assessment_version)
        revision = quote.current_revision
        if data["occurred_at"] < revision.created_at.replace(second=0, microsecond=0):
            raise ValidationError("The recorded event predates this revision")
        kind = data["kind"]
        before = QuoteSerializer(quote).data
        if kind == QuoteEvent.Kind.SHARED:
            if quote.status != Quote.Status.APPROVED:
                raise Conflict("Review and approve this revision before recording manual sharing")
            if lead.status not in {Lead.Status.ASSESSED, Lead.Status.QUOTED}:
                raise Conflict("Only an assessed inquiry can have a recorded quotation")
            target = Quote.Status.SENT
            if lead.status == Lead.Status.ASSESSED:
                update_versioned(lead, lead.version, status=Lead.Status.QUOTED)
            settle_task(org, f"quote:{quote.pk}:share")
            plan_task(org, lead, f"quote:{quote.pk}:reply", "Follow up on shared quotation",
                      request.user, due_at=data["follow_up_due_at"])
        else:
            if quote.status != Quote.Status.SENT:
                raise Conflict("Record manual sharing of this revision before the customer response")
            shared = QuoteEvent.objects.filter(organization=org, revision=revision, kind=QuoteEvent.Kind.SHARED).first()
            if not shared or data["occurred_at"] < shared.occurred_at:
                raise ValidationError("The customer response cannot predate the recorded sharing")
            target = kind
            settle_task(org, f"quote:{quote.pk}:reply")
            if kind == QuoteEvent.Kind.ACCEPTED:
                if lead.status not in {Lead.Status.QUOTED, Lead.Status.DORMANT}:
                    raise Conflict("Review the inquiry stage before recording customer approval")
                transition_lead(LeadStatus(lead.status), LeadStatus.WON, accepted_quote=True)
                update_versioned(lead, lead.version, status=Lead.Status.WON)
                # All competing drafts/reviews for this inquiry are now historical.
                Quote.objects.filter(organization=org, assessment__consultation__lead=lead).exclude(pk=quote.pk).filter(
                    status__in=[Quote.Status.REVIEW, Quote.Status.APPROVED]).update(
                        status=Quote.Status.DRAFT, version=F("version")+1)
                from .models import NextAction
                NextAction.objects.filter(organization=org, lead=lead, done=False, cancelled=False).filter(
                    Q(origin_key__startswith="quote:") | Q(origin_key__startswith="assessment:") | Q(origin_key__startswith="visit:")).update(
                    cancelled=True, version=F("version")+1)
                plan_task(org, lead, f"quote:{quote.pk}:project", "Plan project from recorded customer approval", request.user)
            elif kind == QuoteEvent.Kind.REVISION_REQUESTED:
                plan_task(org, lead, f"assessment:{assessment.pk}:estimate", "Revise quotation from customer feedback", request.user)
            else:
                from .models import NextAction
                NextAction.objects.create(organization=org, lead=lead, assignee=request.user,
                    title="Review declined quotation", due_at=timezone.now())
        QuoteEvent.objects.create(
            organization=org, revision=revision, actor=request.user, kind=kind,
            reference=data["reference"], note=data["note"], occurred_at=data["occurred_at"])
        update_versioned(quote, data["expected_version"], status=target)
        audit(request, quote, "QUOTE_"+kind+"_RECORDED", data["note"], before)
        return Response(QuoteSerializer(quote).data)


class ApprovalCorrectionInput(serializers.Serializer):
    expected_version = serializers.IntegerField(min_value=1)
    reference = serializers.CharField(max_length=500)
    note = serializers.CharField(max_length=4000)
    follow_up_due_at = serializers.DateTimeField()

    def validate_follow_up_due_at(self, value):
        if value <= timezone.now():
            raise serializers.ValidationError("Choose a future customer follow-up time")
        return value


class ApprovalCorrectionView(APIView):
    @transaction.atomic
    def post(self, request, pk):
        org, member = organization_for(request)
        if member.role != Membership.Role.OWNER:
            raise PermissionDenied("Only owners can correct recorded customer approval")
        reference = get_object_or_404(Quote, pk=pk, organization=org)
        lead = get_object_or_404(Lead.objects.select_for_update(), pk=reference.assessment.consultation.lead_id, organization=org)
        quote = get_object_or_404(Quote.objects.select_for_update(), pk=pk, organization=org)
        serializer = ApprovalCorrectionInput(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        if quote.version != data["expected_version"]:
            raise Conflict()
        if quote.status != Quote.Status.ACCEPTED or lead.status != Lead.Status.WON:
            raise Conflict("Only a recorded approval can be corrected here")
        if Project.objects.filter(organization=org, lead=lead).exists():
            raise Conflict("This revision already has a project; preserve its accepted baseline")
        if not QuoteEvent.objects.filter(organization=org, revision=quote.current_revision, kind=QuoteEvent.Kind.ACCEPTED).exists():
            raise Conflict("Recorded approval evidence is unavailable")
        before = QuoteSerializer(quote).data
        QuoteEvent.objects.create(organization=org, revision=quote.current_revision, actor=request.user,
            kind=QuoteEvent.Kind.APPROVAL_CORRECTED, reference=data["reference"], note=data["note"], occurred_at=timezone.now())
        update_versioned(lead, lead.version, status=Lead.Status.QUOTED)
        update_versioned(quote, data["expected_version"], status=Quote.Status.SENT)
        settle_task(org, f"quote:{quote.pk}:project", cancelled=True)
        plan_task(org, lead, f"quote:{quote.pk}:reply", "Follow up on shared quotation", request.user,
                  due_at=data["follow_up_due_at"])
        audit(request, quote, "QUOTE_APPROVAL_CORRECTED", data["note"], before)
        return Response(QuoteSerializer(quote).data)
