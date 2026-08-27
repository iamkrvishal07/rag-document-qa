import io
from pathlib import Path

import fitz
from docx import Document


ALLOWED_EXTENSIONS = {".pdf", ".docx"}

ALLOWED_MIME_TYPES = {
    ".pdf": {
        "application/pdf",
    },
    ".docx": {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    },
}


def get_file_extension(filename: str) -> str:
    return Path(filename).suffix.lower()


def is_supported_file(
    filename: str,
    content_type: str | None,
) -> bool:
    extension = get_file_extension(filename)

    if extension not in ALLOWED_EXTENSIONS:
        return False

    if content_type not in ALLOWED_MIME_TYPES[extension]:
        return False

    return True


def is_file_readable(
    file_bytes: bytes,
    extension: str,
) -> bool:
    try:
        if extension == ".pdf":
            document = fitz.open(
                stream=file_bytes,
                filetype="pdf",
            )

            document.close()
            return True

        if extension == ".docx":
            Document(io.BytesIO(file_bytes))
            return True

        return False

    except Exception:
        return False