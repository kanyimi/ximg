import pytesseract
from PIL import Image
import os

# Windows-only: explicitly set path if needed
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"


IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp'}


def extract_text_from_image(file_path: str) -> str:
    """
    Extract text from an image file using Tesseract OCR
    """
    ext = os.path.splitext(file_path)[1].lower()
    if ext not in IMAGE_EXTENSIONS:
        return ""

    try:
        with Image.open(file_path) as img:
            # Convert to RGB for better OCR results
            img = img.convert("RGB")
            text = pytesseract.image_to_string(img)
            return text.strip()
    except Exception as e:
        return f"OCR failed: {e}"
