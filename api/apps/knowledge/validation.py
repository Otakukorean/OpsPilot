from dataclasses import dataclass
from hashlib import sha256
from io import BytesIO
from pathlib import Path

from django.conf import settings
from pypdf import PdfReader
from pypdf.errors import PdfReadError


class InvalidDocument(ValueError):
    def __init__(self, code, message):
        self.code = code
        super().__init__(message)


@dataclass(frozen=True)
class ValidatedUpload:
    data: bytes
    extension: str
    content_type: str
    sha256: str
    page_count: int | None


def validate_upload(upload):
    filename = Path(upload.name or "")
    extension = filename.suffix.lower()
    if extension not in {".pdf", ".txt"}:
        raise InvalidDocument("unsupported_file_type", "Only PDF and TXT files are supported.")

    allowed_mime = {
        ".pdf": {"application/pdf"},
        ".txt": {"text/plain"},
    }
    content_type = (upload.content_type or "").lower().split(";", 1)[0].strip()
    if content_type not in allowed_mime[extension]:
        raise InvalidDocument("invalid_content_type", "The file content type does not match its extension.")

    data = upload.read(settings.KNOWLEDGE_MAX_UPLOAD_BYTES + 1)
    upload.seek(0)
    if not data:
        raise InvalidDocument("empty_file", "The uploaded file is empty.")
    if len(data) > settings.KNOWLEDGE_MAX_UPLOAD_BYTES:
        raise InvalidDocument("file_too_large", "The uploaded file exceeds the configured size limit.")

    if extension == ".pdf":
        page_count = _validate_pdf(data)
    else:
        page_count = None
        _validate_text(data)

    return ValidatedUpload(
        data=data,
        extension=extension,
        content_type=content_type,
        sha256=sha256(data).hexdigest(),
        page_count=page_count,
    )


def _validate_pdf(data):
    if not data.startswith(b"%PDF-"):
        raise InvalidDocument("invalid_file_signature", "The file is not a valid PDF.")
    try:
        reader = PdfReader(BytesIO(data), strict=True)
        if reader.is_encrypted:
            raise InvalidDocument("encrypted_pdf", "Password-protected PDFs are not supported.")
        page_count = len(reader.pages)
    except InvalidDocument:
        raise
    except (PdfReadError, ValueError, TypeError, OSError):
        raise InvalidDocument("malformed_pdf", "The PDF could not be processed.") from None
    if page_count < 1:
        raise InvalidDocument("empty_pdf", "The PDF contains no pages.")
    if page_count > settings.KNOWLEDGE_MAX_PDF_PAGES:
        raise InvalidDocument("too_many_pages", "The PDF exceeds the configured page limit.")
    return page_count


def _validate_text(data):
    if b"\x00" in data:
        raise InvalidDocument("invalid_text", "The TXT file is not plain UTF-8 text.")
    try:
        data.decode("utf-8")
    except UnicodeDecodeError:
        raise InvalidDocument("invalid_text_encoding", "TXT files must use UTF-8 encoding.") from None
