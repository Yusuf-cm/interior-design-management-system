from django.test import TestCase
from rest_framework.test import APIRequestFactory
from .models import User
from .serializers import UserSerializer


class UserProfileSecurityTests(TestCase):
    def test_staff_cannot_change_own_role_through_profile_serializer(self):
        user = User.objects.create_user(username="staff_member", password="test-password", role="staff")
        serializer = UserSerializer(user, data={"role": "admin", "first_name": "Updated"}, partial=True)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        serializer.save()
        user.refresh_from_db()
        self.assertEqual(user.role, "staff")
        self.assertEqual(user.first_name, "Updated")
