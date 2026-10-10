from rest_framework import serializers
from .models import Job
from apps.accounts.models import User

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

    def validate(self, attrs):
        user = self.context['request'].user
        if user.role != User.IS_ADMIN:
            customer = attrs.get('customer')
            current_customer = self.instance.customer_id if self.instance else None
            if customer and customer.created_by_id != user.id and customer.id != current_customer:
                raise serializers.ValidationError({'customer': 'Select a customer you manage.'})
            if 'assigned_staff' in attrs and attrs['assigned_staff'] != user:
                raise serializers.ValidationError({'assigned_staff': 'Only administrators can reassign projects.'})
        return attrs
