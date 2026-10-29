"""Owner-managed company access. No email delivery or global privilege changes."""
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404
from rest_framework import serializers, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Activity, Membership, NextAction, Organization
from .views import Conflict, organization_for, update_versioned


def owner_context(request, *, lock=False):
    org, member = organization_for(request)
    if lock:
        org = Organization.objects.select_for_update().get(pk=org.pk)
        member.refresh_from_db()
    if not member.active or member.role != Membership.Role.OWNER or not request.user.is_active:
        raise PermissionDenied("Only owners can manage studio access")
    return org, member


def member_data(member):
    return {"id": member.pk, "user_id": member.user_id, "username": member.user.username,
            "name": member.user.get_full_name() or member.user.username,
            "role": member.role, "active": member.active, "version": member.version,
            "account_active": member.user.is_active,
            "open_actions": NextAction.objects.filter(
                organization_id=member.organization_id, assignee_id=member.user_id,
                done=False, cancelled=False).count()}


class NewMemberSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150, validators=[UnicodeUsernameValidator()])
    name = serializers.CharField(max_length=150)
    role = serializers.ChoiceField(choices=Membership.Role.choices)
    password = serializers.CharField(write_only=True, min_length=12, max_length=1024, trim_whitespace=False)

    def validate(self, data):
        user = get_user_model()(username=data["username"], first_name=data["name"])
        try:
            validate_password(data["password"], user=user)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"password": exc.messages})
        return data


class TeamView(APIView):
    def get(self, request):
        org, _ = owner_context(request)
        members = Membership.objects.filter(organization=org).select_related("user").order_by("user__username")
        return Response([member_data(member) for member in members])

    @transaction.atomic
    def post(self, request):
        org, _ = owner_context(request, lock=True)
        serializer = NewMemberSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        if get_user_model().objects.filter(username=data["username"]).exists():
            raise Conflict("Username unavailable; no existing account was changed")
        try:
            with transaction.atomic():
                user = get_user_model().objects.create_user(
                    username=data["username"], first_name=data["name"], password=data["password"])
        except IntegrityError:
            raise Conflict("Username unavailable; no existing account was changed")
        member = Membership.objects.create(organization=org, user=user, role=data["role"])
        Activity.objects.create(
            organization=org, actor=request.user, kind="TEAM_MEMBER_ADDED",
            details={"membership_id": member.pk, "user_id": user.pk, "role": member.role},
        )
        return Response(member_data(member), status=status.HTTP_201_CREATED)


class MemberUpdateSerializer(serializers.Serializer):
    expected_version = serializers.IntegerField(min_value=1)
    role = serializers.ChoiceField(choices=Membership.Role.choices, required=False)
    active = serializers.BooleanField(required=False)
    note = serializers.CharField(max_length=4000)

    def validate(self, data):
        if not any(key in data for key in ("role", "active")):
            raise serializers.ValidationError("Supply a role or access change")
        return data


class TeamMemberView(APIView):
    @transaction.atomic
    def patch(self, request, pk):
        org, _ = owner_context(request, lock=True)
        member = get_object_or_404(Membership.objects.select_for_update().select_related("user"),
                                   organization=org, pk=pk)
        serializer = MemberUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        if member.version != data["expected_version"]:
            raise Conflict()
        role = data.get("role", member.role)
        active = data.get("active", member.active)
        removing_owner = member.active and member.role == Membership.Role.OWNER and (not active or role != Membership.Role.OWNER)
        if removing_owner and not Membership.objects.filter(
            organization=org, active=True, role=Membership.Role.OWNER, user__is_active=True,
        ).exclude(pk=member.pk).exists():
            raise Conflict("Keep at least one active owner in the studio")
        before = {"role": member.role, "active": member.active}
        update_versioned(member, data["expected_version"], role=role, active=active)
        Activity.objects.create(
            organization=org, actor=request.user, kind="TEAM_ACCESS_CHANGED",
            details={"membership_id": member.pk, "before": before,
                     "after": {"role": member.role, "active": member.active}, "note": data["note"]},
        )
        return Response(member_data(member))
