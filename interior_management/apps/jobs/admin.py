from django.contrib import admin
from .models import Job

@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    # We can display the @property methods in the admin too!
    list_display = ('title', 'customer', 'status', 'estimated_cost', 'remaining_balance', 'is_fully_paid')
    list_filter = ('status', 'assigned_staff', 'start_date')
    search_fields = ('title', 'customer__name', 'description')
    
    # Organising the detail view
    fieldsets = (
        ('General Info', {
            'fields': ('title', 'customer', 'description', 'status')
        }),
        ('Schedule', {
            'fields': ('start_date', 'due_date')
        }),
        ('Financials', {
            'fields': ('estimated_cost', 'actual_payment_received')
        }),
        ('Assignment', {
            'fields': ('assigned_staff',)
        }),
    )

    # These are calculated, so they must be read-only in the admin
    def remaining_balance(self, obj):
        return obj.remaining_balance
    
    def is_fully_paid(self, obj):
        return obj.is_fully_paid
    is_fully_paid.boolean = True # Shows a nice Green Check / Red X icon