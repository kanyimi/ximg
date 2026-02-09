from datetime import datetime, timedelta
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import render, redirect
from django.utils import timezone
from django.http import HttpResponseBadRequest
from django.db.models import Q
from photohostapp.models import Section, StoredFile
from secret_notes.models import SecretNote
from .models import SiteVisit,  ReadOnceNoteRetention, FlaggedSecretNote, DashboardProfile
from django.http import JsonResponse
from .auth_utils import dashboard_2fa_required, staff_required
# Import here to avoid circular import problems
from secret_notes.crypto import decrypt_text
from django.contrib import messages
import base64
import io
import pyotp
import qrcode
import os
import platform
import shutil
from django.conf import settings
import mimetypes
from django.http import Http404, FileResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_GET
from django.core.paginator import Paginator

def _parse_range(request):
    """
    Accepts:
      ?start=YYYY-MM-DD&end=YYYY-MM-DD
    end is inclusive in UI, but we convert to [start, end+1day) for filtering.
    """
    start_s = request.GET.get("start")
    end_s = request.GET.get("end")

    if not start_s or not end_s:
        # default: last 7 days inclusive
        end = timezone.localdate()
        start = end - timedelta(days=6)
        return start, end

    try:
        start = datetime.strptime(start_s, "%Y-%m-%d").date()
        end = datetime.strptime(end_s, "%Y-%m-%d").date()
    except ValueError:
        raise ValueError("Invalid date format. Use YYYY-MM-DD")

    if start > end:
        raise ValueError("Start date cannot be after end date")

    return start, end


def _dt_bounds(start_date, end_date):
    tz = timezone.get_current_timezone()
    start_dt = timezone.make_aware(datetime.combine(start_date, datetime.min.time()), tz)
    # end inclusive -> convert to end+1 day exclusive
    end_dt = timezone.make_aware(datetime.combine(end_date + timedelta(days=1), datetime.min.time()), tz)
    return start_dt, end_dt

def _fmt_bytes(num: int) -> str:
    # 1024-based (KiB, MiB...) but with friendly labels
    step = 1024.0
    for unit in ["B", "KB", "MB", "GB", "TB", "PB"]:
        if num < step:
            return f"{num:.0f} {unit}" if unit == "B" else f"{num:.2f} {unit}"
        num /= step
    return f"{num:.2f} EB"

def _get_server_stats():
    # Disk stats: use MEDIA_ROOT if set, else project base dir
    disk_path = getattr(settings, "BASE_DIR", ".")
    du = shutil.disk_usage(disk_path)

    disk_total = du.total
    disk_used = du.used
    disk_free = du.free
    disk_used_pct = round((disk_used / disk_total) * 100, 1) if disk_total else 0.0

    stats = {
        "os": f"{platform.system()} {platform.release()}",
        "python": platform.python_version(),
        "disk_path": str(disk_path),
        "disk_total": _fmt_bytes(disk_total),
        "disk_used": _fmt_bytes(disk_used),
        "disk_free": _fmt_bytes(disk_free),
        "disk_used_pct": disk_used_pct,
    }

    # Optional: psutil gives CPU/RAM/uptime (works on Windows + Linux)
    try:
        import psutil

        # CPU
        cpu_percent = psutil.cpu_percent(interval=0.2)
        cpu_count = psutil.cpu_count(logical=True) or 0

        # RAM
        vm = psutil.virtual_memory()
        ram_total = vm.total
        ram_used = vm.used
        ram_available = vm.available
        ram_used_pct = round(vm.percent, 1)

        # Uptime
        boot = timezone.datetime.fromtimestamp(psutil.boot_time(), tz=timezone.get_current_timezone())
        uptime_td = timezone.now() - boot

        stats.update({
            "cpu_percent": round(cpu_percent, 1),
            "cpu_count": cpu_count,
            "ram_total": _fmt_bytes(ram_total),
            "ram_used": _fmt_bytes(ram_used),
            "ram_available": _fmt_bytes(ram_available),
            "ram_used_pct": ram_used_pct,
            "uptime": str(timedelta(seconds=int(uptime_td.total_seconds()))),
        })

    except Exception:
        # If psutil isn't installed or fails, we still have disk + OS/Python
        stats.update({
            "cpu_percent": None,
            "cpu_count": None,
            "ram_total": None,
            "ram_used": None,
            "ram_available": None,
            "ram_used_pct": None,
            "uptime": None,
        })

    # Load average (Linux/macOS only)
    try:
        la = os.getloadavg()  # (1, 5, 15)
        stats["loadavg"] = f"{la[0]:.2f}, {la[1]:.2f}, {la[2]:.2f}"
    except Exception:
        stats["loadavg"] = None

    return stats

def _parse_ddmmyyyy(s: str):
    s = (s or "").strip()
    try:
        return datetime.strptime(s, "%d.%m.%Y").date()
    except ValueError:
        return None
def login_view(request):
    if request.user.is_authenticated and request.user.is_staff:
        # If already logged in, go to OTP if needed else dashboard
        prof, _ = DashboardProfile.objects.get_or_create(user=request.user)
        if prof.totp_enabled and not request.session.get("dashboard_2fa_ok", False):
            return redirect("dashboard:twofa_verify")
        return redirect("dashboard:shell")

    if request.method == "POST":
        username = (request.POST.get("username") or "").strip()
        password = request.POST.get("password") or ""

        user = authenticate(request, username=username, password=password)
        if not user:
            messages.error(request, "Invalid username or password.")
            return render(request, "dashboard/login.html")

        if not user.is_staff:
            messages.error(request, "Access denied.")
            return render(request, "dashboard/login.html")

        login(request, user)

        # Reset 2FA flag each login
        request.session["dashboard_2fa_ok"] = False

        prof, _ = DashboardProfile.objects.get_or_create(user=user)
        if prof.totp_enabled:
            return redirect("dashboard:twofa_verify")

        # No 2FA enabled -> allow dashboard
        request.session["dashboard_2fa_ok"] = True
        return redirect("dashboard:shell")

    return render(request, "dashboard/login.html")


def logout_view(request):
    logout(request)
    request.session.pop("dashboard_2fa_ok", None)
    return redirect("dashboard:login")



def twofa_verify(request):
    if not request.user.is_authenticated:
        return redirect("dashboard:login")
    if not request.user.is_staff:
        return redirect("dashboard:login")

    prof, _ = DashboardProfile.objects.get_or_create(user=request.user)

    # If user doesn't have 2FA enabled, consider them verified
    if not prof.totp_enabled:
        request.session["dashboard_2fa_ok"] = True
        return redirect("dashboard:shell")

    if request.method == "POST":
        code = (request.POST.get("code") or "").strip().replace(" ", "")
        totp = pyotp.TOTP(prof.totp_secret)

        if totp.verify(code, valid_window=1):
            request.session["dashboard_2fa_ok"] = True
            return redirect("dashboard:shell")

        messages.error(request, "Invalid code. Try again.")

    return render(request, "dashboard/2fa_verify.html")


def twofa_page(request):
    return render(request, "dashboard/shell.html", {"initial_route": "twofa"})
@login_required
@user_passes_test(staff_required)
def twofa_partial(request):
    prof, _ = DashboardProfile.objects.get_or_create(user=request.user)

    # If already enabled, just show status + disable form (handled in template)
    # If disabled, we show setup inside this partial.

    qr_data_url = None
    secret = prof.totp_secret or ""

    if not prof.totp_enabled:
        # Generate secret if missing
        if not prof.totp_secret:
            prof.totp_secret = pyotp.random_base32()
            prof.save(update_fields=["totp_secret"])
            secret = prof.totp_secret

        # Build QR
        issuer = "Ximg Dashboard"
        label = request.user.username
        uri = pyotp.totp.TOTP(prof.totp_secret).provisioning_uri(
            name=label,
            issuer_name=issuer
        )

        qr = qrcode.QRCode(box_size=8, border=2)
        qr.add_data(uri)
        qr.make(fit=True)
        img = qr.make_image()

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        qr_b64 = base64.b64encode(buf.getvalue()).decode("ascii")
        qr_data_url = f"data:image/png;base64,{qr_b64}"

        # Enable flow (POST inside the partial)
        if request.method == "POST" and request.POST.get("action") == "enable":
            code = (request.POST.get("code") or "").strip().replace(" ", "")
            totp = pyotp.TOTP(prof.totp_secret)

            if totp.verify(code, valid_window=1):
                prof.totp_enabled = True
                prof.save(update_fields=["totp_enabled"])
                request.session["dashboard_2fa_ok"] = True
                messages.success(request, "2FA enabled.")
                return redirect("dashboard:twofa_page")  # or redirect back to shell route that loads 2fa
            else:
                messages.error(request, "Invalid code. 2FA not enabled.")

    return render(request, "dashboard/partials/twofa.html", {
        "totp_enabled": prof.totp_enabled,
        "has_secret": bool(prof.totp_secret),
        "secret": secret,
        "qr_data_url": qr_data_url,
    })
@dashboard_2fa_required
def twofa_disable(request):
    prof, _ = DashboardProfile.objects.get_or_create(user=request.user)

    if request.method == "POST":
        prof.totp_enabled = False
        prof.totp_secret = ""
        prof.save(update_fields=["totp_enabled", "totp_secret"])
        request.session["dashboard_2fa_ok"] = False
        messages.success(request, "2FA disabled.")
        return redirect("dashboard:twofa_page")

    return HttpResponseBadRequest("POST only")

@dashboard_2fa_required
def shell(request):
    # Dashboard container page (single page). Content is loaded via JS from partials.
    return render(request, "dashboard/shell.html")


@dashboard_2fa_required
def stats_page(request):
    # If someone opens /dashboard/stats/ directly, return the shell (JS will load stats)
    return render(request, "dashboard/shell.html", {"initial_route": "stats"})


@dashboard_2fa_required
def sections_page(request):
    return render(request, "dashboard/shell.html", {"initial_route": "sections"})


@dashboard_2fa_required
def files_page(request):
    return render(request, "dashboard/shell.html", {"initial_route": "files"})


@dashboard_2fa_required
def stats_partial(request):
    try:
        start, end = _parse_range(request)
    except ValueError as e:
        return HttpResponseBadRequest(str(e))

    start_dt, end_dt = _dt_bounds(start, end)

    files_count = StoredFile.objects.filter(uploaded_at__gte=start_dt, uploaded_at__lt=end_dt).count()
    sections_count = Section.objects.filter(created_at__gte=start_dt, created_at__lt=end_dt).count()
    notes_count = SecretNote.objects.filter(created_at__gte=start_dt, created_at__lt=end_dt).count()

    visitors_count = SiteVisit.objects.filter(date__gte=start, date__lte=end).values("visitor_id").distinct().count()

    server_stats = _get_server_stats()

    return render(request, "dashboard/partials/stats.html", {
        "start": start,
        "end": end,
        "files_count": files_count,
        "sections_count": sections_count,
        "notes_count": notes_count,
        "visitors_count": visitors_count,
        "server_stats": server_stats,
    })



@dashboard_2fa_required
def secret_notes_page(request):
    return render(request, "dashboard/shell.html", {"initial_route": "secret-notes"})



@require_GET
def preview_file(request, slug, file_id):
    stored_file = get_object_or_404(StoredFile, id=file_id, section__slug=slug)
    section = stored_file.section

    if section.is_expired():
        raise Http404("Section expired")

    content_type, _ = mimetypes.guess_type(stored_file.original_name or stored_file.file.name)
    if not content_type or not content_type.startswith("image/"):
        raise Http404("Not an image")

    resp = FileResponse(stored_file.file.open("rb"), content_type=content_type)
    resp["Content-Disposition"] = f'inline; filename="{stored_file.original_name}"'
    return resp

def download_file(request, slug, file_id):
    stored_file = get_object_or_404(StoredFile, id=file_id, section__slug=slug)
    section = stored_file.section

    if section.is_expired():
        raise Http404("Section expired")

    return FileResponse(
        stored_file.file.open("rb"),
        as_attachment=True,
        filename=stored_file.original_name,
    )

@dashboard_2fa_required
def files_partial(request):
    q = (request.GET.get("q") or "").strip()

    qs = StoredFile.objects.select_related("section").order_by("-uploaded_at")

    q_date = _parse_ddmmyyyy(q)

    if q:
        if q_date:
            # ✅ date search (Django handles TZ correctly)
            qs = qs.filter(uploaded_at__date=q_date)
        else:
            # ✅ text search
            qs = qs.filter(
                Q(original_name__icontains=q) |
                Q(section__slug__icontains=q) |
                Q(file__icontains=q)
            )

    # Exclude expired sections (python-side)
    valid_files = [f for f in qs if not f.section.is_expired()]

    paginator = Paginator(valid_files, 20)
    page_number = request.GET.get("page") or 1
    page_obj = paginator.get_page(page_number)

    return render(request, "dashboard/partials/files.html", {
        "q": q,
        "page_obj": page_obj,
        "files": page_obj.object_list,
    })


@dashboard_2fa_required
def sections_partial(request):
    q = (request.GET.get("q") or "").strip()
    q_low = q.lower()

    qs = Section.objects.all().order_by("-created_at")

    # Exclude expired (python-side)
    sections = [s for s in qs if not s.is_expired()]

    if q:
        q_date = _parse_ddmmyyyy(q)

        def match_section(s):
            # text match (slug/title)
            if q_low in (s.slug or "").lower() or q_low in (s.title or "").lower():
                return True

            # date match
            if q_date:
                # created_at date match
                if s.created_at and s.created_at.date() == q_date:
                    return True
                # expires_at property match
                exp = s.expires_at
                if exp and exp.date() == q_date:
                    return True
                return False

            # if query looks like dd.mm.yyyy string, match formatted dates too
            if len(q) == 10 and q[2] == "." and q[5] == ".":
                created_str = s.created_at.strftime("%d.%m.%Y") if s.created_at else ""
                expires_str = s.expires_at.strftime("%d.%m.%Y") if s.expires_at else ""
                return q == created_str or q == expires_str

            return False

        sections = [s for s in sections if match_section(s)]

    paginator = Paginator(sections, 20)
    page_number = request.GET.get("page") or 1
    page_obj = paginator.get_page(page_number)

    return render(request, "dashboard/partials/sections.html", {
        "q": q,
        "page_obj": page_obj,
        "sections": page_obj.object_list,
    })



@dashboard_2fa_required
def secret_notes_partial(request):
    q_raw = (request.GET.get("q") or "").strip()
    now = timezone.now()

    # keep current tab on reload
    tab = (request.GET.get("tab") or "active").strip()
    if tab not in ("active", "retention", "flagged"):
        tab = "active"

    # page params per tab
    page_active = request.GET.get("page_active") or 1
    page_retention = request.GET.get("page_retention") or 1
    page_flagged = request.GET.get("page_flagged") or 1

    # Base querysets
    notes_qs = (
        SecretNote.objects
        .filter(Q(expires_at__isnull=True) | Q(expires_at__gt=now))
        .order_by("-created_at")
    )

    retention_qs = (
        ReadOnceNoteRetention.objects
        .filter(expires_at__gt=now)
        .order_by("-created_at")
    )

    flagged_qs = FlaggedSecretNote.objects.order_by("-created_at")

    # ---- Search handling (text OR date dd.mm.yyyy) ----
    q_date = _parse_ddmmyyyy(q_raw)
    q = q_raw.lower()

    if q_raw:
        if q_date:
            # ✅ Date search
            # Active notes: created_at OR expires_at on that date
            notes_qs = notes_qs.filter(
                Q(created_at__date=q_date) |
                Q(expires_at__date=q_date)
            )

            # Retention: created_at OR expires_at on that date (still respects expires_at__gt=now base filter)
            retention_qs = retention_qs.filter(
                Q(created_at__date=q_date) |
                Q(expires_at__date=q_date)
            )

            # Flagged: created_at on that date
            flagged_qs = flagged_qs.filter(created_at__date=q_date)

        else:
            # ✅ Text search (existing behavior)
            notes_qs = notes_qs.filter(id__icontains=q)
            retention_qs = retention_qs.filter(note_id__icontains=q)
            flagged_qs = flagged_qs.filter(
                Q(note_id__icontains=q) | Q(matched_terms__icontains=q)
            )

    # ---- Paginate Active notes (no decrypt) ----
    notes_paginator = Paginator(notes_qs, 20)
    notes_page = notes_paginator.get_page(page_active)

    # ---- Paginate Retention (decrypt only on current page) ----
    retention_paginator = Paginator(retention_qs, 20)
    retention_page = retention_paginator.get_page(page_retention)

    retention_rows = []
    for r in retention_page.object_list:
        cipher = r.cyphertext or ""
        try:
            text = decrypt_text(cipher) if cipher else ""
        except Exception:
            text = "[Unable to decrypt]"

        preview = (text[:30] + "…") if len(text) > 30 else text
        retention_rows.append({
            "note_id": str(r.note_id),
            "created_at": r.created_at,
            "expires_at": r.expires_at,
            "had_password": r.had_password,
            "preview": preview,
            "plaintext": text,
        })

    # ---- Paginate Flagged (decrypt only on current page) ----
    flagged_paginator = Paginator(flagged_qs, 20)
    flagged_page = flagged_paginator.get_page(page_flagged)

    flagged_rows = []
    for f in flagged_page.object_list:
        cipher = f.ciphertext or ""
        try:
            text = decrypt_text(cipher) if cipher else ""
        except Exception:
            text = "[Unable to decrypt]"

        preview = (text[:30] + "…") if len(text) > 30 else text
        flagged_rows.append({
            "note_id": str(f.note_id),
            "created_at": f.created_at,
            "matched_terms": f.matched_terms,
            "preview": preview,
            "plaintext": text,
        })

    return render(request, "dashboard/partials/secret_notes.html", {
        "q": q_raw,
        "tab": tab,

        "notes_page": notes_page,
        "retention_page": retention_page,
        "flagged_page": flagged_page,

        "notes": list(notes_page.object_list),
        "retention_rows": retention_rows,
        "flagged_rows": flagged_rows,
    })

@dashboard_2fa_required
def api_secret_notes(request):
    """
    Returns:
    - current (not deleted) SecretNotes (excluding expired ones)
    - retention plaintext entries (not expired)
    """
    now = timezone.now()

    notes_qs = (
        SecretNote.objects
        .filter(Q(expires_at__isnull=True) | Q(expires_at__gt=now))
        .order_by("-created_at")
    )

    notes = []
    for n in notes_qs:
        notes.append({
            "id": str(n.id),
            "created_at": n.created_at.isoformat(),
            "expires_at": n.expires_at.isoformat() if n.expires_at else None,
            "delete_after_read": n.delete_after_read,
            "has_password": n.has_password,
        })

    retention_qs = (
        ReadOnceNoteRetention.objects
        .filter(expires_at__gt=now)
        .order_by("-created_at")
    )

    retention = []
    for r in retention_qs:
        retention.append({
            "note_id": str(r.note_id),
            "created_at": r.created_at.isoformat(),
            "expires_at": r.expires_at.isoformat(),
            "had_password": r.had_password,
            # show a safe preview (you can remove preview if you want)
            "preview": (r.plaintext[:120] + "…") if len(r.plaintext) > 120 else r.plaintext,
            "plaintext": r.plaintext,  # include only if you REALLY want full text in dashboard
        })

    return JsonResponse({"notes": notes, "retention": retention})