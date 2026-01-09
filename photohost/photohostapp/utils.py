# from PIL import Image
# from io import BytesIO
# from django.core.files.base import ContentFile
#
# def remove_exif_and_get_file(uploaded_file):
#     """
#     If file is an image, re-save it using Pillow to strip EXIF data.
#     If not an image, return original file.
#     """
#     try:
#         uploaded_file.seek(0)
#         img = Image.open(uploaded_file)
#
#         # Force load to verify it's really an image
#         img.verify()
#
#         # Reopen after verify
#         uploaded_file.seek(0)
#         img = Image.open(uploaded_file)
#
#         # Convert to RGB to safely strip metadata
#         if img.mode in ("RGBA", "LA"):
#             background = Image.new("RGB", img.size, (255, 255, 255))
#             background.paste(img, mask=img.split()[3])
#             img = background
#         else:
#             img = img.convert("RGB")
#
#         bio = BytesIO()
#         img.save(bio, format="JPEG", quality=95)
#         bio.seek(0)
#
#         name = uploaded_file.name
#         if not name.lower().endswith(".jpg") and not name.lower().endswith(".jpeg"):
#             name = f"{name.rsplit('.', 1)[0]}.jpg"
#
#         return (name, ContentFile(bio.read(), name=name))
#
#     except Exception:
#         # Not an image → return original file
#         uploaded_file.seek(0)
#         return (uploaded_file.name, ContentFile(uploaded_file.read(), name=uploaded_file.name))


import os
from io import BytesIO
from django.core.files.base import ContentFile, File
from PIL import Image

def remove_exif_and_get_file(uploaded_file):
    """
    Fast EXIF removal:
    - Only strips EXIF for JPEG/JPG by re-saving pixels to JPEG (keeps JPEG output).
    - For all other files, returns the original uploaded file WITHOUT reading it into memory.
    """
    name = uploaded_file.name or "upload"
    ext = os.path.splitext(name)[1].lower()

    # Only JPEG really needs EXIF stripping here
    if ext in [".jpg", ".jpeg"]:
        uploaded_file.seek(0)
        img = Image.open(uploaded_file)

        # Ensure pixels are loaded, but avoid verify()+reopen cost
        img = img.convert("RGB")

        bio = BytesIO()
        # Saving without exif parameter strips metadata
        img.save(bio, format="JPEG", quality=90, optimize=True)
        bio.seek(0)

        return (name, ContentFile(bio.read(), name=name))

    # Non-JPEG: return original file as-is, no memory copy
    uploaded_file.seek(0)
    return (name, File(uploaded_file))
