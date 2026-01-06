from django.db import models
from django.utils import timezone
from django.utils.crypto import get_random_string
import uuid

class Section(models.Model):
    title = models.CharField(max_length=200, blank=True)
    slug = models.SlugField(unique=True, max_length=32, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    lifetime_days = models.PositiveSmallIntegerField(default=7)
    keep_original_filenames = models.BooleanField(default=False)
    batch_id = models.UUIDField(null=True, blank=True, db_index=True)
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = get_random_string(8)
        super().save(*args, **kwargs)

    @property
    def expires_at(self):
        return self.created_at + timezone.timedelta(days=self.lifetime_days)

    def is_expired(self):
        exp = self.expires_at

        # Normalize timezone safety
        if timezone.is_naive(exp):
            exp = timezone.make_aware(exp, timezone.get_current_timezone())

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


