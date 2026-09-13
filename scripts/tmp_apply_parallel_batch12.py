#!/usr/bin/env python3
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "data" / "curation" / "reading_aid_overrides.json"

records = [
    {
        "candidateId": "CAND-ACADEMIC-2026-09-09-EXTRA-6b5b5e038ac4-030",
        "kind": "full_text_intro",
        "sourceLabel": "Bank of Italy Temi di discussione no. 1502 full-text PDF located with Parallel Search",
        "sourceUrl": "https://www.bancaditalia.it/pubblicazioni/temi-discussione/2025/2025-1502/en_tema_1502.pdf",
        "synopsis": "The 2025 Bank of Italy working paper studies whether financial distress increases Mafia infiltration of firms, using firm exposure to the Covid-19 shock and a firm-level infiltration proxy derived from investigative connections. It also examines whether extraordinary government support mitigated firms’ reliance on Mafia-linked liquidity.",
        "checkedAt": "2026-09-13",
        "note": "Parallel Search fetched the official Bank of Italy Temi di discussione no. 1502 PDF and matched Marco Castelluccio, Lucia Rizzica, the exact 2025 title and publication identity. Evidence basis: full_text. The earlier 2023 IFS working-paper CandidateRecord remains a distinct manifestation and is not silently merged or replaced. No verbatim text, private full-text ingestion, eligibility decision or canonicalisation is persisted here."
    },
    {
        "candidateId": "CAND-ACADEMIC-2026-09-10-EXTRA-f276bc827f57-007",
        "kind": "verified_abstract_source",
        "sourceLabel": "Rivisteweb publisher abstract located with Parallel Search",
        "sourceUrl": "https://www.rivisteweb.it/doi/10.1425/23230",
        "synopsis": "The article examines the links connecting Mafia groups with political, economic and professional spheres. It treats Mafia power as involving political action and the search for power, and emphasises the role of relationships with sectors of the ruling class and of bridge-building across otherwise different networks.",
        "checkedAt": "2026-09-13",
        "note": "Parallel Search fetched the exact Rivisteweb publisher record for Rocco Sciarrone, Stato e mercato 3/2006, pp. 369–402 and DOI 10.1425/23230, including its explicit Abstract section. Evidence basis: abstract_only. The article body is subscription/purchase access and was not verified as OA, so claims beyond the publisher abstract remain not_verifiable; no scientific decision is persisted."
    },
    {
        "candidateId": "CAND-ACADEMIC-2026-09-10-007",
        "kind": "verified_abstract_source",
        "sourceLabel": "OJP/NCJRS exact indexed abstract located with Parallel Search",
        "sourceUrl": "https://www.ojp.gov/ncjrs/virtual-library/abstracts/crime-crime-control-and-yakuza-contemporary-japan",
        "synopsis": "The 1997 article surveys contemporary Japanese crime and crime-control context alongside the role of the Yakuza, covering social features such as group duty and face as well as crime statistics and the position of gangsters in modern Japan.",
        "checkedAt": "2026-09-13",
        "note": "Parallel Search fetched the exact OJP/NCJRS record for NCJ 169383, K. Maguire, Criminologist 21(3), pp. 131–141, and its explicit Abstract section. Evidence basis: abstract_only. OJP states that no download is available, so full text was not verified and substantive details beyond the indexed abstract remain not_verifiable; no private source ingestion or scientific decision is inferred."
    }
]

payload = json.loads(PATH.read_text(encoding="utf-8"))
if payload.get("schemaVersion") != 1 or not isinstance(payload.get("records"), list):
    raise SystemExit("unexpected reading aid override schema")
existing = {row.get("candidateId") for row in payload["records"]}
for row in records:
    if row["candidateId"] in existing:
        raise SystemExit(f"candidate already overridden: {row['candidateId']}")
    payload["records"].append(row)
PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(f"appended {len(records)} reading-aid overrides")
