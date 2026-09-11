#!/usr/bin/env python3
"""Partition the existing benchmark; never access a production service or credential."""
import argparse
import hashlib
import json
import os
import tarfile
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from scripts.calibration import paper_content_benchmark as base

PARTS = 3
MAX_CASES = 6
MIN_CASES = 4


def pool(part):
    if type(part) is not int or not 0 <= part < PARTS:
        raise ValueError('benchmark_invalid_partition')
    return base.DOIS[part::PARTS]


def write_private(path, value):
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'w', encoding='utf-8') as out:
        json.dump(value, out, ensure_ascii=False)


def check_recipient():
    recipient = json.loads((base.ROOT / 'config/enrichment-benchmark-recipient.json').read_text())
    if datetime.now(timezone.utc) >= datetime.fromisoformat(recipient['expires_at'].replace('Z', '+00:00')):
        raise RuntimeError('benchmark_recipient_expired')


def collect(part):
    records = json.loads((base.ROOT / 'site/data/paper-register.json').read_text())['records']
    by_doi = {}
    for record in records:
        by_doi.setdefault(record.get('doi', '').lower(), record)
    packets, availability = [], []
    for doi in pool(part):
        if len(packets) == MAX_CASES:
            break
        record = by_doi.get(doi)
        if record is None:
            availability.append({'doi': doi, 'status': 'not_in_current_register'})
            continue
        try:
            packets.append(base.retrieve(record))
            status = 'abstract_ready'
        except Exception as error:
            allowed = {'benchmark_identity_mismatch', 'benchmark_abstract_not_returned',
                       'benchmark_source_over_limit', 'benchmark_response_limit', 'benchmark_redirect_refused'}
            status = str(error) if str(error) in allowed else 'provider_or_decode_failure'
        availability.append({'doi': doi, 'status': status})
        time.sleep(1)
    return {'protocol': base.PROTOCOL, 'partition': part, 'partitions': PARTS,
            'packets': packets, 'availability': availability, 'scientific_validation': False}


def validate_packets(payload, part):
    if payload.get('protocol') != base.PROTOCOL or payload.get('partition') != part:
        raise ValueError('benchmark_partition_mismatch')
    packets = payload.get('packets')
    if not isinstance(packets, list) or not MIN_CASES <= len(packets) <= MAX_CASES:
        raise ValueError('benchmark_insufficient_partition_coverage')
    seen = set()
    for packet in packets:
        source = packet['sources'][0]
        record = json.loads(packet['target']['record_json'])
        if record['doi'] not in pool(part) or record['doi'] in seen:
            raise ValueError('benchmark_partition_identity')
        seen.add(record['doi'])
        rebuilt = base.packet_for(record, {'DOI': record['doi'], 'title': [record['title']], 'abstract': source['text']})
        if rebuilt['target'] != packet['target'] or rebuilt['sources'][0]['content_sha256'] != source['content_sha256']:
            raise ValueError('benchmark_local_source_integrity')
        if packet.get('scope') != 'offline_benchmark_not_a_production_receipt':
            raise ValueError('benchmark_invalid_scope')
    return packets


def infer(payload, part, output):
    packets = validate_packets(payload, part)
    with tempfile.TemporaryDirectory(prefix='cile-bench-engine-', dir=os.environ.get('RUNNER_TEMP')) as directory:
        work = Path(directory)
        os.chmod(work, 0o700)
        archive_path, weights = work / 'engine.tar.gz', work / 'model.gguf'
        base.download('https://github.com/ggml-org/llama.cpp/releases/download/b10333/llama-b10333-bin-ubuntu-x64.tar.gz', archive_path,
                      '936ce04d98abe2a977e9dd2ff92659bb96947e136acee8f2bc3e21d8eaebbf23', 30000000)
        base.download('https://huggingface.co/unsloth/Qwen3-4B-Instruct-2507-GGUF/resolve/main/Qwen3-4B-Instruct-2507-Q4_K_M.gguf', weights,
                      '3605803b982cb64aead44f6c1b2ae36e3acdb41d8e46c8a94c6533bc4c67e597', 3000000000)
        with tarfile.open(archive_path) as archive:
            archive.extractall(work / 'bin', filter='data')
        binary = next((work / 'bin').rglob('llama-server'))
        os.chmod(binary, 0o700)
        def checkpoint(results):
            base.seal_output(output, {'protocol': base.PROTOCOL, 'partition': part, 'results': results,
                                     'scientific_validation': False, 'production_proposals_written': 0})
        results = base.evaluate(binary, weights, work, packets, checkpoint)
        checkpoint(results)
        valid = sum(result['status'] == 'structurally_valid_unreviewed' for result in results)
        print(json.dumps({'partition': part, 'cases': len(results), 'structurally_valid': valid,
                          'scientific_validation': False, 'production_proposals_written': 0}), flush=True)
        if valid != len(results):
            raise RuntimeError('benchmark_structural_failures_require_review')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=['collect', 'infer'])
    parser.add_argument('--partition', type=int, choices=range(PARTS), required=True)
    parser.add_argument('--private-input', type=Path, required=True)
    parser.add_argument('--sealed-output', type=Path, required=True)
    args = parser.parse_args()
    check_recipient()
    if args.stage == 'collect':
        payload = collect(args.partition)
        base.seal_output(args.sealed_output, payload)
        validate_packets(payload, args.partition)
        write_private(args.private_input, payload)
        print(json.dumps({'partition': args.partition, 'sources_ready': len(payload['packets']),
                          'production_access': False}), flush=True)
    else:
        try:
            if args.private_input.stat().st_size > 500000:
                raise ValueError('benchmark_private_input_limit')
            infer(json.loads(args.private_input.read_text()), args.partition, args.sealed_output)
        finally:
            args.private_input.unlink(missing_ok=True)

if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        safe = {'benchmark_recipient_expired', 'benchmark_insufficient_partition_coverage',
                'benchmark_partition_mismatch', 'benchmark_partition_identity', 'benchmark_local_source_integrity',
                'benchmark_invalid_scope', 'benchmark_private_input_limit', 'benchmark_structural_failures_require_review',
                'benchmark_engine_failed', 'benchmark_engine_timeout', 'benchmark_sealing_failed'}
        raise SystemExit(str(error) if str(error) in safe else 'benchmark_partition_failed_no_content_logged') from None
