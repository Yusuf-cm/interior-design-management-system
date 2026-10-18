from django.conf import settings
from django.db import models


class Organization(models.Model):
    name = models.CharField(max_length=180)
    currency = models.CharField(max_length=3, default="KES")
    created_at = models.DateTimeField(auto_now_add=True)


class Membership(models.Model):
    class Role(models.TextChoices):
        OWNER = "OWNER"
        COORDINATOR = "COORDINATOR"
        DESIGNER = "DESIGNER"
        FIELD = "FIELD"

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=Role.choices)
    active = models.BooleanField(default=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["organization", "user"], name="unique_org_membership")]


class Customer(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.PROTECT)
    name = models.CharField(max_length=180)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=40, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class Lead(models.Model):
    class Status(models.TextChoices):
        NEW = "NEW"
        CONTACTED = "CONTACTED"
        QUALIFIED = "QUALIFIED"
        CONSULTATION_BOOKED = "CONSULTATION_BOOKED"
        ASSESSED = "ASSESSED"
        QUOTED = "QUOTED"
        WON = "WON"
        LOST = "LOST"
        DORMANT = "DORMANT"

    organization = models.ForeignKey(Organization, on_delete=models.PROTECT)
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name="leads")
    brief = models.TextField(blank=True)
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.NEW)
    version = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)


class Activity(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.PROTECT)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    lead = models.ForeignKey(Lead, on_delete=models.PROTECT, null=True, blank=True)
    kind = models.CharField(max_length=64)
    details = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)


class NextAction(models.Model):
    consultation = models.OneToOneField("Consultation", null=True, blank=True,
                                      on_delete=models.PROTECT, related_name="visit_action")
    organization = models.ForeignKey(Organization, on_delete=models.PROTECT)
    lead = models.ForeignKey(Lead, on_delete=models.PROTECT, related_name="actions")
    assignee = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    title = models.CharField(max_length=180)
    due_at = models.DateTimeField(null=True, blank=True)
    done = models.BooleanField(default=False)
    cancelled = models.BooleanField(default=False)
    version = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)


class Consultation(models.Model):
    class Status(models.TextChoices):
        PROPOSED = "PROPOSED"
        CONFIRMED = "CONFIRMED"
        RESCHEDULED = "RESCHEDULED"
        COMPLETED = "COMPLETED"
        CANCELLED = "CANCELLED"
        NO_SHOW = "NO_SHOW"

    organization = models.ForeignKey(Organization, on_delete=models.PROTECT)
    lead = models.ForeignKey(Lead, on_delete=models.PROTECT, related_name="consultations")
    assignee = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    location = models.CharField(max_length=300)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PROPOSED)
    outcome = models.TextField(blank=True)
    version = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=models.Q(ends_at__gt=models.F("starts_at")),
                                   name="consultation_positive_duration"),
        ]
        indexes = [models.Index(fields=["organization", "assignee", "status", "starts_at"])]
