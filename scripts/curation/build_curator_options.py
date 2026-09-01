#!/usr/bin/env python3
"""Build the public-safe controlled options used by the curator interface.

The projection contains only codebook values. It never reads or exports the
candidate queue, curator actions, evidence or reviewer identities.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

try:
    from .apply_candidate_decision import CONFIDENCE, DECISIONS, STAGES
except ImportError:  # Direct script execution from the repository root.
    from apply_candidate_decision import CONFIDENCE, DECISIONS, STAGES


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = ROOT / "site" / "data" / "curator-options.json"

STAGE_OPTIONS = (
    ("title_abstract", "Titolo e abstract", "Decisione basata su titolo e abstract esaminati."),
    ("full_text", "Testo completo", "Decisione basata sul testo completo o su sezioni identificate."),
    ("seed_validation", "Validazione seed", "Riesame governato di un lavoro proveniente dal seed."),
)
DECISION_OPTIONS = (
    ("eligible_core", "Includi nel nucleo", "La relazione di infiltrazione è centrale e sostenuta dall'evidenza."),
    ("eligible_contextual", "Includi come contestuale", "Contributo concettuale, comparativo o metodologico necessario."),
    ("maybe_full_text_needed", "Serve altro testo", "L'evidenza disponibile non consente ancora una decisione."),
    ("not_eligible", "Escludi dal perimetro", "Il lavoro non soddisfa il confine concettuale della review."),
    ("duplicate", "Segna come duplicato", "Un altro candidato o paper rappresenta lo stesso lavoro."),
    ("not_academic", "Fonte non accademica", "Il record non rientra nelle fonti scientifiche ammesse."),
    ("not_retrievable", "Non reperibile", "Non è stato possibile ottenere l'evidenza necessaria."),
)
CONFIDENCE_OPTIONS = (
    ("high", "Alta"),
    ("medium", "Media"),
    ("low", "Bassa"),
)


class CuratorOptionsError(ValueError):
    """Raised when controlled registries cannot produce a safe projection."""


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise CuratorOptionsError(f"{path.name} has no header")
        return [dict(row) for row in reader]


def build_payload(root: Path = ROOT) -> dict[str, object]:
    if {code for code, _, _ in STAGE_OPTIONS} != STAGES:
        raise CuratorOptionsError("Curator stage options differ from the decision validator")
    if {code for code, _, _ in DECISION_OPTIONS} != DECISIONS:
        raise CuratorOptionsError("Curator decision options differ from the decision validator")
    if {code for code, _ in CONFIDENCE_OPTIONS} != CONFIDENCE:
        raise CuratorOptionsError("Curator confidence options differ from the decision validator")

    reasons = read_csv(root / "data" / "registry" / "exclusion_reasons.csv")
    topics = [
        row
        for row in read_csv(root / "data" / "registry" / "taxonomy.csv")
        if row.get("dimension") == "topic"
    ]
    secondary_collections = read_csv(
        root / "data" / "registry" / "secondary_collections.csv"
    )
    reason_codes = [row.get("code", "").strip() for row in reasons]
    topic_codes = [row.get("code", "").strip() for row in topics]
    secondary_codes = [
        row.get("collection_code", "").strip() for row in secondary_collections
    ]
    if "" in reason_codes or len(reason_codes) != len(set(reason_codes)):
        raise CuratorOptionsError("Exclusion reasons contain an empty or duplicate code")
    if "" in topic_codes or len(topic_codes) != len(set(topic_codes)):
        raise CuratorOptionsError("Topic taxonomy contains an empty or duplicate code")
    if "" in secondary_codes or len(secondary_codes) != len(set(secondary_codes)):
        raise CuratorOptionsError(
            "Secondary collections contain an empty or duplicate code"
        )

    return {
        "schemaVersion": 2,
        "screeningStages": [
            {"code": code, "label": label, "description": description}
            for code, label, description in STAGE_OPTIONS
        ],
        "decisions": [
            {"code": code, "label": label, "description": description}
            for code, label, description in DECISION_OPTIONS
        ],
        "confidenceLevels": [
            {"code": code, "label": label} for code, label in CONFIDENCE_OPTIONS
        ],
        "exclusionReasons": [
            {
                "code": row["code"].strip(),
                "label": row["label"].strip(),
                "definition": row["definition"].strip(),
            }
            for row in reasons
        ],
        "topics": [
            {
                "code": row["code"].strip(),
                "label": row["label"].strip(),
                "definition": row["definition"].strip(),
            }
            for row in topics
        ],
        "secondaryCollections": [
            {
                "code": row["collection_code"].strip(),
                "label": row["label"].strip(),
                "description": row["description"].strip(),
                "eligibilityRelation": row["eligibility_relation"].strip(),
            }
            for row in secondary_collections
        ],
    }


def write_payload(payload: dict[str, object], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = build_payload(args.root.resolve())
    write_payload(payload, args.output)
    print(
        "[OK] Built curator options: "
        f"{len(payload['decisions'])} decisions, "
        f"{len(payload['exclusionReasons'])} exclusion reasons, "
        f"{len(payload['topics'])} topics and "
        f"{len(payload['secondaryCollections'])} secondary collection(s)."
    )


if __name__ == "__main__":
    try:
        main()
    except (OSError, csv.Error, CuratorOptionsError) as exc:
        raise SystemExit(f"[CURATOR OPTIONS BLOCKED] {exc}") from exc
