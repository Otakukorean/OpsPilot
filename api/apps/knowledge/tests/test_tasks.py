import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from apps.accounts.models import Membership, User, Workspace
from apps.knowledge.models import Document
from apps.knowledge.tasks import ingest_document


class IngestionTaskTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._media = tempfile.TemporaryDirectory()
        cls._override = override_settings(MEDIA_ROOT=cls._media.name)
        cls._override.enable()

    @classmethod
    def tearDownClass(cls):
        cls._override.disable()
        cls._media.cleanup()
        super().tearDownClass()

    def setUp(self):
        workspace = Workspace.objects.create(name="Ingestion Workspace")
        user = User.objects.create_user(email="admin@ingestion.example", password="synthetic-password")
        Membership.objects.create(user=user, workspace=workspace, role=Membership.Role.ADMIN)
        self.document = Document.objects.create(
            workspace=workspace,
            uploaded_by=user,
            title="Synthetic Troubleshooting",
            source_file=SimpleUploadedFile(
                "guide.txt",
                b"Duplicate payment error T24-000 means a fictional request was repeated.",
                content_type="text/plain",
            ),
            original_filename="guide.txt",
            content_type="text/plain",
            size_bytes=72,
            sha256="b" * 64,
        )

    def test_task_extracts_chunks_and_is_idempotent(self):
        ingest_document.apply(args=[str(self.document.id)]).get()
        self.document.refresh_from_db()

        self.assertEqual(self.document.status, Document.Status.READY)
        self.assertEqual(self.document.embedding_model, "local_hashing_v1")
        self.assertEqual(self.document.chunks.count(), 1)
        chunk = self.document.chunks.get()
        self.assertEqual(chunk.workspace_id, self.document.workspace_id)
        self.assertIn("T24-000", chunk.text)
        self.assertEqual(len(chunk.embedding), 384)

        ingest_document.apply(args=[str(self.document.id)]).get()
        self.assertEqual(self.document.chunks.count(), 1)

    def test_empty_text_fails_with_sanitized_reason(self):
        empty = Document.objects.create(
            workspace=self.document.workspace,
            uploaded_by=self.document.uploaded_by,
            title="Whitespace",
            source_file=SimpleUploadedFile("empty.txt", b"   ", content_type="text/plain"),
            original_filename="empty.txt",
            content_type="text/plain",
            size_bytes=3,
            sha256="c" * 64,
        )

        ingest_document.apply(args=[str(empty.id)]).get()
        empty.refresh_from_db()

        self.assertEqual(empty.status, Document.Status.FAILED)
        self.assertEqual(empty.failure_reason, "no_extractable_text")
        self.assertEqual(empty.chunks.count(), 0)
