from django.db import models
from django.contrib.auth.models import AbstractUser

class UserRole(models.TextChoices):
    ADMIN = 'ADMIN', 'Admin'
    MANAGER = 'MANAGER', 'Manager'
    SUPERVISOR = 'SUPERVISOR', 'Supervisor'
    CASHIER = 'CASHIER', 'Cashier'
    STAFF = 'STAFF', 'Staff'

class User(AbstractUser):
    roles = models.JSONField(
        default=list,
        blank=True,
        help_text="List of assigned user roles"
    )
    phone = models.CharField(
        max_length=30,
        blank=True,
        null=True,
        help_text="Contact phone number"
    )

    @property
    def role(self):
        """Primary role for display and backward-compatibility."""
        if not self.roles:
            return UserRole.CASHIER
        return self.roles[0]

    def has_role(self, role_name):
        """Check if user has a specific role (or is superuser)."""
        if self.is_superuser:
            return True
        return role_name in (self.roles or [])

    def has_any_role(self, *role_names):
        """Check if user has at least one of the specified roles (or is superuser)."""
        if self.is_superuser:
            return True
        return any(r in (self.roles or []) for r in role_names)

    def is_admin_role(self):
        """Check if user has the ADMIN role or is superuser."""
        return self.is_superuser or UserRole.ADMIN in (self.roles or [])

    def is_manager_role(self):
        """Check if user has ADMIN or MANAGER role or is superuser."""
        return self.is_superuser or any(r in (self.roles or []) for r in (UserRole.ADMIN, UserRole.MANAGER))

    def is_supervisor_role(self):
        """Check if user has ADMIN, MANAGER, or SUPERVISOR role or is superuser."""
        return self.is_superuser or any(r in (self.roles or []) for r in (UserRole.ADMIN, UserRole.MANAGER, UserRole.SUPERVISOR))

    def is_cashier_role(self):
        """Check if user has CASHIER or STAFF role."""
        return any(r in (self.roles or []) for r in (UserRole.CASHIER, UserRole.STAFF))

    def get_roles_display(self):
        """Return human-readable comma-separated list of roles."""
        if not self.roles:
            return "Staff"
        role_map = dict(UserRole.choices)
        return ", ".join([role_map.get(r, r) for r in self.roles])

    def save(self, *args, **kwargs):
        if not self.roles:
            self.roles = [UserRole.STAFF]
        elif isinstance(self.roles, str):
            self.roles = [r.strip() for r in self.roles.split(',') if r.strip()]

        if self.is_superuser and UserRole.ADMIN not in self.roles:
            self.roles.append(UserRole.ADMIN)

        if any(r in (self.roles or []) for r in (UserRole.ADMIN, UserRole.MANAGER)):
            self.is_staff = True

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.get_roles_display()})"
