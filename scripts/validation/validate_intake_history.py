#!/usr/bin/env python3
"""Reject deletion or rewriting of committed intake receipts against a trusted base.

The base must come from the authenticated CI event, never the proposed PR body.
New receipts remain subject to ontology/intake validation. Corrections require a
new attributed observation; this gate does not establish truth of source bytes.
"""
import argparse
from pathlib import Path
import subprocess

PREFIX = 'data/curation/intake_access/'


def validate_history(root, base):
    def git(*args):
        return subprocess.check_output(['git', '-C', str(root), *args])
    git('rev-parse', '--verify', base + '^{commit}')
    paths = git('ls-tree', '-r', '--name-only', '-z', base, '--', PREFIX).decode().split('\0')
    for name in filter(None, paths):
        path = Path(root) / name
        if not path.is_file() or path.read_bytes() != git('show', f'{base}:{name}'):
            raise ValueError(f'committed intake evidence is immutable: {name}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', required=True)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[2])
    args = parser.parse_args()
    validate_history(args.root, args.base)
