"""Tenant-scoped visit scheduling. No external calendar or customer messages."""
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import serializers, status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Activity, Consultation, Lead, Membership, NextAction
from .workflow_tasks import plan_task
from .views import Conflict, organization_for, require_office_member, update_versioned


class ConsultationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Consultation
        fields = ["id", "lead", "assignee", "starts_at", "ends_at", "location",
                  "status", "outcome", "version", "created_at"]
        read_only_fields = fields


class ScheduleSerializer(serializers.Serializer):
    starts_at = serializers.DateTimeField()
    ends_at = serializers.DateTimeField()
    location = serializers.CharField(max_length=300)
    assignee = serializers.IntegerField(min_value=1)

    def validate(self, data):
        if data["ends_at"] <= data["starts_at"]:
            raise serializers.ValidationError("Visit end must follow its start")
        if data["starts_at"] <= timezone.now():
            raise serializers.ValidationError("Schedule visits in the future")
        return data


class VisitCommandSerializer(serializers.Serializer):
    expected_version = serializers.IntegerField(min_value=1)
    command = serializers.ChoiceField(choices=["confirm", "reschedule", "cancel", "complete", "no_show"])
    note = serializers.CharField(max_length=4000)
    starts_at = serializers.DateTimeField(required=False)
    ends_at = serializers.DateTimeField(required=False)
    location = serializers.CharField(max_length=300, required=False)
    assignee = serializers.IntegerField(min_value=1, required=False)


def eligible_lead(lead):
    if lead.status not in {Lead.Status.QUALIFIED, Lead.Status.CONSULTATION_BOOKED}:
        raise Conflict("A visit requires a qualified inquiry")


def assigned_member(org, user_id, actor_membership, *, restrict_assignment=True):
    # Serializes bookings for this staff member on databases supporting row locks.
    member = Membership.objects.select_for_update().filter(
        organization=org, user_id=user_id, active=True, user__is_active=True,
    ).first()
    if not member:
        raise ValidationError({"assignee": "Assignee unavailable"})
    if restrict_assignment and user_id != actor_membership.user_id and actor_membership.role not in {
        Membership.Role.OWNER, Membership.Role.COORDINATOR,
    }:
        raise PermissionDenied("Only owners and coordinators can assign other staff")
    return member


def check_conflict(visit):
    if Consultation.objects.filter(
        organization=visit.organization, assignee_id=visit.assignee_id,
        status=Consultation.Status.CONFIRMED,
        starts_at__lt=visit.ends_at, ends_at__gt=visit.starts_at,
    ).exclude(pk=visit.pk).exists():
        raise Conflict("Staff member already has a confirmed visit during this time")


def audit(request, visit, command, note, before=None):
    Activity.objects.create(
        organization=visit.organization, actor=request.user, lead=visit.lead,
        kind="CONSULTATION_" + command.upper(),
        details={"consultation_id": visit.pk, "note": note,
                 "before": before, "after": ConsultationSerializer(visit).data},
    )


def sync_action(visit):
    action = NextAction.objects.filter(consultation=visit).first()
    if visit.status == Consultation.Status.CONFIRMED:
        if action:
            update_versioned(action, action.version, title="Attend consultation",
                             due_at=visit.starts_at, assignee_id=visit.assignee_id,
                             done=False, cancelled=False)
        else:
            NextAction.objects.create(
                organization=visit.organization, lead=visit.lead, consultation=visit,
                assignee_id=visit.assignee_id, title="Attend consultation", due_at=visit.starts_at,
            )
    elif action:
        update_versioned(action, action.version,
                         done=visit.status == Consultation.Status.COMPLETED,
                         cancelled=visit.status != Consultation.Status.COMPLETED)


class ConsultationListView(APIView):
    def get(self, request):
        org, membership = organization_for(request)
        visits = Consultation.objects.filter(organization=org).order_by("starts_at", "pk")
        if membership.role == Membership.Role.FIELD:
            visits = visits.filter(assignee=request.user)
        return Response(ConsultationSerializer(visits, many=True).data)


class ConsultationCreateView(APIView):
    @transaction.atomic
    def post(self, request, pk):
        org, membership = organization_for(request)
        require_office_member(membership)
        lead = get_object_or_404(Lead.objects.select_for_update(), organization=org, pk=pk)
        eligible_lead(lead)
        serializer = ScheduleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        assigned_member(org, data["assignee"], membership)
        visit = Consultation.objects.create(
            organization=org, lead=lead, assignee_id=data["assignee"],
            starts_at=data["starts_at"], ends_at=data["ends_at"], location=data["location"],
        )
        # Proposals do not reserve staff time or change inquiry stage.
        audit(request, visit, "proposed", "Visit proposed")
        return Response(ConsultationSerializer(visit).data, status=status.HTTP_201_CREATED)


class ConsultationCommandView(APIView):
    @transaction.atomic
    def post(self, request, pk):
        org, membership = organization_for(request)
        qs = Consultation.objects.filter(organization=org)
        if membership.role == Membership.Role.FIELD:
            qs = qs.filter(assignee=request.user)
        reference = get_object_or_404(qs, pk=pk)
        lead = get_object_or_404(Lead.objects.select_for_update(), organization=org, pk=reference.lead_id)
        visit = get_object_or_404(qs.select_for_update(), pk=pk)
        serializer = VisitCommandSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        command = data["command"]
        if membership.role == Membership.Role.FIELD and command not in {"complete", "no_show"}:
            raise PermissionDenied("Field staff can only record assigned visit outcomes")
        if visit.version != data["expected_version"]:
            raise Conflict()
        eligible_lead(lead)
        before = ConsultationSerializer(visit).data
        active = {Consultation.Status.PROPOSED, Consultation.Status.CONFIRMED, Consultation.Status.RESCHEDULED}
        if visit.status not in active:
            raise Conflict("This visit already has a final outcome")
        changes = {}
        if command == "reschedule":
            scheduling = ScheduleSerializer(data={key: data[key] for key in
                ("starts_at", "ends_at", "location", "assignee") if key in data})
            scheduling.is_valid(raise_exception=True)
            plan = scheduling.validated_data
            assigned_member(org, plan["assignee"], membership)
            changes = {"starts_at": plan["starts_at"], "ends_at": plan["ends_at"],
                       "location": plan["location"], "assignee_id": plan["assignee"]}
            changes["status"] = Consultation.Status.RESCHEDULED
        else:
            if any(key in data for key in ("starts_at", "ends_at", "location", "assignee")):
                raise ValidationError("Schedule fields are only accepted for rescheduling")
            if command == "confirm":
                if visit.status not in {Consultation.Status.PROPOSED, Consultation.Status.RESCHEDULED}:
                    raise Conflict("Only proposed or rescheduled visits can be confirmed")
                if visit.starts_at <= timezone.now():
                    raise ValidationError("Cannot confirm a visit whose start has passed")
                assigned_member(org, visit.assignee_id, membership, restrict_assignment=False)
                check_conflict(visit)
                changes["status"] = Consultation.Status.CONFIRMED
                if lead.status == Lead.Status.QUALIFIED:
                    update_versioned(lead, lead.version, status=Lead.Status.CONSULTATION_BOOKED)
            elif command == "cancel":
                changes["status"] = Consultation.Status.CANCELLED
            else:
                if visit.status != Consultation.Status.CONFIRMED:
                    raise Conflict("Only confirmed visits can have outcomes")
                if visit.starts_at > timezone.now():
                    raise ValidationError("Cannot record an outcome before the visit starts")
                changes = {"status": Consultation.Status.COMPLETED if command == "complete"
                           else Consultation.Status.NO_SHOW, "outcome": data["note"]}
        update_versioned(visit, data["expected_version"], **changes)
        sync_action(visit)
        if command in {"complete", "no_show", "cancel"}:
            if command == "complete":
                plan_task(org, lead, f"visit:{visit.pk}:assessment", "Prepare visit assessment", request.user)
            else:
                NextAction.objects.create(
                    organization=org, lead=lead, assignee=request.user, due_at=timezone.now(),
                    title={"no_show": "Follow up on missed consultation",
                           "cancel": "Review cancelled consultation"}[command],
                )
        audit(request, visit, command, data["note"], before)
        return Response(ConsultationSerializer(visit).data)
