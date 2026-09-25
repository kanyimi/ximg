# dashboard/signals.py

import logging
from django.db.models.signals import pre_save, pre_delete, post_save
from django.dispatch import receiver
from django.utils import timezone

from photohostapp.models import (
    StoredFile,
    Section
)
from secret_notes.models import SecretNote
from .models import ReadOnceNoteRetention, DashboardContentStat

logger = logging.getLogger(__name__)


@receiver(pre_save, sender=ReadOnceNoteRetention)
def cleanup_expired_on_save(sender, instance, **kwargs):
    """Delete expired retention notes before saving new ones"""
    # Run cleanup "in the background" style (same pattern as your Section signal)
    from django.db import connection

    with connection.cursor() as cursor:
        # Find and delete expired retention copies
        expired_ids = []
        now = timezone.now()

        # Only check rows that could be expired (fast filter)
        for r in ReadOnceNoteRetention.objects.filter(expires_at__isnull=False, expires_at__lte=now):
            expired_ids.append(r.id)

        if expired_ids:
            ReadOnceNoteRetention.objects.filter(id__in=expired_ids).delete()
            logger.info(f"Cleaned up {len(expired_ids)} expired retention copies")



@receiver(post_save, sender=StoredFile)
def track_stored_file_created(sender, instance, created, **kwargs):
    if not created:
        return

    DashboardContentStat.objects.get_or_create(
        content_type=DashboardContentStat.CONTENT_FILE,
        object_id=str(instance.pk),
        defaults={
            "created_at": instance.uploaded_at,
        },
    )


@receiver(pre_delete, sender=StoredFile)
def track_stored_file_deleted(sender, instance, **kwargs):
    stat, _ = DashboardContentStat.objects.get_or_create(
        content_type=DashboardContentStat.CONTENT_FILE,
        object_id=str(instance.pk),
        defaults={
            "created_at": instance.uploaded_at,
        },
    )

    if stat.deleted_at is None:
        stat.deleted_at = timezone.now()
        stat.save(update_fields=["deleted_at"])

@receiver(post_save, sender=Section)
def track_section_created(sender, instance, created, **kwargs):
    if not created:
        return

    DashboardContentStat.objects.get_or_create(
        content_type=DashboardContentStat.CONTENT_SECTION,
        object_id=str(instance.pk),
        defaults={
            "created_at": instance.created_at,
        },
    )


@receiver(pre_delete, sender=Section)
def track_section_deleted(sender, instance, **kwargs):
    stat, _ = DashboardContentStat.objects.get_or_create(
        content_type=DashboardContentStat.CONTENT_SECTION,
        object_id=str(instance.pk),
        defaults={
            "created_at": instance.created_at,
        },
    )

    if stat.deleted_at is None:
        stat.deleted_at = timezone.now()
        stat.save(update_fields=["deleted_at"])

@receiver(post_save, sender=SecretNote)
def track_secret_note_created(sender, instance, created, **kwargs):
    if not created:
        return

    DashboardContentStat.objects.get_or_create(
        content_type=DashboardContentStat.CONTENT_NOTE,
        object_id=str(instance.pk),
        defaults={
            "created_at": instance.created_at,
        },
    )


@receiver(pre_delete, sender=SecretNote)
def track_secret_note_deleted(sender, instance, **kwargs):
    stat, _ = DashboardContentStat.objects.get_or_create(
        content_type=DashboardContentStat.CONTENT_NOTE,
        object_id=str(instance.pk),
        defaults={
            "created_at": instance.created_at,
        },
    )

    if stat.deleted_at is None:
        stat.deleted_at = timezone.now()
        stat.save(update_fields=["deleted_at"])