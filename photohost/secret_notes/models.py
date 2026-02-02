import uuid
from django.db import models
from django.utils import timezone
from django.contrib.auth.hashers import make_password, check_password


class SecretNote(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    ciphertext = models.TextField()
    delete_after_read = models.BooleanField(default=False)
    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    has_password = models.BooleanField(default=False)
    password_hash = models.CharField(max_length=255, null=True, blank=True)

    def set_password(self, raw_password):
        """Hash and store the password"""
        if raw_password:
            self.password_hash = make_password(raw_password)
            self.has_password = True
        else:
            self.password_hash = None
            self.has_password = False

    def check_password(self, raw_password):
        """Verify the password"""
        if not self.has_password or not self.password_hash:
            return True  # No password set, always valid
        return check_password(raw_password, self.password_hash)


    def is_expired(self) -> bool:
        """
        Returns True if the note has an expires_at and it's in the past.
        If expires_at is None => not expired.
        """
        if not self.expires_at:
            return False

        exp = self.expires_at
        if timezone.is_naive(exp):
            exp = timezone.make_aware(exp, timezone.get_current_timezone())
        return timezone.now() >= exp