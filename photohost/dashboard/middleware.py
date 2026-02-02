import hashlib
from django.utils import timezone
from .models import SiteVisit

class SimpleVisitorCounterMiddleware:
    """
    Very simple unique visitor counter per day.
    Uses a hash of IP + User-Agent. (Good enough for your requirement.)
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Avoid counting admin/static/media
        path = request.path or ""
        if path.startswith("/static/") or path.startswith("/media/") or path.startswith("/admin/"):
            return self.get_response(request)

        ip = request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[0].strip() or request.META.get("REMOTE_ADDR", "")
        ua = request.META.get("HTTP_USER_AGENT", "")
        raw = f"{ip}|{ua}".encode("utf-8", errors="ignore")
        visitor_id = hashlib.sha256(raw).hexdigest()[:64]

        today = timezone.localdate()
        try:
            SiteVisit.objects.get_or_create(date=today, visitor_id=visitor_id)
        except Exception:
            # Don't ever break requests because of counter
            pass

        return self.get_response(request)
