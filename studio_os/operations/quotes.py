"""Internal quotation drafting and review. No sending, acceptance or commitments."""
from decimal import Decimal
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import serializers, status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView
from studio_os.domain.policies import DomainError
from studio_os.domain.pricing import calculate_estimate
from .models import Activity, Assessment, Lead, Membership, Quote, QuoteRevision
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

    class Meta:
        model = Quote
        fields = ["id", "assessment", "lead", "customer_name", "currency", "status", "version", "source_current",
                  "current_revision", "created_at"]
        read_only_fields = fields

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
                         "revisions": QuoteRevisionSerializer(
                             quote.revisions.filter(organization=org).order_by("number"), many=True).data})


class QuoteRevisionView(APIView):
    @transaction.atomic
    def post(self, request, pk):
        org, _, _, assessment, quote = locked_quote(request, pk)
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
