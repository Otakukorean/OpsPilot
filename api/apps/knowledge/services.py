from pathlib import Path

from django.core.files.base import ContentFile
from django.db import transaction

from .models import Document
from .tasks import ingest_document


def create_document(*, membership, actor, title, original_filename, validated):
    safe_title = title.strip() or Path(original_filename).stem
    safe_title = safe_title[:255]
    safe_original_name = Path(original_filename).name[:255]

    document = Document(
        workspace_id=membership.workspace_id,
        uploaded_by=actor,
        title=safe_title,
        original_filename=safe_original_name,
        content_type=validated.content_type,
        size_bytes=len(validated.data),
        sha256=validated.sha256,
        page_count=validated.page_count,
    )
    try:
        with transaction.atomic():
            document.source_file.save(
                f"source{validated.extension}",
                ContentFile(validated.data),
                save=False,
            )
            document.save()
            transaction.on_commit(lambda: ingest_document.delay(str(document.id)))
    except Exception:
        if document.source_file.name:
            document.source_file.storage.delete(document.source_file.name)
        raise
    return document


def delete_document(document):
    storage = document.source_file.storage
    storage_name = document.source_file.name
    with transaction.atomic():
        document.delete()
        transaction.on_commit(lambda: storage.delete(storage_name))
