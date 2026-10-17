from django.db import transaction
from django.utils import timezone
from rest_framework import serializers, status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.generics import ListCreateAPIView, ListAPIView
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Activity, Customer, Lead, Membership, NextAction


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
        fields = ["id", "customer", "brief", "status", "created_at"]
        read_only_fields = ["id", "status", "created_at"]


class LeadListCreateView(ListCreateAPIView):
    serializer_class = LeadSerializer

    def get_queryset(self):
        org, _ = organization_for(self.request)
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
        fields = ["id", "lead", "customer_name", "title", "due_at", "done"]


class DailyQueueView(ListAPIView):
    serializer_class = ActionSerializer

    def get_queryset(self):
        org, membership = organization_for(self.request)
        qs = NextAction.objects.filter(organization=org, done=False).select_related("lead__customer")
        if membership.role == Membership.Role.FIELD:
            qs = qs.filter(assignee=self.request.user)
        return qs.order_by("due_at", "created_at")



class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = ["id", "name", "email", "phone", "created_at"]
        read_only_fields = ["id", "created_at"]


class CustomerListCreateView(ListCreateAPIView):
    """Tenant-scoped customer directory; company ownership is never client-supplied."""
    serializer_class = CustomerSerializer

    def get_queryset(self):
        org, _ = organization_for(self.request)
        return Customer.objects.filter(organization=org).order_by("-created_at")

    @transaction.atomic
    def perform_create(self, serializer):
        org, membership = organization_for(self.request)
        if membership.role == Membership.Role.FIELD:
            raise PermissionDenied("Field staff cannot create customers")
        serializer.save(organization=org)
