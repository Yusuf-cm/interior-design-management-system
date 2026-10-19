"""Same-origin development workspace and session bootstrap."""
import json
from django.contrib.auth import authenticate, login, logout
from django.http import JsonResponse
from django.middleware.csrf import get_token, rotate_token
from django.shortcuts import render
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_POST
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Membership
from .views import organization_for, require_office_member


def session_payload(request):
    signed_in = request.user.is_authenticated and request.user.is_active
    memberships = []
    if signed_in:
        memberships = list(Membership.objects.filter(
            user=request.user, active=True,
        ).select_related("organization").order_by("organization__name").values(
            "organization_id", "organization__name", "role"))
    return {"authenticated": signed_in, "csrf_token": get_token(request),
            "user": {"id": request.user.pk, "name": request.user.get_full_name() or request.user.username}
            if signed_in else None,
            "organizations": [{"id": member["organization_id"], "name": member["organization__name"],
                               "role": member["role"]} for member in memberships]}


@never_cache
@ensure_csrf_cookie
@require_GET
def workspace(request):
    return render(request, "studio_os/workspace.html")


@never_cache
@ensure_csrf_cookie
@require_GET
def session(request):
    return JsonResponse(session_payload(request))


@never_cache
@csrf_protect
@require_POST
def sign_in(request):
    try:
        data = json.loads(request.body)
        if not isinstance(data, dict):
            raise ValueError()
    except (ValueError, UnicodeDecodeError):
        return JsonResponse({"detail": "Enter a username and password"}, status=400)
    username, password = data.get("username"), data.get("password")
    if not isinstance(username, str) or not isinstance(password, str) or len(username) > 150 or len(password) > 1024:
        return JsonResponse({"detail": "Enter a username and password"}, status=400)
    user = authenticate(request, username=username, password=password)
    if user is None:
        return JsonResponse({"detail": "Username or password is incorrect"}, status=400)
    login(request, user)
    return JsonResponse(session_payload(request))


@never_cache
@csrf_protect
@require_POST
def sign_out(request):
    logout(request)
    rotate_token(request)
    return JsonResponse(session_payload(request))


class StaffDirectoryView(APIView):
    def get(self, request):
        org, membership = organization_for(request)
        require_office_member(membership)
        members = Membership.objects.filter(
            organization=org, active=True, user__is_active=True,
        ).select_related("user").order_by("user__username")
        return Response([{"id": member.user_id, "name": member.user.get_full_name() or member.user.username,
                          "role": member.role} for member in members])
