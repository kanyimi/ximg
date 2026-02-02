from django.conf import settings
import uuid
from django.db import models
from django.utils import timezone
class SiteVisit(models.Model):
    date = models.DateField(db_index=True)
    visitor_id = models.CharField(max_length=64, db_index=True)

    class Meta:
        unique_together = ("date", "visitor_id")

    def __str__(self):
        return f"{self.date} {self.visitor_id}"


class ReadOnceNoteRetention(models.Model):

    id = models.BigAutoField(primary_key=True)

    note_id = models.UUIDField(db_index=True)  # the SecretNote.id
    cyphertext = models.TextField()

    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(db_index=True)

    # optional metadata (helpful in dashboard)
    had_password = models.BooleanField(default=False)

    def is_expired(self) -> bool:
        exp = self.expires_at
        if timezone.is_naive(exp):
            exp = timezone.make_aware(exp, timezone.get_current_timezone())
        return timezone.now() >= exp

    def __str__(self):
        return f"Retention copy for {self.note_id}"


class FlaggedSecretNote(models.Model):
    note_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ciphertext = models.TextField()
    matched_terms = models.CharField(max_length=500)  # e.g. "OMG, Мега"
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"FlaggedSecretNote {self.note_id} ({self.matched_terms})"




class DashboardProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="dashboard_profile")
    totp_secret = models.CharField(max_length=64, blank=True, default="")
    totp_enabled = models.BooleanField(default=False)

    def __str__(self):
        return f"DashboardProfile({self.user.username})"

