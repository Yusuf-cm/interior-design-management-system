from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    # Roles
    IS_ADMIN = 'admin'
    IS_STAFF = 'STAFF'

    ROLE_CHOICES = [
        (IS_ADMIN, 'Admin'),
        (IS_STAFF, 'Staff'),
    ]

    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default=IS_STAFF)
    phone_number = models.CharField(max_length=15,blank=True, null=True)

    def __str__(self):
        return f"{self.username}({self.role})"
    
