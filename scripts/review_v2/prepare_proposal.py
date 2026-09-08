#!/usr/bin/env python3
"""Prepare a public hash-only approval manifest; no scientific decision is applied."""
import json
import os
import re
from pathlib import Path


def parse(body):
    match = re.fullmatch(r"<!-- cile-v2-proposal:([A-Za-z0-9-]{8,80}) -->\n\n```json\n(\{[^\n]+\})\n```", body or "")
    if not match:
        raise ValueError("invalid approval envelope")
    payload = json.loads(match[2])
    if set(payload) != {"proposal_id", "payload_sha256", "protocol_version", "action"}:
        raise ValueError("public manifest must contain hashes and identifiers only")
    if payload["proposal_id"] != match[1] or payload["action"] != "approve_screening" or payload["protocol_version"] != "CILE-4PT-v2":
        raise ValueError("approval manifest mismatch")
    if not re.fullmatch(r"[a-f0-9]{64}", payload["payload_sha256"]):
        raise ValueError("invalid proposal hash")
    return payload


if __name__ == "__main__":
    event = json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text())
    if event["sender"]["login"] != event["repository"]["owner"]["login"] or event["sender"]["type"] != "User":
        raise SystemExit("human owner instruction required")
    payload = parse(event["issue"]["body"])
    path = Path("scientific-approvals") / f"{payload['proposal_id']}.json"
    path.parent.mkdir(exist_ok=True)
    if path.exists():
        raise SystemExit("approval manifest already exists; refusing replacement")
    path.write_text(json.dumps(payload, indent=2) + "\n")
