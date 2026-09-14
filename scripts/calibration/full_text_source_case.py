#!/usr/bin/env python3
"""Capture one already-registered full-text calibration source into encrypted audit transport.

This is source preparation only: no production private-store write, extraction proposal,
classification, calibration receipt or completion receipt is created here.
"""
import argparse
import hashlib
import json
import os
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from scripts.oa_acquisition import acquire_pdf

ROOT = Path(__file__).resolve().parents[2]
PROTOCOL = 'CILE-FULLTEXT-CALIBRATION-SOURCE-1'
MAX_TEXT = 2_000_000


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False)


def norm(value):
    return ' '.join(str(value).lower().split())


def candidate(candidate_id, url):
    records = json.loads((ROOT / 'site/data/paper-register.json').read_text())['records']
    matches = [record for record in records if record.get('id') == candidate_id]
    if len(matches) != 1:
        raise RuntimeError('fulltext_candidate_not_registered')
    record = matches[0]
    if url not in record.get('sourceLinks', []):
        raise RuntimeError('fulltext_url_not_candidate_bound')
    return record


def extract_text(pdf_bytes):
    with tempfile.TemporaryDirectory(prefix='cile-fulltext-', dir=os.environ.get('RUNNER_TEMP')) as directory:
        folder = Path(directory)
        pdf = folder / 'source.pdf'
        txt = folder / 'source.txt'
        fd = os.open(pdf, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, 'wb') as handle:
            handle.write(pdf_bytes)
        env = {'PATH': os.environ.get('PATH', '/usr/bin:/bin'), 'HOME': str(folder)}
        result = subprocess.run(['pdftotext', '-layout', '-enc', 'UTF-8', str(pdf), str(txt)],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                timeout=90, env=env)
        if result.returncode or not txt.exists():
            raise RuntimeError('fulltext_text_extraction_failed')
        text = txt.read_text(encoding='utf-8', errors='strict')
    if len(text) < 1000 or len(text) > MAX_TEXT:
        raise RuntimeError('fulltext_text_bounds_failed')
    return text


def seal(output, payload):
    recipient = ROOT / 'config/fulltext-calibration-recipient.json'
    data = json.loads(recipient.read_text())
    if datetime.now(timezone.utc) >= datetime.fromisoformat(data['expires_at'].replace('Z', '+00:00')):
        raise RuntimeError('fulltext_recipient_expired')
    js = """import{readFileSync,writeFileSync}from'node:fs';
import{seal}from'./scripts/enrichment/seal-audit.mjs';
let s='';for await(const c of process.stdin)s+=c;
const recipient=JSON.parse(readFileSync('config/fulltext-calibration-recipient.json','utf8'));
writeFileSync(process.argv[1],JSON.stringify(seal(Buffer.from(s),recipient)),{flag:'wx',mode:0o600});"""
    temporary = output.with_name(output.name + '.next')
    temporary.unlink(missing_ok=True)
    result = subprocess.run(['node', '--input-type=module', '-e', js, str(temporary)],
                            input=canonical(payload), text=True, cwd=ROOT,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                            timeout=20, env={'PATH': os.environ.get('PATH', '/usr/bin:/bin')})
    if result.returncode:
        temporary.unlink(missing_ok=True)
        raise RuntimeError('fulltext_sealing_failed')
    os.replace(temporary, output)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate-id', required=True)
    parser.add_argument('--url', required=True)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--retention-basis', required=True)
    parser.add_argument('--licence-status', required=True)
    args = parser.parse_args()

    record = candidate(args.candidate_id, args.url)
    pdf, observation = acquire_pdf(args.url)
    text = extract_text(pdf)
    expected = 'the economic impact of organized crime infiltration in the legal economy'
    if expected not in norm(text[:20000]):
        raise RuntimeError('fulltext_identity_text_mismatch')
    text_hash = hashlib.sha256(text.encode()).hexdigest()
    payload = {
        'protocol': PROTOCOL,
        'candidate': {key: record.get(key) for key in ('id', 'title', 'doi', 'sourceLinks')},
        'source_url': observation['full_text_url'],
        'pdf_sha256': observation['full_text_sha256'],
        'pdf_byte_count': observation['byte_count'],
        'text_sha256': text_hash,
        'text': text,
        'text_extractor': 'pdftotext -layout -enc UTF-8',
        'retention_basis': args.retention_basis,
        'licence_status': args.licence_status,
        'observed_at': observation['verified_at'],
        'scope': 'private_calibration_source_not_production_source_or_receipt',
    }
    seal(args.output, payload)
    print(json.dumps({
        'candidate_id': args.candidate_id,
        'source_url': observation['full_text_url'],
        'pdf_sha256': observation['full_text_sha256'],
        'text_sha256': text_hash,
        'text_chars': len(text),
        'encrypted': True,
        'scientific_validation': False,
        'production_writes': 0,
    }))


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        allowed = {
            'fulltext_candidate_not_registered', 'fulltext_url_not_candidate_bound',
            'fulltext_text_extraction_failed', 'fulltext_text_bounds_failed',
            'fulltext_recipient_expired', 'fulltext_sealing_failed',
            'fulltext_identity_text_mismatch',
        }
        code = str(error)
        raise SystemExit(code if code in allowed or code.startswith('OA ') else 'fulltext_capture_failed') from None
