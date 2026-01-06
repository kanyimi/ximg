from django.utils import timezone
from .models import SecretNote

SecretNote.objects.filter(
    expires_at__lt=timezone.now()
).delete()
