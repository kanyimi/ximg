from django.db import models
from django.utils import timezone
from django.utils.crypto import get_random_string
import uuid
from django.contrib.auth.hashers import make_password, check_password
class Section(models.Model):
    title = models.CharField(max_length=200, blank=True)
    slug = models.SlugField(unique=True, max_length=32, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    lifetime_days = models.PositiveSmallIntegerField(default=7)
    keep_original_filenames = models.BooleanField(default=False)
    batch_id = models.UUIDField(null=True, blank=True, db_index=True)

    password_hash = models.CharField(
        max_length=128,
        blank=True,
        default=""
    )

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = get_random_string(8)
        super().save(*args, **kwargs)

    @property
    def is_password_protected(self):
        return bool(self.password_hash)

    def set_section_password(self, raw_password):
        self.password_hash = (
            make_password(raw_password) if raw_password else ""
        )

    def check_section_password(self, raw_password):
        if not self.password_hash:
            return True
        return check_password(raw_password, self.password_hash)

    @property
    def expires_at(self):
        return self.created_at + timezone.timedelta(
            days=self.lifetime_days
        )

    def is_expired(self):
        exp = self.expires_at

        if timezone.is_naive(exp):
            exp = timezone.make_aware(
                exp,
                timezone.get_current_timezone()
            )

        return timezone.now() >= exp

    def __str__(self):
        return f"Section {self.slug}"

def upload_to(instance, filename):
    ext = filename.rsplit(".", 1)[-1] if "." in filename else ""

    if instance.section.keep_original_filenames:
        final_name = filename
    else:
        final_name = f"{uuid.uuid4().hex}.{ext}" if ext else uuid.uuid4().hex

    return f"sections/{instance.section.slug}/{final_name}"

class StoredFile(models.Model):
    section = models.ForeignKey(Section, related_name="files", on_delete=models.CASCADE)
    original_name = models.CharField(max_length=512)
    file = models.FileField(upload_to=upload_to)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    coordinates = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return self.original_name




