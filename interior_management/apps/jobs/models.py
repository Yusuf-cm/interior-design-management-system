from django.db import models
from django.conf import settings
from apps.customers.models import Customer

class Job(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('ACTIVE', 'Active'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
    ]

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='jobs')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    
    # Workflow
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    start_date = models.DateField(null=True, blank=True)
    due_date = models.DateField(null=True, blank=True)
    
    # Financials
    estimated_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    actual_payment_received = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    # Management
    assigned_staff = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='assigned_jobs'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} - {self.customer.name}"

    class Meta:
        ordering = ['-created_at']

    @property
    def remaining_balance(self):
        return self.estimated_cost - self.actual_payment_received
    
    @property
    def is_fully_paid(self):
        return self.actual_payment_received >= self.estimated_cost