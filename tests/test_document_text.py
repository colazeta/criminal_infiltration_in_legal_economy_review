import unittest
import shutil
from pathlib import Path
from unittest.mock import patch
from scripts.enrichment import document_text
from scripts.enrichment.document_text import extract_document


def synthetic_pdf():
    # A complete generated two-page PDF. No third-party content or dependency.
    bodies = [b'<< /Type /Catalog /Pages 2 0 R >>',
              b'<< /Type /Pages /Kids [3 0 R 4 0 R] /Count 2 >>',
              b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 5 0 R >> >> /Contents 6 0 R >>',
              b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 5 0 R >> >> /Contents 7 0 R >>',
              b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>']
    for page in [1, 2]:
        stream = f'BT /F1 10 Tf 40 700 Td (Synthetic page {page}: procurement evidence from company data. This is a generated software test, not a research finding.) Tj ET'.encode()
        bodies.append(b'<< /Length '+str(len(stream)).encode()+b' >>\nstream\n'+stream+b'\nendstream')
    data = b'%PDF-1.4\n'; offsets = [0]
    for i, body in enumerate(bodies, 1):
        offsets.append(len(data)); data += f'{i} 0 obj\n'.encode()+body+b'\nendobj\n'
    start = len(data)
    data += b'xref\n0 8\n0000000000 65535 f \n'
    data += b''.join(f'{offset:010d} 00000 n \n'.encode() for offset in offsets[1:])
    return data + f'trailer\n<< /Size 8 /Root 1 0 R >>\nstartxref\n{start}\n%%EOF\n'.encode()


@unittest.skipUnless(shutil.which('pdfinfo') and shutil.which('pdftotext'), 'Poppler integration dependency required')
class DocumentTextTests(unittest.TestCase):
    def test_real_parser_preserves_two_pages_and_deterministic_text(self):
        text, receipt = extract_document(synthetic_pdf())
        self.assertEqual(receipt['page_count'], 2)
        self.assertEqual(receipt['method'], 'native')
        self.assertEqual(text.count('\f'), 2)
        self.assertIn('Synthetic page 2', text)
        self.assertEqual(extract_document(synthetic_pdf()), (text, receipt))

    def test_html_truncated_and_forged_pdf_are_rejected(self):
        for body in [b'<html>Login required</html>', b'%PDF-1.7\nnot a real PDF\n%%EOF', synthetic_pdf()[:100]]:
            with self.subTest(body=body[:20]), self.assertRaises(RuntimeError):
                extract_document(body)

    @unittest.skipUnless(shutil.which('pdftoppm') and shutil.which('tesseract'), 'OCR integration dependencies required')
    def test_native_failure_uses_separate_real_ocr_receipt(self):
        native = document_text._run
        def no_embedded_text(args, folder, timeout=90):
            result = native(args, folder, timeout)
            if args[:2] == ['pdftotext', '-layout']:
                Path(args[-1]).write_text('\f\f')
            return result
        with patch.object(document_text, '_run', no_embedded_text):
            text, receipt = extract_document(synthetic_pdf())
        self.assertEqual(receipt['method'], 'ocr')
        self.assertEqual(receipt['page_count'], 2)
        self.assertIn('tesseract', receipt['extractor_version'])
        self.assertEqual(text.count('\f'), 2)
