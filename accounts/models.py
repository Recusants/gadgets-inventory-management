from django.db import models
from django.contrib.auth.models import AbstractUser

class UserRole(models.TextChoices):
    ADMIN = 'ADMIN', 'Admin'
    MANAGER = 'MANAGER', 'Manager'
    STAFF = 'STAFF', 'Staff'

class User(AbstractUser):
    role = models.CharField(
        max_length=20,
        choices=UserRole.choices,
        default=UserRole.STAFF,
        help_text="Role-based access level"
    )
    phone = models.CharField(
        max_length=30,
        blank=True,
        null=True,
        help_text="Contact phone number"
    )

    def is_admin_role(self):
        return self.role == UserRole.ADMIN or self.is_superuser

    def is_manager_role(self):
        return self.role in (UserRole.ADMIN, UserRole.MANAGER) or self.is_superuser

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.get_role_display()})"
