from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, Http404, FileResponse, JsonResponse, StreamingHttpResponse
from django.views.decorators.http import require_http_methods, require_GET
from .forms import SectionCreateForm, ImageUploadForm
from .models import Section, StoredFile
from .utils import remove_exif_and_get_file
from django.contrib import messages
import io
import zipfile
import os
import uuid
import mimetypes
from django.views.decorators.cache import never_cache
from django.utils.crypto import salted_hmac
from django.urls import reverse

MAX_SECTION_SIZE_MB = 300
MAX_SECTION_SIZE_BYTES = MAX_SECTION_SIZE_MB * 1024 * 1024

# @require_GET
# def view_file(request, slug, file_id):
#
#     stored_file = get_object_or_404(
#         StoredFile.objects.select_related("section"),
#         id=file_id,
#         section__slug=slug
#     )
#
#     section = stored_file.section
#
#     if section.is_expired():
#         raise Http404("Section expired")
#
#     if not has_section_access(request, section):
#         return redirect(
#             "photohostapp:section_password",
#             slug=section.slug
#         )
#
#     import mimetypes
#
#     content_type, _ = mimetypes.guess_type(
#         stored_file.original_name
#     )
#
#     response = FileResponse(
#         stored_file.file.open("rb"),
#         content_type=content_type or "application/octet-stream",
#         as_attachment=False
#     )
#
#     response["Cache-Control"] = "private, no-store"
#     response["X-Content-Type-Options"] = "nosniff"
#
#     return response
def section_access_key(section):
    return f"section_access_{section.pk}"


def section_access_signature(section):
    return salted_hmac(
        "photohostapp.section_access",
        f"{section.pk}:{section.password_hash}"
    ).hexdigest()


def has_section_access(request, section):
    if not section.is_password_protected:
        return True

    return (
        request.session.get(section_access_key(section))
        == section_access_signature(section)
    )


@never_cache
@require_http_methods(["GET", "POST"])
def section_password(request, slug):

    section = get_object_or_404(Section, slug=slug)

    if section.is_expired():
        return render(request, "404.html", status=404)

    if not section.is_password_protected:
        return redirect("photohostapp:section_detail", slug=slug)

    if has_section_access(request, section):
        return redirect("photohostapp:section_detail", slug=slug)

    error = None

    if request.method == "POST":

        password = request.POST.get("password", "")

        if section.check_section_password(password):

            request.session[section_access_key(section)] = (
                section_access_signature(section)
            )

            return redirect(
                "photohostapp:section_detail",
                slug=slug
            )

        error = "Incorrect password. Please try again."

    return render(
        request,
        "photohostapp/section_password.html",
        {
            "section": section,
            "error": error
        }
    )

@require_http_methods(["GET", "POST"])
def create_section_and_upload(request):
    if request.method == "POST":
        sform = SectionCreateForm(request.POST)

        if sform.is_valid():
            files = request.FILES.getlist("files")

            if not files:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'status': 'error', 'message': 'No files selected.'}, status=400)
                messages.error(request, "No files selected.")
                return redirect("photohostapp:create")

            total_size = sum(f.size for f in files)
            if total_size > MAX_SECTION_SIZE_BYTES:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'status': 'error', 'message': 'Total upload size must not exceed 300 MB.'}, status=400)
                messages.error(request, "Total upload size must not exceed 300 MB.")
                return redirect("photohostapp:create")

            # Always create ONE section (album)
            section = sform.save()

            for f in files:
                processed_name, content = remove_exif_and_get_file(f)

                sf = StoredFile(section=section)

                # Save using ORIGINAL filename input, so upload_to() can decide UUID vs original
                sf.file.save(f.name, content, save=True)

                # NOW decide what to store in DB for "original_name"
                if section.keep_original_filenames:
                    sf.original_name = os.path.basename(f.name)  # keep original
                else:
                    sf.original_name = os.path.basename(sf.file.name)  # store UUID name

                sf.save(update_fields=["original_name"])

            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'status': 'success',
                    'message': 'Files uploaded successfully.',
                    'redirect_url': reverse('photohostapp:section_detail', kwargs={'slug': section.slug})
                })

            messages.success(request, "Files uploaded successfully.")
            return redirect("photohostapp:section_detail", slug=section.slug)

        # Form validation failed
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'status': 'error',
                'message': 'Form validation failed.',
                'errors': sform.errors
            }, status=400)

    # GET
    sform = SectionCreateForm()
    return render(request, "photohostapp/upload.html", {"sform": sform})


def section_detail(request, slug):
    try:
        section = Section.objects.get(slug=slug)
    except Section.DoesNotExist:
        return render(request, "404.html", status=404)

    if section.is_expired():
        return render(request, "404.html", status=404)

    # NEW: Password protection
    if not has_section_access(request, section):
        return redirect(
            "photohostapp:section_password",
            slug=section.slug
        )

    image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.tiff'}

    files = []
    for f in section.files.all():
        name = getattr(f.file, 'name', '') or ''
        ext = os.path.splitext(name)[1].lower()
        mime, _ = mimetypes.guess_type(name)

        f.is_image = (mime and mime.startswith('image/')) or ext in image_extensions
        f.is_text = ext == '.txt'
        f.text_preview = ""

        if f.is_text:
            try:
                with open(f.file.path, "r", encoding="utf-8", errors="ignore") as fh:
                    f.text_preview = fh.read().strip()
            except Exception:
                pass

        files.append(f)

    return render(
        request,
        "photohostapp/section_detail.html",
        {
            "section": section,
            "files": files
        }
    )




def download_zip(request, slug):
    section = get_object_or_404(Section, slug=slug)
    if section.is_expired():
        raise Http404("Section expired")

    if not has_section_access(request, section):
        return redirect(
            "photohostapp:section_password",
            slug=section.slug
        )
    files = section.files.all()
    if not files:
        raise Http404("No files")
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in files:
            f.file.open("rb")
            data = f.file.read()
            f.file.close()
            zf.writestr(f.original_name, data)
    buffer.seek(0)
    response = HttpResponse(buffer.getvalue(), content_type="application/zip")
    response["Content-Disposition"] = f'attachment; filename="{section.slug}.zip"'
    return response

def download_file(request, slug, file_id):
    stored_file = get_object_or_404(StoredFile, id=file_id, section__slug=slug)
    section = stored_file.section

    if section.is_expired():
        raise Http404("Section expired")

    if not has_section_access(request, section):
        return redirect(
            "photohostapp:section_password",
            slug=section.slug
        )
    # FileResponse can stream without manually opening
    return FileResponse(
        stored_file.file.open("rb"),
        as_attachment=True,
        filename=stored_file.original_name,
    )


