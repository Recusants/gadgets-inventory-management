"""
Custom middleware for 21 Void Technologies.
Enforces role-based session timeouts:
- Admins: 1 hour (3600 seconds)
- Staff / Managers: 8 hours (28800 seconds)
"""

from django.shortcuts import redirect
from django.conf import settings
from django.http import JsonResponse
from accounts.models import UserRole

class RoleSessionTimeoutMiddleware:
    """Sets session timeout dynamically based on the user's role."""
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            # Check if expiry is already configured for this session
            current_expiry = request.session.get('_role_expiry_set')
            user_role = getattr(request.user, 'role', None)
            
            if user_role == UserRole.ADMIN or request.user.is_superuser:
                target_expiry = 3600  # 1 hour
                role_key = 'admin_3600'
            else:
                target_expiry = 28800  # 8 hours
                role_key = 'staff_28800'

            if current_expiry != role_key:
                request.session.set_expiry(target_expiry)
                request.session['_role_expiry_set'] = role_key

        return self.get_response(request)


class GlobalLoginRequiredMiddleware:
    """
    Guarantees that unauthenticated users are redirected to LOGIN_URL.
    Exempts login/logout, static assets, and media.
    Handles AJAX gracefully with a 401 redirect JSON envelope.
    """
    EXEMPT_PREFIXES = (
        '/accounts/login/',
        '/accounts/logout/',
        '/static/',
        '/media/',
        '/admin/login/',
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not request.user.is_authenticated:
            path = request.path_info
            if not any(path.startswith(prefix) for prefix in self.EXEMPT_PREFIXES):
                if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    return JsonResponse({
                        'status': 'error',
                        'icon': 'error',
                        'title': 'Authentication Required',
                        'message': 'Your session has expired. Please log in again.',
                        'data': {'redirect_url': settings.LOGIN_URL}
                    }, status=401)
                return redirect(f"{settings.LOGIN_URL}?next={request.path}")

        return self.get_response(request)

