from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from django.db.models import Q


class EmailOrUsernameModelBackend(ModelBackend):
    """
    Custom authentication backend that allows users to authenticate
    using their email address (case-insensitive) or username as a fallback.
    """
    def user_can_authenticate(self, user):
        """Allow authenticate to return user so login view can present a clear deactivation message."""
        return True

    def authenticate(self, request, username=None, password=None, **kwargs):
        UserModel = get_user_model()
        identifier = username or kwargs.get('email')

        if not identifier or not password:
            return None

        identifier = identifier.strip()

        # Match by email first (case-insensitive), fallback to username
        user = UserModel.objects.filter(
            Q(email__iexact=identifier) | Q(username__iexact=identifier)
        ).first()

        if user and user.check_password(password) and self.user_can_authenticate(user):
            return user

        return None
