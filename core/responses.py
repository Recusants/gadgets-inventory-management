"""
Uniform JSON Response Helpers for 21 Void Technologies.
Every AJAX response adheres strictly to the uniform JSON envelope contract:
{
    "title": str,
    "message": str,
    "icon": "success" | "error" | "warning" | "info" | "question",
    "data": dict | list | str | None,
    "pagination": dict | None,
    "errors": dict | None
}
"""

from django.http import JsonResponse

def json_response(title, message, icon="info", data=None, pagination=None, errors=None, status=200):
    """Base helper to construct the uniform JSON envelope."""
    payload = {
        "status": "success" if icon == "success" else ("error" if icon == "error" else icon),
        "title": title,
        "message": message,
        "icon": icon,
        "data": data,
        "pagination": pagination,
        "errors": errors or {}
    }
    return JsonResponse(payload, status=status)

def success_response(title="Success", message="Operation completed successfully", data=None, pagination=None, status=200):
    """Canonical success response."""
    return json_response(
        title=title,
        message=message,
        icon="success",
        data=data,
        pagination=pagination,
        errors=None,
        status=status
    )

def error_response(title="Error", message="An error occurred", errors=None, data=None, status=400):
    """Canonical validation or general error response."""
    return json_response(
        title=title,
        message=message,
        icon="error",
        data=data,
        pagination=None,
        errors=errors or {},
        status=status
    )

def warning_response(title="Warning", message="Please review the warning", data=None, status=200):
    """Canonical warning response."""
    return json_response(
        title=title,
        message=message,
        icon="warning",
        data=data,
        pagination=None,
        errors=None,
        status=status
    )

def permission_denied_response(title="Access Denied", message="You do not have permission to perform this action."):
    """Canonical permission failure response."""
    return json_response(
        title=title,
        message=message,
        icon="error",
        data=None,
        pagination=None,
        errors=None,
        status=403
    )

def server_error_response(title="Server Error", message="An unexpected server error occurred. Please contact your administrator."):
    """Canonical 500 server failure response."""
    return json_response(
        title=title,
        message=message,
        icon="error",
        data=None,
        pagination=None,
        errors=None,
        status=500
    )
