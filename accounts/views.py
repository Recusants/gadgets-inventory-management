"""
Function-Based Views for Authentication and User Management.
Strictly zero Django Forms, 100% FBVs, uniform JSON envelope responses.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.views.decorators.http import require_POST, require_GET
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q

from .models import User, UserRole
from core.validators import validate_login, validate_user
from core.responses import success_response, error_response, permission_denied_response
from core.decorators import admin_required, ajax_required


# ==============================================================================
# AUTHENTICATION (LOGIN & LOGOUT)
# ==============================================================================

def login_view(request):
    """
    Renders login screen on GET; processes credentials via AJAX on POST.
    """
    if request.user.is_authenticated:
        return redirect('dashboard:index')

    is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'

    if request.method == 'POST':
        errors = validate_login(request.POST)
        if errors:
            if is_ajax:
                return error_response(
                    title="Login Failed",
                    message="Please enter your username and password.",
                    errors=errors
                )
            return render(request, 'accounts/login.html', {'errors': errors})

        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()
        user = authenticate(request, username=username, password=password)

        if user is not None:
            if not user.is_active:
                if is_ajax:
                    return error_response(
                        title="Account Disabled",
                        message="Your account has been deactivated. Contact an administrator.",
                        status=403
                    )
                return render(request, 'accounts/login.html', {
                    'general_error': "Your account has been deactivated. Contact an administrator."
                })

            login(request, user)
            if is_ajax:
                return success_response(
                    title="Welcome Back!",
                    message=f"Logged in as {user.get_full_name() or user.username}",
                    data={"redirect_url": "/"}
                )
            return redirect('dashboard:index')
        else:
            if is_ajax:
                return error_response(
                    title="Invalid Credentials",
                    message="Incorrect username or password. Please try again.",
                    errors={"password": "Username and password do not match our records."},
                    status=401
                )
            return render(request, 'accounts/login.html', {
                'general_error': "Incorrect username or password. Please try again."
            })

    return render(request, 'accounts/login.html')



def logout_view(request):
    """Logs user out and redirects to login screen."""
    logout(request)
    return redirect('accounts:login')


# ==============================================================================
# USER MANAGEMENT (ADMIN ONLY)
# ==============================================================================

@admin_required
def user_list_view(request):
    """Render User Management page shell (Admin only) with stats and initial table pre-rendered."""
    roles = UserRole.choices
    all_users = User.objects.all()
    stats = {
        'total': all_users.count(),
        'admins': all_users.filter(role=UserRole.ADMIN).count(),
        'managers': all_users.filter(role=UserRole.MANAGER).count(),
        'staff': all_users.filter(role=UserRole.STAFF).count(),
        'active': all_users.filter(is_active=True).count(),
        'inactive': all_users.filter(is_active=False).count(),
    }
    queryset = all_users.order_by('-date_joined')
    paginator = Paginator(queryset, 12)
    users = paginator.page(1)
    return render(request, 'accounts/user_list.html', {
        'roles': roles,
        'users': users,
        'paginator': paginator,
        'total_count': paginator.count,
        'stats': stats,
    })


@admin_required
def user_table_partial(request):
    """Return User table body and pagination partial with search and filters."""
    query = request.GET.get('q', '').strip()
    role = request.GET.get('role', '').strip()
    status = request.GET.get('status', '').strip().lower()
    page_num = request.GET.get('page', 1)

    queryset = User.objects.all().order_by('-date_joined')
    if query:
        queryset = queryset.filter(
            Q(username__icontains=query) |
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(email__icontains=query) |
            Q(phone__icontains=query)
        )
    if role and role in UserRole.values:
        queryset = queryset.filter(role=role)
    if status == 'active':
        queryset = queryset.filter(is_active=True)
    elif status == 'inactive':
        queryset = queryset.filter(is_active=False)

    paginator = Paginator(queryset, 12)
    try:
        users = paginator.page(page_num)
    except (PageNotAnInteger, EmptyPage):
        users = paginator.page(1)

    return render(request, 'accounts/partials/user_table.html', {
        'users': users,
        'paginator': paginator,
        'total_count': paginator.count,
    })


@admin_required
def user_add_modal(request):
    """Return Add User modal partial."""
    roles = UserRole.choices
    return render(request, 'accounts/partials/user_add_modal.html', {'roles': roles})


@admin_required
def user_edit_modal(request, pk):
    """Return Edit User modal partial."""
    user = get_object_or_404(User, pk=pk)
    roles = UserRole.choices
    return render(request, 'accounts/partials/user_edit_modal.html', {
        'target_user': user,
        'roles': roles,
    })


@require_POST
@admin_required
def user_create(request):
    """Create a new user with hashed password."""
    errors = validate_user(request.POST)
    if errors:
        return error_response(
            title="Validation Failed",
            message="Please resolve the errors highlighted below.",
            errors=errors
        )

    role = request.POST.get('role', UserRole.STAFF)
    user = User.objects.create_user(
        username=request.POST.get('username', '').strip(),
        password=request.POST.get('password', '').strip(),
        email=request.POST.get('email', '').strip(),
        first_name=request.POST.get('first_name', '').strip(),
        last_name=request.POST.get('last_name', '').strip(),
        role=role,
        phone=request.POST.get('phone', '').strip(),
        is_staff=True if role in (UserRole.ADMIN, UserRole.MANAGER) else False
    )

    return success_response(
        title="User Created",
        message=f'User account "{user.username}" ({user.get_role_display()}) created successfully.',
        data={"user_id": user.pk}
    )


@require_POST
@admin_required
def user_update(request, pk):
    """Update user profile and optionally change password."""
    user = get_object_or_404(User, pk=pk)
    errors = validate_user(request.POST, instance=user)
    if errors:
        return error_response(
            title="Validation Failed",
            message="Please resolve the errors highlighted below.",
            errors=errors
        )

    # Protect self from role downgrade away from ADMIN
    new_role = request.POST.get('role', user.role)
    if user.pk == request.user.pk and new_role != UserRole.ADMIN:
        return error_response(
            title="Action Blocked",
            message="You cannot downgrade your own administrator role.",
            status=400
        )

    # Active status handling
    is_active_val = request.POST.get('is_active')
    if is_active_val is not None:
        new_active = is_active_val in ('1', 'true', 'on', True)
        if user.pk == request.user.pk and not new_active:
            return error_response(
                title="Action Blocked",
                message="You cannot deactivate your own active administrator account.",
                status=400
            )
        user.is_active = new_active

    user.first_name = request.POST.get('first_name', '').strip()
    user.last_name = request.POST.get('last_name', '').strip()
    user.email = request.POST.get('email', '').strip()
    user.phone = request.POST.get('phone', '').strip()
    user.role = new_role
    user.is_staff = True if user.role in (UserRole.ADMIN, UserRole.MANAGER) else False

    # Optional password change
    new_password = request.POST.get('password', '').strip()
    if new_password:
        user.set_password(new_password)

    user.save()

    return success_response(
        title="User Updated",
        message=f'User account "{user.username}" updated successfully.',
        data={"user_id": user.pk}
    )


@require_POST
@admin_required
def user_toggle_status(request, pk):
    """Toggle user active / inactive status."""
    if request.user.pk == pk:
        return error_response(
            title="Action Blocked",
            message="You cannot deactivate your own active administrator account.",
            status=400
        )

    user = get_object_or_404(User, pk=pk)
    user.is_active = not user.is_active
    user.save(update_fields=['is_active'])

    state_str = "activated" if user.is_active else "deactivated"
    return success_response(
        title="Status Changed",
        message=f'User account "{user.username}" has been {state_str}.',
        data={"user_id": user.pk, "is_active": user.is_active}
    )


@require_POST
@admin_required
def user_delete(request, pk):
    """Delete user account (prevents deleting oneself)."""
    if request.user.pk == pk:
        return error_response(
            title="Action Blocked",
            message="You cannot delete your own active administrator account.",
            status=400
        )

    user = get_object_or_404(User, pk=pk)
    uname = user.username
    user.delete()

    return success_response(
        title="User Deleted",
        message=f'User account "{uname}" has been deleted.'
    )
