from rest_framework import serializers
from .models import Customer

class CustomerSerializer(serializers.ModelSerializer):
    created_by_name = serializers.ReadOnlyField(source='created_by.username')

    class Meta:
        model = Customer
        fields = '__all__'
        read_only_fields = ['created_by', 'created_at', 'updated_at']