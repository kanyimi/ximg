from django.contrib import admin
from .models import SecretNote


@admin.register(SecretNote)
class SecretNoteAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "delete_after_read",
        "expires_at",
        "created_at",
    )

    readonly_fields = (
        "id",
        "ciphertext",
        "created_at",
    )

    ordering = ("-created_at",)
