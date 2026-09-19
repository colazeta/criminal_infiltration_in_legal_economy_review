"""Deterministic native/OCR extraction; exact source text is never printed.

PDF parsing is performed before creating the signed extraction attestation.
Existing source strings/offsets are never edited. OCR is a separate whole-document
method with its own extractor version, source digest and language configuration.
"""
from __future__ import annotations
import hashlib
import os
import re
import subprocess
import tempfile
from pathlib import Path

PROTOCOL = 'CILE-DOCUMENT-TEXT-1'


def _run(args, folder, timeout=90):
    result = subprocess.run(args, capture_output=True, timeout=timeout,
                            env={'PATH': os.environ.get('PATH', '/usr/bin:/bin'),
                                 'LC_ALL': 'C', 'TMPDIR': str(folder)})
    if result.returncode:
        raise RuntimeError('document_parser_failed')
    return result


def extract_document(pdf: bytes, *, allow_ocr=True, ocr_language='eng'):
    if not isinstance(pdf, bytes) or not 0 < len(pdf) <= 4194304:
        raise RuntimeError('document_byte_limit')
    if not pdf.startswith(b'%PDF-') or b'%%EOF' not in pdf[-2048:]:
        raise RuntimeError('document_invalid_pdf')
    with tempfile.TemporaryDirectory(prefix='cile-document-') as directory:
        folder = Path(directory)
        path = folder / 'source.pdf'
        path.write_bytes(pdf)
        path.chmod(0o600)
        info = _run(['pdfinfo', str(path)], folder).stdout.decode('utf-8', 'replace')
        page_match = re.search(r'^Pages:\s+(\d+)\s*$', info, re.M)
        if not page_match or re.search(r'^Encrypted:\s+yes', info, re.M):
            raise RuntimeError('document_parser_validation_failed')
        page_count = int(page_match[1])
        if not 1 <= page_count <= 500:
            raise RuntimeError('document_page_limit')
        output = folder / 'source.txt'
        method = 'native'
        try:
            _run(['pdftotext', '-layout', '-enc', 'UTF-8', str(path), str(output)], folder)
            text = output.read_text(encoding='utf-8')
        except (RuntimeError, UnicodeDecodeError):
            text = ''
        version = _run(['pdftotext', '-v'], folder).stderr.decode('utf-8', 'replace').splitlines()[0]
        pages = text.split('\f')
        if pages and not pages[-1].strip():
            pages.pop()
        low_density = sum(len(re.sub(r'\s', '', page)) < 40 for page in pages)
        native_failed = len(text.strip()) < 100 or len(pages) != page_count or low_density > max(1, page_count // 5)
        if native_failed:
            if not allow_ocr:
                raise RuntimeError('document_ocr_required')
            if page_count > 30 or ocr_language not in {'eng', 'ita', 'deu', 'fra', 'spa'}:
                raise RuntimeError('document_ocr_limit')
            method = 'ocr'
            _run(['pdftoppm', '-r', '120', '-png', str(path), str(folder / 'page')], folder, timeout=180)
            images = sorted(folder.glob('page-*.png'), key=lambda p: int(p.stem.split('-')[-1]))
            if len(images) != page_count:
                raise RuntimeError('document_ocr_page_mismatch')
            text = ''.join(_run(['tesseract', str(image), 'stdout', '-l', ocr_language], folder, timeout=90).stdout.decode('utf-8') + '\f' for image in images)
            version = _run(['tesseract', '--version'], folder).stdout.decode('utf-8').splitlines()[0] + ' ' + ocr_language + ' 120dpi'
        if len(re.sub(r'\s', '', text)) < 100 or len(text) > 2000000:
            raise RuntimeError('document_extraction_quality_failed')
    version = re.sub(r'[^-\w .+():/]', '', version)[:160]
    return text, {'protocol_version': PROTOCOL, 'method': method,
                  'extractor_version': version, 'page_count': page_count,
                  'text_sha256': hashlib.sha256(text.encode()).hexdigest(),
                  'pdf_sha256': hashlib.sha256(pdf).hexdigest(), 'parser_validated': True}
