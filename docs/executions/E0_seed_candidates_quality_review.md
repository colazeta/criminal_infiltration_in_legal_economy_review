# E0 Seed Candidates Quality Review

This quality review evaluates `data/raw/e0_seed_candidates_draft.md` using a strict scope standard before any promotion to official seed CSV.

## Per-candidate assessment

| seed_id | likely final decision | scope fit | reason specificity | metadata verification needs | DOI verification needs | main risk notes |
|---|---|---|---|---|---|---|
| E0-D001 | promote_to_core_seed | direct | high | confirm edition details | likely none/book | low risk; strong anchor |
| E0-D002 | promote_to_contextual_seed | contextual-strong | medium-high | confirm bibliographic details | likely none/book | potentially duplicative with D001 |
| E0-D003 | verify_before_promotion | contextual | medium | verify exact title/editors | not priority | broad handbook risk |
| E0-D004 | verify_before_promotion | contextual | medium | verify chapter-level targeting | not priority | too broad unless chapter-scoped |
| E0-D005 | verify_before_promotion | likely direct | medium | verify exact report/paper identity | verify if DOI exists | may be report literature |
| E0-D006 | verify_before_promotion | likely direct | medium | verify real paper existence | verify | possible fabricated/unclear citation |
| E0-D007 | promote_to_core_seed | direct | high | verify journal metadata | verify DOI | strong procurement-infiltration link |
| E0-D008 | verify_before_promotion | likely direct | medium | verify exact publication | verify | title may be provisional |
| E0-D009 | keep_as_candidate_seed | contextual | medium | verify publication format | verify | could be generic entrepreneurship |
| E0-D010 | verify_before_promotion | contextual | medium | verify exact source | verify | may be too conceptual |
| E0-D011 | downgrade_or_reject | contextual-weak | low | verify if specific article exists | verify | too generic as currently stated |
| E0-D012 | verify_before_promotion | contextual | medium | verify real bibliographic record | verify | uncertain citation details |
| E0-D013 | promote_to_contextual_seed | contextual-strong | high | verify publication metadata | verify DOI | corruption focus may be indirect |
| E0-D014 | verify_before_promotion | likely direct | medium | verify specific empirical source | verify | unclear reference granularity |
| E0-D015 | verify_before_promotion | likely direct | medium | verify exact work | verify | title may be non-canonical |
| E0-D016 | downgrade_or_reject | contextual-weak | low | verify if record exists | verify | procurement cartel focus may miss OC infiltration |
| E0-D017 | keep_as_candidate_seed | contextual | medium | specify concrete report/article | no DOI likely | report quality heterogeneity |
| E0-D018 | verify_before_promotion | likely direct | medium | verify exact paper | verify | uncertain metadata |
| E0-D019 | verify_before_promotion | likely direct | medium | verify publication identity | verify | high relevance but currently vague |
| E0-D020 | verify_before_promotion | likely direct | medium | verify source | verify | potential over-contextualization |
| E0-D021 | keep_as_candidate_seed | contextual | medium | identify specific scholarly source | unlikely | may be policy-heavy, not academic |
| E0-D022 | verify_before_promotion | direct/contextual | medium | verify exact paper | verify | currently too generic citation |
| E0-D023 | promote_to_contextual_seed | contextual-strong | medium-high | verify bibliographic details | verify if available | useful embeddedness framework |
| E0-D024 | verify_before_promotion | likely direct | medium | verify exact study | verify | may overlap with methodological set |
| E0-D025 | promote_to_contextual_seed | contextual-strong | high | verify bibliographic details | likely none/book | broad AML lens but foundational |
| E0-D026 | verify_before_promotion | contextual | medium | verify exact title/source | verify | may not directly target legal-economy infiltration |
| E0-D027 | verify_before_promotion | likely direct | medium | verify publication identity | verify | uncertain bibliographic precision |
| E0-D028 | verify_before_promotion | contextual-strong | medium | verify exact source | verify | facilitator focus needs clear legal-economy link |
| E0-D029 | promote_to_contextual_seed | contextual-method | high | verify edition/source | likely none/book | robust methods anchor |
| E0-D030 | verify_before_promotion | direct-method | medium | identify exact Transcrime paper | verify if DOI exists | currently placeholder-like |
| E0-D031 | verify_before_promotion | contextual-method | medium | verify exact paper | verify | uncertain citation details |
| E0-D032 | verify_before_promotion | contextual-method | medium | verify exact source | verify | may be too broad if generic methods piece |

## 1) Candidates recommended for direct promotion into `data/raw/e0_seed_candidates.csv`

### Promote to core_seed
- E0-D001
- E0-D007

### Promote to contextual_seed
- E0-D002
- E0-D013
- E0-D023
- E0-D025
- E0-D029

## 2) Candidates requiring verification before promotion
- E0-D003, E0-D004, E0-D005, E0-D006, E0-D008, E0-D010, E0-D012
- E0-D014, E0-D015, E0-D018, E0-D019, E0-D020, E0-D022, E0-D024
- E0-D026, E0-D027, E0-D028, E0-D030, E0-D031, E0-D032

## 3) Candidates to downgrade or reject
- E0-D011: downgrade_or_reject unless a specific, in-scope article is identified.
- E0-D016: downgrade_or_reject unless explicit organized-crime infiltration linkage is shown.

## 4) Gap analysis by the 8 seed strata
- **Strongest coverage:** conceptual/theoretical (1), procurement/market capture (4), methods (8).
- **Moderate but fragile (verification-heavy):** mafia-legal business (2), sectoral infiltration (5), ownership/governance (6), laundering (7).
- **Weakest precision:** criminal entrepreneurship/criminal firms (3), where several entries are generic and risk scope drift.
- **Structural gap:** limited clearly verified, article-level records with confident metadata/DOI across strata 2, 5, 6, 7.

## 5) Recommendations for targeted additions before finalising E0
1. Add 6–10 **high-certainty journal articles** with verified DOI, prioritizing strata 2, 5, 6, 7.
2. Replace generic/placeholder records with **specific paper-level citations** (avoid “topic labels” as entries).
3. Ensure each stratum has at least:
   - 2 likely core_seed,
   - 1–2 contextual_seed,
   with explicit legal-economy linkage.
4. For procurement and sectoral papers, prioritize records with clear empirical bases (judicial/company/procurement data).
5. Keep books/handbooks as contextual anchors, but avoid overloading E0 with broad references that weaken precision.
