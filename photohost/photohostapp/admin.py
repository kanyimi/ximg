from django.contrib import admin
from .models import Section, StoredFile


@admin.register(Section)
class SectionAdmin(admin.ModelAdmin):
    list_display = ("slug", "title", "created_at", "lifetime_days", "expires_at", "is_expired")
    search_fields = ("slug", "title")
    list_filter = ("created_at", "lifetime_days")
    readonly_fields = ("created_at", "expires_at", "slug")


@admin.register(StoredFile)
class StoredFileAdmin(admin.ModelAdmin):
    list_display = ("original_name", "section", "uploaded_at")
    search_fields = ("original_name", "section__slug")
    list_filter = ("uploaded_at",)
    readonly_fields = ("uploaded_at",)
