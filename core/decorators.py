"""
Decorators for 21 Void Technologies.
Includes role-based access control and AJAX enforcement.
"""

from functools import wraps
from django.shortcuts import redirect
from django.http import HttpResponseBadRequest
from .responses import permission_denied_response, error_response

def role_required(allowed_roles):
    """
    Decorator to restrict view access to specific user roles.
    If the user does not have an allowed role, returns a standard permission denied JSON envelope
    for AJAX requests, or redirects to the dashboard for regular requests.
    """
    if isinstance(allowed_roles, str):
        allowed_roles = [allowed_roles]

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    return error_response("Authentication Required", "Please log in to continue.", status=401)
                return redirect('accounts:login')

            user_role = getattr(request.user, 'role', None)
            is_super = getattr(request.user, 'is_superuser', False)

            if is_super or user_role in allowed_roles:
                return view_func(request, *args, **kwargs)

            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return permission_denied_response(
                    title="Access Denied",
                    message="You do not have the required permissions for this action."
                )
            return redirect('dashboard:index')
        return _wrapped_view
    return decorator

def admin_required(view_func):
    """Shorthand for requiring the ADMIN role."""
    return role_required(['ADMIN'])(view_func)

def manager_or_admin_required(view_func):
    """Shorthand for requiring MANAGER or ADMIN roles."""
    return role_required(['ADMIN', 'MANAGER'])(view_func)

def ajax_required(view_func):
    """
    Ensures that the endpoint can only be accessed via AJAX (jQuery $.ajax).
    Returns standard JSON envelope if invoked as standard browser navigation.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if request.headers.get('x-requested-with') != 'XMLHttpRequest':
            return error_response(
                title="Invalid Request",
                message="This endpoint only accepts asynchronous AJAX requests.",
                status=400
            )
        return view_func(request, *args, **kwargs)
    return _wrapped_view
