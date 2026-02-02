
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.db import transaction
from django.utils import timezone
from .models import SecretNote
import logging

logger = logging.getLogger(__name__)


@receiver(pre_save, sender=SecretNote)
def cleanup_expired_on_save(sender, instance, **kwargs):
    """Delete expired sections before saving new ones"""
    # Run cleanup in the background
    from django.db import connection
    with connection.cursor() as cursor:
        # Find and delete expired sections
        expired_ids = []
        for secretNote in SecretNote.objects.all():
            if secretNote.is_expired():
                expired_ids.append(secretNote.id)

        if expired_ids:
            SecretNote.objects.filter(id__in=expired_ids).delete()
            logger.info(f"Cleaned up {len(expired_ids)} expired secretNote")


