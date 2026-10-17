from django.db import transaction
from django.shortcuts import get_object_or_404
from django.db.models import Q
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
        _, membership = organization_for(self.request)
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
        fields = ["id", "lead", "customer_name", "title", "due_at", "done"]


class DailyQueueView(ListAPIView):
    serializer_class = ActionSerializer

    def get_queryset(self):
        org, membership = organization_for(self.request)
        qs = NextAction.objects.filter(organization=org, done=False).select_related("lead__customer")
        if membership.role == Membership.Role.FIELD:
            qs = qs.filter(assignee=self.request.user)
        # Today's queue includes overdue and undated work, not future reminders.
        tomorrow = timezone.localtime(timezone.now()).replace(hour=0, minute=0, second=0, microsecond=0) + timezone.timedelta(days=1)
        return qs.filter(Q(due_at__lt=tomorrow) | Q(due_at__isnull=True)).order_by("due_at", "created_at")



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
        _, membership = organization_for(self.request)
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
        actions = NextAction.objects.select_for_update().filter(organization=org)
        if membership.role == Membership.Role.FIELD:
            actions = actions.filter(assignee=request.user)
        action = get_object_or_404(actions, pk=pk)
        # Repeated completion is harmless and never creates duplicate follow-ups.
        if action.done:
            return Response(ActionSerializer(action).data)
        serializer = CompletionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        action.done = True
        action.save(update_fields=["done"])
        Activity.objects.create(
            organization=org, actor=request.user, lead=action.lead,
            kind="ACTION_COMPLETED", details={"action_id": action.pk, "note": data["note"]},
        )
        if "follow_up_title" in data:
            NextAction.objects.create(
                organization=org, lead=action.lead, assignee=action.assignee,
                title=data["follow_up_title"], due_at=data["follow_up_due_at"],
            )
        return Response(ActionSerializer(action).data)
