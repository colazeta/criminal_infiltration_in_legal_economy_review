#!/usr/bin/env python3
from pathlib import Path

path = Path(__file__).resolve().parents[2] / ".github/workflows/intake-to-curation.yml"
text = path.read_text(encoding="utf-8")
old = '''          if ! command -v pdftotext >/dev/null 2>&1; then
            sudo apt-get update -qq
            sudo apt-get install -y --no-install-recommends poppler-utils
          fi
'''
new = '''          if ! command -v pdftotext >/dev/null 2>&1; then
            # The hosted-runner Chrome apt source is unrelated to abstract
            # coverage and can transiently publish inconsistent indexes.
            # Disable only that source before refreshing apt so a Chrome
            # mirror error cannot block installation of poppler-utils.
            while IFS= read -r source_file; do
              sudo mv "$source_file" "$source_file.disabled"
            done < <(grep -rl 'dl.google.com/linux/chrome' /etc/apt/sources.list.d 2>/dev/null || true)
            sudo apt-get update -o Acquire::Retries=3 -qq
            sudo apt-get install -y --no-install-recommends poppler-utils
          fi
'''
if old not in text:
    raise SystemExit("poppler apt anchor not found")
path.write_text(text.replace(old, new, 1), encoding="utf-8")
