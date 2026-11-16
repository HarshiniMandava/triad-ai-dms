
import io
import os

import pymupdf as fitz
import pytesseract
from PIL import Image, ImageOps

TESSERACT_PATH = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

if os.path.isfile(TESSERACT_PATH):
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH


def extract_text(file_bytes, filename):
    extension = os.path.splitext(filename)[1].lower()

    try:
        if extension == ".pdf":
            pdf = fitz.open(stream=file_bytes, filetype="pdf")
            extracted = []

            try:
                for page in pdf:
                    text = page.get_text("text")

                    if text.strip():
                        extracted.append(text)
                    else:
                        pix = page.get_pixmap(
                            matrix=fitz.Matrix(2, 2),
                            alpha=False
                        )

                        image = Image.open(
                            io.BytesIO(pix.tobytes("png"))
                        )

                        extracted.append(
                            pytesseract.image_to_string(image)
                        )
            finally:
                pdf.close()

            return "\n".join(extracted).strip()

        if extension in [".png", ".jpg", ".jpeg", ".tiff", ".bmp"]:
            image = Image.open(io.BytesIO(file_bytes))
            image = ImageOps.exif_transpose(image).convert("RGB")
            return pytesseract.image_to_string(image).strip()

        return ""

    except Exception as error:
        print("OCR extraction failed:", error)
        return ""
