#!/usr/bin/env python3
"""Snapshot/verify a review without deleting, activating or changing any record."""
import argparse
import csv
import hashlib
import io
import json
import subprocess
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EXTERNAL = ("issues_comments", "pull_requests_reviews", "ledger", "automation", "deployments", "persistent_state")


def digest(data):
    return hashlib.sha256(data).hexdigest()


def snapshot(output, external=None, ref="HEAD"):
    output = Path(output)
    if output.exists():
        raise ValueError("snapshot destination must not exist")
    output.mkdir(parents=True)
    commit = subprocess.check_output(["git", "rev-parse", ref], cwd=ROOT, text=True).strip()
    archive = subprocess.check_output(["git", "archive", "--format=tar", commit], cwd=ROOT)
    (output / "repository.tar").write_bytes(archive)
    files, counts = {}, {}
    with tarfile.open(fileobj=io.BytesIO(archive)) as handle:
        for member in handle.getmembers():
            if not member.isfile():
                continue
            content = handle.extractfile(member).read()
            files[member.name] = {"sha256": digest(content), "bytes": len(content)}
            if member.name.startswith(("data/registry/", "data/curation/")) and member.name.endswith(".csv"):
                counts[member.name] = len(list(csv.DictReader(io.StringIO(content.decode("utf-8-sig")))))
    supplied = external or {}
    external_files = {}
    for key in EXTERNAL:
        if key not in supplied:
            continue
        source = Path(supplied[key])
        data = source.read_bytes()
        # Evidence exports must declare scope/completeness; a blank JSON file is not a backup.
        envelope = json.loads(data)
        if not isinstance(envelope, dict) or envelope.get("scope") != key or envelope.get("complete") is not True or "records" not in envelope:
            raise ValueError(f"unverified external export:{key}")
        path = f"external-{key}.json"
        (output / path).write_bytes(data)
        external_files[key] = {"file": path, "sha256": digest(data), "bytes": len(data)}
    shallow = subprocess.check_output(["git", "rev-parse", "--is-shallow-repository"], cwd=ROOT, text=True).strip() == "true"
    if not shallow:
        subprocess.run(["git", "bundle", "create", str(output.resolve() / "history.bundle"), "--all"], cwd=ROOT, check=True, capture_output=True)
    manifest = {"version": 1, "git_commit": commit, "repository_sha256": digest(archive), "files": files, "counts": counts,
                "history_complete": not shallow, "history_sha256": digest((output / "history.bundle").read_bytes()) if not shallow else None,
                "external": external_files, "missing_external": sorted(set(EXTERNAL) - set(external_files)),
                "cutover_ready": not shallow and set(external_files) == set(EXTERNAL)}
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    verify(output)
    return manifest


def verify(directory):
    directory = Path(directory)
    manifest = json.loads((directory / "manifest.json").read_text())
    archive = (directory / "repository.tar").read_bytes()
    if digest(archive) != manifest["repository_sha256"]:
        raise ValueError("repository archive hash mismatch")
    observed = {}
    with tarfile.open(fileobj=io.BytesIO(archive)) as handle:
        for member in handle.getmembers():
            if member.issym() or member.islnk() or member.name.startswith("/") or ".." in Path(member.name).parts:
                raise ValueError("unsafe archive member")
            if member.isfile():
                data = handle.extractfile(member).read()
                observed[member.name] = {"sha256": digest(data), "bytes": len(data)}
    if observed != manifest["files"]:
        raise ValueError("restored file inventory mismatch")
    if set(manifest["external"]) - set(EXTERNAL):
        raise ValueError("unknown external scope")
    for scope, item in manifest["external"].items():
        if item["file"] != f"external-{scope}.json":
            raise ValueError("unexpected external path")
        data = (directory / item["file"]).read_bytes()
        if digest(data) != item["sha256"] or len(data) != item["bytes"]:
            raise ValueError("external snapshot hash mismatch")
        envelope = json.loads(data)
        if envelope.get("scope") != scope or envelope.get("complete") is not True or "records" not in envelope:
            raise ValueError("external completeness mismatch")
    if manifest["history_complete"] and digest((directory / "history.bundle").read_bytes()) != manifest["history_sha256"]:
        raise ValueError("history bundle hash mismatch")
    missing = sorted(set(EXTERNAL) - set(manifest["external"]))
    if manifest["missing_external"] != missing or manifest["cutover_ready"] != (manifest["history_complete"] and not missing):
        raise ValueError("snapshot readiness mismatch")
    return {"verified_files": len(observed), "counts": manifest["counts"], "cutover_ready": manifest["cutover_ready"]}


def restore(directory, destination):
    result = verify(directory)
    destination = Path(destination)
    if destination.exists():
        raise ValueError("restore requires a new isolated directory")
    destination.mkdir(parents=True)
    with tarfile.open(Path(directory) / "repository.tar") as archive:
        archive.extractall(destination, filter="data")
    manifest = json.loads((Path(directory) / "manifest.json").read_text())
    for name, metadata in manifest["files"].items():
        if digest((destination / name).read_bytes()) != metadata["sha256"]:
            raise ValueError("restored bytes differ")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["snapshot", "verify", "restore"])
    parser.add_argument("directory", type=Path)
    parser.add_argument("--destination", type=Path)
    parser.add_argument("--external-manifest", type=Path, help="Private mapping from external scopes to verified JSON exports")
    args = parser.parse_args()
    if args.action == "snapshot":
        result = snapshot(args.directory, json.loads(args.external_manifest.read_text()) if args.external_manifest else None)
        print(json.dumps({"git_commit": result["git_commit"], "counts": result["counts"], "missing_external": result["missing_external"], "cutover_ready": result["cutover_ready"]}))
    elif args.action == "verify":
        print(json.dumps(verify(args.directory)))
    elif args.destination:
        print(json.dumps(restore(args.directory, args.destination)))
    else:
        parser.error("restore requires --destination")
