from io import BytesIO
from types import SimpleNamespace

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, override_settings
from pypdf import PdfWriter

from apps.knowledge.chunking import chunk_pages
from apps.knowledge.embeddings import LocalHashingEmbeddingProvider
from apps.knowledge.extraction import ExtractedPage
from apps.knowledge.validation import InvalidDocument, validate_upload


class KnowledgeServiceTests(SimpleTestCase):
    def test_chunking_has_bounded_overlap_and_preserves_pages(self):
        pages = [ExtractedPage(page=4, text="one two three four five six")]

        chunks = chunk_pages(pages, size=4, overlap=1)

        self.assertEqual([chunk.text for chunk in chunks], ["one two three four", "four five six"])
        self.assertEqual([chunk.page for chunk in chunks], [4, 4])

    def test_local_embeddings_are_deterministic_and_dimensioned(self):
        provider = LocalHashingEmbeddingProvider()

        first, second = provider.embed(["duplicate payment error", "duplicate payment error"])

        self.assertEqual(first, second)
        self.assertEqual(len(first), 384)
        self.assertAlmostEqual(sum(value * value for value in first), 1.0)

    def test_txt_validation_rejects_mime_spoofing_and_binary_content(self):
        spoofed = SimpleUploadedFile("guide.txt", b"synthetic text", content_type="application/pdf")
        binary = SimpleUploadedFile("guide.txt", b"synthetic\x00text", content_type="text/plain")

        with self.assertRaisesRegex(InvalidDocument, "content type"):
            validate_upload(spoofed)
        with self.assertRaisesRegex(InvalidDocument, "plain UTF-8"):
            validate_upload(binary)

    @override_settings(KNOWLEDGE_MAX_UPLOAD_BYTES=5)
    def test_validation_rejects_oversized_file(self):
        upload = SimpleUploadedFile("guide.txt", b"123456", content_type="text/plain")

        with self.assertRaisesRegex(InvalidDocument, "size limit"):
            validate_upload(upload)

    def test_pdf_validation_checks_real_signature_and_page_count(self):
        output = BytesIO()
        writer = PdfWriter()
        writer.add_blank_page(width=100, height=100)
        writer.write(output)
        upload = SimpleUploadedFile("guide.pdf", output.getvalue(), content_type="application/pdf")

        validated = validate_upload(upload)

        self.assertEqual(validated.page_count, 1)
        self.assertEqual(validated.extension, ".pdf")

    def test_fake_pdf_is_rejected(self):
        upload = SimpleUploadedFile("guide.pdf", b"not a PDF", content_type="application/pdf")

        with self.assertRaisesRegex(InvalidDocument, "valid PDF"):
            validate_upload(upload)
