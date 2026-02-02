# dashboard/signals.py

import logging
from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.utils import timezone

from .models import ReadOnceNoteRetention

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
