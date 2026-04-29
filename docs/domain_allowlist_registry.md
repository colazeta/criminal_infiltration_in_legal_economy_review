# Domain allowlist registry

Questo documento registra i domini internet autorizzati per la review sistematica con snowballing sul tema dell'infiltrazione criminale nell'economia legale.

Il registro serve a tracciare:
- domini abilitati nell'ambiente;
- feed supportato;
- motivazione d'uso;
- livello di rischio;
- esecuzione di primo utilizzo;
- modalità di utilizzo (automatica o manuale/assistita).

## Domain categories

### Core bibliographic and metadata APIs

| Domain | Purpose | Feed type | Automation status | Risk level | First execution | Notes |
|---|---|---|---|---|---|---|
| api.openalex.org | Scholarly works, authors, venues, citations/references | database search; snowballing | automated | low | E0 | Core open bibliographic source |
| api.crossref.org | DOI metadata and bibliographic enrichment | metadata enrichment | automated | low | E0 | DOI/title/author validation |
| api.semanticscholar.org | Citation graph and paper metadata | forward/backward snowballing | automated | low-medium | E0 | Respect API limits |
| opencitations.net | Open citation data | citation graph | automated | low | E0 | Alternative citation source |
| doi.org | DOI resolution | identifier validation | automated | low | E0 | Canonical DOI checks |
| api.unpaywall.org | Open access discovery | full-text support | automated | low | E0 | Only lawful OA versions |
| api.datacite.org | DataCite DOI metadata | metadata enrichment | automated | low | E0 | Dataset/report DOI enrichment |

### Specialist/open scholarly feeds

| Domain | Purpose | Feed type | Automation status | Risk level | First execution | Notes |
|---|---|---|---|---|---|---|
| pubmed.ncbi.nlm.nih.gov | PubMed search and metadata | database search | assisted/automated | low | E0 | Criminology/public health overlaps |
| eutils.ncbi.nlm.nih.gov | NCBI programmatic access | database search | automated | low | E0 | Structured PubMed queries |
| europepmc.org | Europe PMC metadata/full text | database search/full text | automated | low | E0 | OA scholarly source |
| arxiv.org | Preprints | database search | assisted | low | E0 | Working papers/preprints |
| export.arxiv.org | arXiv API | metadata retrieval | automated | low | E0 | Use only when relevant |
| zenodo.org | Datasets and scholarly deposits | supplementary material | assisted | low | E0 | Datasets/reports |
| datacite.org | DataCite portal | metadata lookup | assisted | low | E0 | Manual DOI cross-check |
| openalex.org | OpenAlex web interface | discovery support | assisted | low | E0 | Manual exploration |
| crossref.org | Crossref web interface | discovery support | assisted | low | E0 | Manual metadata checks |
| semanticscholar.org | Semantic Scholar web interface | discovery support | assisted | low-medium | E0 | Manual verification |

### Institutional databases and publisher platforms (authorised with constraints)

| Domain | Purpose | Feed type | Automation status | Risk level | First execution | Notes |
|---|---|---|---|---|---|---|
| scopus.com | Bibliographic database | database search | manual/assisted | medium | E0 | Institutional access + lawful use required |
| www.scopus.com | Bibliographic database | database search | manual/assisted | medium | E0 | Institutional access + lawful use required |
| webofscience.com | Bibliographic database | database search | manual/assisted | medium | E0 | Institutional access + lawful use required |
| www.webofscience.com | Bibliographic database | database search | manual/assisted | medium | E0 | Institutional access + lawful use required |
| scholar.google.com | Broad discovery | search engine | manual/assisted | medium | E0 | No scraping |
| jstor.org | Academic literature | publisher/archive platform | manual/assisted | medium | E0 | Verify license terms |
| www.jstor.org | Academic literature | publisher/archive platform | manual/assisted | medium | E0 | Verify license terms |
| sciencedirect.com | Publisher platform | full-text verification | manual/assisted | medium | E0 | Record-level checks only |
| www.sciencedirect.com | Publisher platform | full-text verification | manual/assisted | medium | E0 | Record-level checks only |
| link.springer.com | Publisher platform | full-text verification | manual/assisted | medium | E0 | Record-level checks only |
| tandfonline.com | Publisher platform | full-text verification | manual/assisted | medium | E0 | Record-level checks only |
| www.tandfonline.com | Publisher platform | full-text verification | manual/assisted | medium | E0 | Record-level checks only |
| journals.sagepub.com | Publisher platform | full-text verification | manual/assisted | medium | E0 | Record-level checks only |
| academic.oup.com | Publisher platform | full-text verification | manual/assisted | medium | E0 | Record-level checks only |
| cambridge.org | Publisher platform | full-text verification | manual/assisted | medium | E0 | Record-level checks only |
| www.cambridge.org | Publisher platform | full-text verification | manual/assisted | medium | E0 | Record-level checks only |
| onlinelibrary.wiley.com | Publisher platform | full-text verification | manual/assisted | medium | E0 | Record-level checks only |
| heinonline.org | Legal database | database search/full text | manual/assisted | medium | E0 | License-constrained access |
| brill.com | Publisher platform | full-text verification | manual/assisted | medium | E0 | Record-level checks only |
| degruyterbrill.com | Publisher platform | full-text verification | manual/assisted | medium | E0 | Record-level checks only |
| journals.openedition.org | OA journals platform | database search/full text | assisted | low | E0 | Humanities/social sciences |
| cairn.info | Journals platform | database search/full text | manual/assisted | medium | E0 | License-constrained access |
| rivisteweb.it | Journals platform | database search/full text | manual/assisted | medium | E0 | Italian journals focus |

### Institutional repositories

| Domain | Purpose | Feed type | Automation status | Risk level | First execution | Notes |
|---|---|---|---|---|---|---|
| iris.unipa.it | Institutional repository | repository search | assisted | low | E0 | University repository |
| iris.unina.it | Institutional repository | repository search | assisted | low | E0 | University repository |
| air.unimi.it | Institutional repository | repository search | assisted | low | E0 | University repository |
| iris.unito.it | Institutional repository | repository search | assisted | low | E0 | University repository |
| iris.uniroma1.it | Institutional repository | repository search | assisted | low | E0 | University repository |

## Candidate domains not yet authorised

| Domain | Potential use | Condition for activation |
|---|---|---|
| _none currently_ |  |  |

## Domain expansion policy (mandatory)

Prima di iniziare ogni nuova execution, ispezionare questo file.

Se una execution richiede un dominio non autorizzato, non espandere la lista in modo silenzioso. Occorre:

1. identificare il dominio richiesto;
2. spiegare perché è necessario;
3. classificarlo come: core bibliographic API, citation graph, publisher platform, repository, search engine, o institutional database;
4. indicare se l'uso previsto è automated retrieval o manual/assisted consultation;
5. aggiungere una proposta in `Candidate domains not yet authorised`;
6. chiedere approvazione utente prima dell'uso.

## Change log

| Date | Execution | Domain added | Reason | Approved by | Notes |
|---|---|---|---|---|---|
| 2026-04-29 | E0 | Initial allowlist set | Environment configuration for multi-feed snowballing | User | Initial setup from approved list |
