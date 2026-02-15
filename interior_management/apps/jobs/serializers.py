from rest_framework import serializers
from .models import Job

class JobSerializer(serializers.ModelSerializer):
    customer_name = serializers.ReadOnlyField(source='customer.name')
    assigned_staff_name = serializers.ReadOnlyField(source='assigned_staff.username')

    remaining_balance = serializers.ReadOnlyField()
    is_fully_paid = serializers.ReadOnlyField()

    class Meta:
        model = Job
        fields = [
            'id', 'customer', 'customer_name', 'title', 'description', 
            'status', 'start_date', 'due_date', 'estimated_cost', 
            'actual_payment_received', 'remaining_balance', 'is_fully_paid',
            'assigned_staff', 'assigned_staff_name', 'created_at', 'updated_at'
        ]