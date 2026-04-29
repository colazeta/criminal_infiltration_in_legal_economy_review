# Domain allowlist registry

Registry of domains authorised for discovery, snowballing, metadata enrichment, and validation.

## Authorised domains

| Domain | Purpose | Feed type | Automation status | Risk level | First execution | Notes |
|---|---|---|---|---|---|---|
| api.openalex.org | Works/authors/venues/references/citations | bibliographic API | automated | low | E0 | Core source |
| api.crossref.org | DOI metadata enrichment | metadata API | automated | low | E0 | DOI/title/author checks |
| api.semanticscholar.org | Citation graph + metadata | citation graph API | automated | low-medium | E0 | Respect rate limits |
| opencitations.net | Open citation links | citation graph | automated | low | E0 | Complementary citation source |
| doi.org | DOI resolution | identifier resolver | automated | low | E0 | Canonical DOI validation |
| api.unpaywall.org | OA location checks | OA metadata API | automated | low | E0 | Lawful OA only |
| pubmed.ncbi.nlm.nih.gov | PubMed interface | bibliographic database | assisted/automated | low | E0 | Domain-specific overlap |
| eutils.ncbi.nlm.nih.gov | NCBI programmatic access | bibliographic API | automated | low | E0 | Structured querying |
| europepmc.org | Metadata/full-text links | scholarly database | automated | low | E0 | OA-focused |
| arxiv.org | Preprints | repository | assisted | low | E0 | Relevance-gated |
| export.arxiv.org | arXiv API endpoint | repository API | automated | low | E0 | API access |
| zenodo.org | Deposits/datasets/reports | repository | assisted | low | E0 | Supplementary evidence |
| datacite.org | DOI search portal | metadata portal | assisted | low | E0 | Manual checks |
| api.datacite.org | DOI metadata API | metadata API | automated | low | E0 | Structured enrichment |
| openalex.org | Web interface support | bibliographic portal | assisted | low | E0 | Manual checks |
| crossref.org | Web interface support | metadata portal | assisted | low | E0 | Manual checks |
| semanticscholar.org | Web interface support | discovery portal | assisted | low-medium | E0 | Manual verification |

## Candidate domains not yet authorised

| Domain | Potential use | Condition for activation |
|---|---|---|
| _none yet_ |  |  |

## Domain expansion policy
Before each new execution, inspect this file.
If a required domain is not authorised:
1. identify the domain;
2. explain why needed;
3. classify it (core bibliographic API, citation graph, publisher platform, repository, search engine, institutional database);
4. state automation mode (automated vs manual/assisted);
5. add proposed row under candidates;
6. request explicit user approval before use.
