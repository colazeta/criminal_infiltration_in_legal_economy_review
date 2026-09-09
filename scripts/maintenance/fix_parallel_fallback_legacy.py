#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# Preserve v1 Consensus provenance as readable history without authorising it for v2/v3.
path = ROOT / "scripts/metrics/fetch_surveillance_ledger.py"
text = path.read_text(encoding="utf-8")
old = '        prefix = {"Exa": "EXA", "Parallel Search": "PARALLEL"}.get(source_name)\n'
new = '        prefix = {"Consensus": "CONSENSUS", "Exa": "EXA", "Parallel Search": "PARALLEL"}.get(source_name)\n'
if old not in text:
    raise SystemExit("ledger prefix anchor not found")
path.write_text(text.replace(old, new, 1), encoding="utf-8")

# Match the intentionally earlier source-scoped rejection in the new negative test.
path = ROOT / "tests/test_parallel_search_fallback.py"
text = path.read_text(encoding="utf-8")
old = 'with self.assertRaisesRegex(MetricsError, "provider-scoped W1–W7"):'
new = 'with self.assertRaisesRegex(MetricsError, "source-scoped ID"):'
if old not in text:
    raise SystemExit("test regex anchor not found")
path.write_text(text.replace(old, new, 1), encoding="utf-8")
