import re
from dataclasses import dataclass


WORD_RE = re.compile(r"\S+")


@dataclass(frozen=True)
class TextChunk:
    page: int | None
    text: str


def chunk_pages(pages, size=600, overlap=80):
    if size <= 0 or overlap < 0 or overlap >= size:
        raise ValueError("Invalid chunking configuration.")

    chunks = []
    step = size - overlap
    for page in pages:
        words = WORD_RE.findall(page.text)
        for start in range(0, len(words), step):
            chunk_words = words[start : start + size]
            if chunk_words:
                chunks.append(TextChunk(page=page.page, text=" ".join(chunk_words)))
            if start + size >= len(words):
                break
    return chunks
