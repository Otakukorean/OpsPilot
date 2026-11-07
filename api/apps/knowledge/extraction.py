from dataclasses import dataclass
from io import BytesIO

from pypdf import PdfReader


class ExtractionError(RuntimeError):
    pass


@dataclass(frozen=True)
class ExtractedPage:
    page: int | None
    text: str


def extract_pages(data, content_type):
    if content_type == "text/plain":
        text = data.decode("utf-8").strip()
        if not text:
            raise ExtractionError("no_extractable_text")
        return [ExtractedPage(page=None, text=text)]

    try:
        reader = PdfReader(BytesIO(data), strict=True)
        pages = [
            ExtractedPage(page=index, text=(page.extract_text() or "").strip())
            for index, page in enumerate(reader.pages, start=1)
        ]
    except Exception as exc:
        raise ExtractionError("pdf_extraction_failed") from exc
    if not any(page.text for page in pages):
        raise ExtractionError("no_extractable_text")
    return pages
