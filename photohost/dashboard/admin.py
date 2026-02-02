from django.contrib import admin
from .models import ReadOnceNoteRetention, FlaggedSecretNote, DashboardProfile


@admin.register(ReadOnceNoteRetention)
class ReadOnceNoteRetentionAdmin(admin.ModelAdmin):
    list_display = (
        "note_id",
        "expires_at",
        "created_at",
    )

    readonly_fields = (
        "id",
        "cyphertext",
        "created_at",
    )

    ordering = ("-created_at",)




@admin.register(FlaggedSecretNote)
class FlaggedSecretNoteAdmin(admin.ModelAdmin):
    list_display = ("note_id", "matched_terms", "created_at")
    list_filter = ("created_at",)
    search_fields = ("note_id", "matched_terms", "ciphertext")
    ordering = ("-created_at",)
    readonly_fields = ("note_id", "created_at")


@admin.register(DashboardProfile)
class DashboardProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "totp_enabled")
    search_fields = ("user__username", "user__email")