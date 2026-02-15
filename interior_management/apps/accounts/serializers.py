from rest_framework import serializers
from .models import User

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'role', 'phone_number', 'first_name', 'last_name']

class RegisterSerializer(serializers.ModelSerializer):
    # We explicitly define these to ensure they are handled as strings
    password = serializers.CharField(write_only=True)
    email = serializers.EmailField(required=True)
    role = serializers.CharField(required=True)

    class Meta:
        model = User
        fields = ['username', 'password', 'email', 'role', 'phone_number']

    def create(self, validated_data):
        # Professional User Creation
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
            role=validated_data.get('role', 'staff'),
            phone_number=validated_data.get('phone_number', '')
        )
        return user