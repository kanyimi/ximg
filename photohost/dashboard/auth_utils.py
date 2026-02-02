# dashboard/auth_utils.py
from functools import wraps
from django.shortcuts import redirect
from django.urls import reverse


def staff_required(user):
    return user.is_authenticated and user.is_staff


def dashboard_2fa_required(view_func):
    """
    - Requires authenticated + staff
    - If user has 2FA enabled, requires session flag dashboard_2fa_ok = True
    """
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        user = request.user
        if not user.is_authenticated:
            return redirect(reverse("dashboard:login"))
        if not user.is_staff:
            return redirect(reverse("dashboard:login"))

        prof = getattr(user, "dashboard_profile", None)
        if prof and prof.totp_enabled:
            if not request.session.get("dashboard_2fa_ok", False):
                return redirect(reverse("dashboard:twofa_verify"))

        return view_func(request, *args, **kwargs)

    return _wrapped
