#!/usr/bin/env python3
"""Emit non-sensitive structural diagnostics for full-text synthesis graphs.

The audit intentionally records counts and digests only. It never serialises
source text, model evidence, field values, record ids or reviewer material.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

AUDIT_PROTOCOL = "CILE-FULLTEXT-TRACE-AUDIT-1"
RECORD_KINDS = ("studies", "datasets", "analyses", "variable_uses", "findings")


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def _records(synthesis: dict[str, Any], key: str) -> list[dict[str, Any]]:
    value = synthesis.get(key)
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _ids(records: list[dict[str, Any]]) -> list[str]:
    return [item.get("id") for item in records if isinstance(item.get("id"), str)]


def _duplicate_count(values: list[str]) -> int:
    return max(0, len(values) - len(set(values)))


def summarise_synthesis(synthesis: Any) -> dict[str, Any]:
    if not isinstance(synthesis, dict):
        structural = {"invalid_top_level_shape": 1}
        return {
            "protocol": AUDIT_PROTOCOL,
            "record_counts": {kind: 0 for kind in RECORD_KINDS},
            "duplicate_record_ids": {kind: 0 for kind in RECORD_KINDS},
            "relation_failures": structural,
            "failure_families": sorted(structural),
            "structural_digest": digest(structural),
        }

    studies = _records(synthesis, "studies")
    datasets = _records(synthesis, "datasets")
    analyses = _records(synthesis, "analyses")
    variables = _records(synthesis, "variable_uses")
    findings = _records(synthesis, "findings")
    by_kind = {
        "studies": studies,
        "datasets": datasets,
        "analyses": analyses,
        "variable_uses": variables,
        "findings": findings,
    }
    record_counts = {kind: len(records) for kind, records in by_kind.items()}
    duplicate_record_ids = {kind: _duplicate_count(_ids(records)) for kind, records in by_kind.items()}

    study_ids = set(_ids(studies))
    dataset_by_id = {item["id"]: item for item in datasets if isinstance(item.get("id"), str)}
    analysis_by_id = {item["id"]: item for item in analyses if isinstance(item.get("id"), str)}
    variable_by_id = {item["id"]: item for item in variables if isinstance(item.get("id"), str)}

    failures: dict[str, int] = {
        "dataset_missing_study": 0,
        "analysis_missing_study": 0,
        "analysis_missing_dataset": 0,
        "analysis_dataset_study_mismatch": 0,
        "analysis_duplicate_dataset_ref": 0,
        "variable_missing_analysis": 0,
        "variable_missing_dataset": 0,
        "variable_dataset_not_in_analysis": 0,
        "variable_duplicate_dataset_ref": 0,
        "finding_missing_analysis": 0,
        "finding_missing_variable": 0,
        "finding_variable_analysis_mismatch": 0,
        "finding_duplicate_variable_ref": 0,
    }

    for dataset in datasets:
        if dataset.get("study_id") not in study_ids:
            failures["dataset_missing_study"] += 1

    for analysis in analyses:
        study_id = analysis.get("study_id")
        if study_id not in study_ids:
            failures["analysis_missing_study"] += 1
        refs = analysis.get("dataset_ids")
        refs = refs if isinstance(refs, list) else []
        string_refs = [ref for ref in refs if isinstance(ref, str)]
        failures["analysis_duplicate_dataset_ref"] += _duplicate_count(string_refs)
        for ref in string_refs:
            dataset = dataset_by_id.get(ref)
            if dataset is None:
                failures["analysis_missing_dataset"] += 1
            elif dataset.get("study_id") != study_id:
                failures["analysis_dataset_study_mismatch"] += 1

    for variable in variables:
        analysis_id = variable.get("analysis_id")
        analysis = analysis_by_id.get(analysis_id)
        if analysis is None:
            failures["variable_missing_analysis"] += 1
        refs = variable.get("dataset_ids")
        refs = refs if isinstance(refs, list) else []
        string_refs = [ref for ref in refs if isinstance(ref, str)]
        failures["variable_duplicate_dataset_ref"] += _duplicate_count(string_refs)
        analysis_datasets = set(analysis.get("dataset_ids", [])) if analysis else set()
        for ref in string_refs:
            if ref not in dataset_by_id:
                failures["variable_missing_dataset"] += 1
            if analysis is not None and ref not in analysis_datasets:
                failures["variable_dataset_not_in_analysis"] += 1

    for finding in findings:
        analysis_id = finding.get("analysis_id")
        if analysis_id not in analysis_by_id:
            failures["finding_missing_analysis"] += 1
        refs = finding.get("variable_use_ids")
        refs = refs if isinstance(refs, list) else []
        string_refs = [ref for ref in refs if isinstance(ref, str)]
        failures["finding_duplicate_variable_ref"] += _duplicate_count(string_refs)
        for ref in string_refs:
            variable = variable_by_id.get(ref)
            if variable is None:
                failures["finding_missing_variable"] += 1
            elif variable.get("analysis_id") != analysis_id:
                failures["finding_variable_analysis_mismatch"] += 1

    failures = {key: value for key, value in failures.items() if value}
    summary_basis = {
        "record_counts": record_counts,
        "duplicate_record_ids": duplicate_record_ids,
        "relation_failures": failures,
    }
    return {
        "protocol": AUDIT_PROTOCOL,
        **summary_basis,
        "failure_families": sorted(failures),
        "structural_digest": digest(summary_basis),
    }
