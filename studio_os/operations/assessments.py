"""Site observations and explicit readiness checks for internal estimates."""
from decimal import Decimal
from django.db import transaction
from django.db.models import F
from django.shortcuts import get_object_or_404
from rest_framework import serializers, status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Activity, Assessment, Consultation, Lead, Membership, Quote
from .views import Conflict, organization_for, require_office_member, require_open_lead, update_versioned
from .workflow_tasks import plan_task, settle_task


class MeasurementSerializer(serializers.Serializer):
    label = serializers.CharField(max_length=180)
    value = serializers.DecimalField(max_digits=12, decimal_places=3, min_value=Decimal("0.001"),
                                     allow_null=True)
    unit = serializers.ChoiceField(choices=["mm", "cm", "m", "m2", "count"])
    required = serializers.BooleanField(default=True)


class AssessmentContentSerializer(serializers.Serializer):
    scope = serializers.CharField(max_length=12000, allow_blank=True)
    notes = serializers.CharField(max_length=12000, allow_blank=True, required=False, default="")
    measurements = MeasurementSerializer(many=True, max_length=100)

    def validate_measurements(self, values):
        labels = [value["label"].casefold() for value in values]
        if len(set(labels)) != len(labels):
            raise serializers.ValidationError("Measurement labels must be distinct")
        # Decimal quantities are stored as strings rather than binary floating point.
        return [{**value, "value": str(value["value"]) if value["value"] is not None else None}
                for value in values]


def missing_information(assessment):
    missing = []
    if not assessment.scope.strip():
        missing.append("scope")
    required = [item for item in assessment.measurements if item["required"]]
    if not required:
        missing.append("required measurement plan")
    missing.extend(item["label"] for item in required if item["value"] is None)
    return missing


class AssessmentSerializer(serializers.ModelSerializer):
    missing_information = serializers.SerializerMethodField()

    class Meta:
        model = Assessment
        fields = ["id", "consultation", "scope", "notes", "measurements", "provisional_reason",
                  "status", "version", "missing_information", "created_at"]
        read_only_fields = fields

    def get_missing_information(self, obj):
        return missing_information(obj)


def audit(request, assessment, kind, note, before=None):
    Activity.objects.create(
        organization=assessment.organization, actor=request.user, lead=assessment.consultation.lead,
        kind=kind, details={"assessment_id": assessment.pk, "note": note,
                            "before": before, "after": AssessmentSerializer(assessment).data},
    )


def scoped_assessment(request, pk):
    org, membership = organization_for(request)
    require_office_member(membership)
    assessment = get_object_or_404(Assessment, pk=pk, organization=org)
    return org, membership, assessment


def locked_assessment(request, pk):
    org, membership, ref = scoped_assessment(request, pk)
    lead = get_object_or_404(Lead.objects.select_for_update(), pk=ref.consultation.lead_id, organization=org)
    assessment = get_object_or_404(Assessment.objects.select_for_update(), pk=pk, organization=org)
    require_open_lead(lead)
    return org, membership, lead, assessment


class AssessmentCreateView(APIView):
    @transaction.atomic
    def post(self, request, pk):
        org, membership = organization_for(request)
        require_office_member(membership)
        visit = get_object_or_404(Consultation, pk=pk, organization=org)
        lead = get_object_or_404(Lead.objects.select_for_update(), pk=visit.lead_id, organization=org)
        require_open_lead(lead)
        if visit.status != Consultation.Status.COMPLETED:
            raise Conflict("Complete the site visit before recording an assessment")
        if Assessment.objects.filter(consultation=visit).exists():
            raise Conflict("This visit already has an assessment")
        serializer = AssessmentContentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        assessment = Assessment.objects.create(organization=org, consultation=visit, **serializer.validated_data)
        settle_task(org, f"visit:{visit.pk}:assessment")
        audit(request, assessment, "ASSESSMENT_CREATED", "Site assessment recorded")
        return Response(AssessmentSerializer(assessment).data, status=status.HTTP_201_CREATED)


class AssessmentEditSerializer(AssessmentContentSerializer):
    expected_version = serializers.IntegerField(min_value=1)
    note = serializers.CharField(max_length=4000)


class AssessmentDetailView(APIView):
    def get(self, request, pk):
        _, _, assessment = scoped_assessment(request, pk)
        return Response(AssessmentSerializer(assessment).data)

    @transaction.atomic
    def patch(self, request, pk):
        org, _, _, assessment = locked_assessment(request, pk)
        if assessment.status == Assessment.Status.READY:
            raise Conflict("Reopen the assessment before changing observations")
        serializer = AssessmentEditSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        for key in ("expected_version", "note"):
            if key not in data:
                raise ValidationError({key: "This field is required"})
        changes = {key: data[key] for key in ("scope", "notes", "measurements") if key in data}
        if not changes:
            raise ValidationError("Supply scope, notes or measurements to change")
        before = AssessmentSerializer(assessment).data
        update_versioned(assessment, data["expected_version"], **changes, provisional_reason="")
        audit(request, assessment, "ASSESSMENT_UPDATED", data["note"], before)
        return Response(AssessmentSerializer(assessment).data)


class AssessmentCommandSerializer(serializers.Serializer):
    expected_version = serializers.IntegerField(min_value=1)
    command = serializers.ChoiceField(choices=["ready", "reopen"])
    note = serializers.CharField(max_length=4000)
    provisional_reason = serializers.CharField(max_length=4000, required=False)


class AssessmentCommandView(APIView):
    @transaction.atomic
    def post(self, request, pk):
        org, membership, lead, assessment = locked_assessment(request, pk)
        serializer = AssessmentCommandSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        if data["expected_version"] != assessment.version:
            raise Conflict()
        before = AssessmentSerializer(assessment).data
        reason = data.get("provisional_reason", "")
        if reason and membership.role != Membership.Role.OWNER:
            raise PermissionDenied("Only an owner can authorize a provisional estimate")
        if data["command"] == "ready":
            if assessment.status not in {Assessment.Status.DRAFT, Assessment.Status.REOPENED}:
                raise Conflict("Assessment is already ready")
            if not assessment.scope.strip():
                raise ValidationError({"scope": "Record the proposed scope first"})
            missing = missing_information(assessment)
            if missing and not reason:
                raise ValidationError({"missing_information": missing})
            update_versioned(assessment, data["expected_version"],
                             status=Assessment.Status.READY, provisional_reason=reason)
            if lead.status == Lead.Status.CONSULTATION_BOOKED:
                update_versioned(lead, lead.version, status=Lead.Status.ASSESSED)
            plan_task(org, lead, f"assessment:{assessment.pk}:estimate",
                      "Prepare quotation draft", request.user)
        else:
            if reason:
                raise ValidationError("Provisional authorization is only accepted when marking ready")
            if assessment.status != Assessment.Status.READY:
                raise Conflict("Only ready assessments can be reopened")
            update_versioned(assessment, data["expected_version"],
                             status=Assessment.Status.REOPENED, provisional_reason="")
            settle_task(org, f"assessment:{assessment.pk}:estimate", cancelled=True)
            # Revoking readiness also revokes any internal approval based on that source.
            quote = Quote.objects.select_for_update().filter(assessment=assessment, organization=org).first()
            if quote:
                Quote.objects.filter(pk=quote.pk).update(status=Quote.Status.DRAFT, version=F("version") + 1)
                settle_task(org, f"quote:{quote.pk}:review", cancelled=True)
                Activity.objects.create(
                    organization=org, actor=request.user, lead=lead, kind="QUOTE_SOURCE_REOPENED",
                    details={"quote_id": quote.pk, "previous_status": quote.status,
                             "new_status": Quote.Status.DRAFT, "note": data["note"]},
                )
            plan_task(org, lead, f"assessment:{assessment.pk}:recheck", "Recheck site assessment", request.user)
        if data["command"] == "ready":
            settle_task(org, f"assessment:{assessment.pk}:recheck")
        audit(request, assessment, "ASSESSMENT_" + data["command"].upper(), data["note"], before)
        return Response(AssessmentSerializer(assessment).data)
