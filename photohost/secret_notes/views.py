from django.utils.translation import gettext as _
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from datetime import timedelta
from .models import SecretNote
from .crypto import encrypt_text, decrypt_text


def create(request):
    if request.method == "POST":
        text = request.POST["text"]
        expiry = request.POST["expiry"]
        password = request.POST.get("password", "").strip()

        delete_after_read = expiry == "read"
        expires_at = None

        if expiry == "1d":
            expires_at = timezone.now() + timedelta(days=1)
        elif expiry == "3d":
            expires_at = timezone.now() + timedelta(days=3)
        elif expiry == "1w":
            expires_at = timezone.now() + timedelta(weeks=1)
        elif expiry == "2w":
            expires_at = timezone.now() + timedelta(weeks=2)
        elif expiry == "1m":
            expires_at = timezone.now() + timedelta(days=30)
        elif expiry == "2m":
            expires_at = timezone.now() + timedelta(days=60)

        note = SecretNote.objects.create(
            ciphertext=encrypt_text(text),
            delete_after_read=delete_after_read,
            expires_at=expires_at,
        )

        # Set password if provided
        if password:
            note.set_password(password)
            note.save()

        return redirect("secret_notes:created", note.id)

    return render(request, "secret_notes/create.html")

def view_note(request, note_id):
    try:
        note = SecretNote.objects.get(id=note_id)
    except SecretNote.DoesNotExist:
        # Show deleted page instead of 404
        return render(
            request,
            "secret_notes/deleted.html",
            status=410  # HTTP 410 Gone (correct semantics)
        )

    # Check if note has expired
    if note.expires_at and timezone.now() > note.expires_at:
        note.delete()
        return render(
            request,
            "secret_notes/deleted.html",
            status=410
        )

    # Check for confirmation parameter for delete-after-read notes
    if note.delete_after_read and not request.GET.get('confirm') == 'true':
        # Show confirmation page before showing password form or note
        if note.has_password:
            # Will show password form after confirmation
            return render(
                request,
                "secret_notes/confirm_read.html",
                {
                    "note_id": note_id,
                    "has_password": True,
                    "message": "This note is password protected and will self-destruct after reading."
                }
            )
        else:
            # No password, just confirmation
            return render(
                request,
                "secret_notes/confirm_read.html",
                {
                    "note_id": note_id,
                    "has_password": False,
                    "message": "This note will self-destruct after reading."
                }
            )

    # Check if password is required
    if note.has_password:
        if request.method == "POST":
            password = request.POST.get("password", "")
            if note.check_password(password):
                # Password correct, show note
                return _decrypt_and_show_note(request, note)
            else:
                # Wrong password
                return render(
                    request,
                    "secret_notes/password.html",
                    {
                        "note_id": note_id,
                        "error": "Invalid password. Please try again.",
                        "delete_after_read": note.delete_after_read
                    },
                    status=403
                )
        else:
            # Show password form
            return render(
                request,
                "secret_notes/password.html",
                {
                    "note_id": note_id,
                    "delete_after_read": note.delete_after_read
                }
            )
    else:
        # No password required
        return _decrypt_and_show_note(request, note)


def _decrypt_and_show_note(request, note):
    """Helper function to decrypt and display note"""
    try:
        text = decrypt_text(note.ciphertext)
    except Exception:
        return render(
            request,
            "secret_notes/error.html",
            {"message": "Unable to decrypt this note."}
        )

    # Delete-after-read logic
    if note.delete_after_read:
        note.delete()

    return render(
        request,
        "secret_notes/view.html",
        {"text": text}
    )
def created(request, note_id):
    # We need to handle the case where the note might have been deleted
    # (e.g., if someone visits the created page after the note expired)
    try:
        note = SecretNote.objects.get(id=note_id)
        return render(request, "secret_notes/created.html", {"note": note})
    except SecretNote.DoesNotExist:
        return render(
            request,
            "secret_notes/deleted.html",
            {"message": "This note has already been deleted or expired."},
            status=410
        )