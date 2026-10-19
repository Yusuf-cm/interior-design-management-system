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
    origin_key = models.CharField(max_length=120, blank=True, default="")
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


    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["organization", "origin_key"],
                                    condition=~models.Q(origin_key=""), name="unique_action_origin"),
        ]


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


class Assessment(models.Model):
    class Status(models.TextChoices):
        DRAFT = "DRAFT"
        READY = "READY_FOR_ESTIMATE"
        REOPENED = "REOPENED"

    organization = models.ForeignKey(Organization, on_delete=models.PROTECT)
    consultation = models.OneToOneField(Consultation, on_delete=models.PROTECT, related_name="assessment")
    scope = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    measurements = models.JSONField(default=list)
    provisional_reason = models.TextField(blank=True)
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.DRAFT)
    version = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)


class Quote(models.Model):
    class Status(models.TextChoices):
        DRAFT = "DRAFT"
        REVIEW = "READY_FOR_REVIEW"
        APPROVED = "APPROVED_TO_SHARE"

    organization = models.ForeignKey(Organization, on_delete=models.PROTECT)
    assessment = models.OneToOneField(Assessment, on_delete=models.PROTECT, related_name="quote")
    currency = models.CharField(max_length=3)
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.DRAFT)
    current_revision = models.ForeignKey("QuoteRevision", null=True, blank=True, on_delete=models.PROTECT,
                                         related_name="+")
    version = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)


class QuoteRevision(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.PROTECT)
    quote = models.ForeignKey(Quote, on_delete=models.PROTECT, related_name="revisions")
    number = models.PositiveIntegerField()
    assessment_version = models.PositiveIntegerField()
    scope_snapshot = models.TextField()
    notes_snapshot = models.TextField(blank=True)
    measurements_snapshot = models.JSONField(default=list)
    provisional_reason_snapshot = models.TextField(blank=True)
    currency = models.CharField(max_length=3)
    items = models.JSONField(default=list)
    subtotal = models.DecimalField(max_digits=18, decimal_places=2)
    discount = models.DecimalField(max_digits=18, decimal_places=2)
    tax_rate = models.DecimalField(max_digits=7, decimal_places=6)
    tax = models.DecimalField(max_digits=18, decimal_places=2)
    total = models.DecimalField(max_digits=18, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["quote", "number"], name="unique_quote_revision"),
            models.CheckConstraint(condition=models.Q(total__gte=0, subtotal__gte=0, discount__gte=0,
                                                       tax_rate__gte=0, tax_rate__lte=1),
                                   name="quote_nonnegative_amounts"),
        ]

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValueError("Quote revisions are append-only; create a new revision")
        super().save(*args, **kwargs)
