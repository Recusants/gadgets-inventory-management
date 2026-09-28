"""
Decorators for Clarity Retail / Avail Technologies.
Includes role-based access control with @allowed_roles and AJAX enforcement.
"""

from functools import wraps
from django.shortcuts import redirect
from django.http import HttpResponseBadRequest
from .responses import permission_denied_response, error_response

def allowed_roles(allowed_roles_list):
    """
    Custom decorator to restrict view access to specific user roles.
    Takes a list of allowed roles.
    Usage:
        @allowed_roles(['ADMIN'])
        @allowed_roles(['ADMIN', 'MANAGER'])
    """
    if isinstance(allowed_roles_list, str):
        allowed_roles_list = [allowed_roles_list]

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    return error_response("Authentication Required", "Please log in to continue.", status=401)
                return redirect('accounts:login')

            user_roles = getattr(request.user, 'roles', []) or []
            if isinstance(user_roles, str):
                user_roles = [user_roles]
            if hasattr(request.user, 'role') and request.user.role and request.user.role not in user_roles:
                user_roles.append(request.user.role)

            # Superuser or staff bypass or role membership match
            has_permission = (
                request.user.is_superuser or
                request.user.is_staff or
                any(r in allowed_roles_list for r in user_roles)
            )

            if has_permission:
                return view_func(request, *args, **kwargs)

            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return permission_denied_response(
                    title="Access Denied",
                    message="You do not have the required permissions for this action."
                )
            return redirect('dashboard:index')
        return _wrapped_view
    return decorator

# Aliases for convenience
role_required = allowed_roles

def admin_required(view_func):
    """Shorthand for requiring the ADMIN role."""
    return allowed_roles(['ADMIN'])(view_func)

def manager_or_admin_required(view_func):
    """Shorthand for requiring MANAGER or ADMIN roles."""
    return allowed_roles(['ADMIN', 'MANAGER'])(view_func)

manager_or_above_required = manager_or_admin_required

def supervisor_or_above_required(view_func):
    """Shorthand for requiring SUPERVISOR, MANAGER, or ADMIN roles."""
    return allowed_roles(['ADMIN', 'MANAGER', 'SUPERVISOR'])(view_func)

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
