# Protocollo operativo per literature review

## Obiettivo
Costruire una review sistematica sul tema **infiltrazione criminale nell'economia legale** con un flusso iterativo di snowballing, screening di eleggibilità e metriche di saturazione per ogni esecuzione.

---

## 1) Architettura generale del workflow

Ogni esecuzione (run) è composta da 5 fasi:

1. **Ingestion multi-feed**
2. **Deduplicazione + normalizzazione metadati**
3. **Screening eleggibilità (eligible/excluded)**
4. **Log motivazione esclusione**
5. **Calcolo metriche di saturazione**

### Entità minime da tracciare

- `paper_id` (chiave interna)
- DOI/Title/Authors/Year/Source
- `feed_origin` (da quale feed arriva)
- `discovery_method` (`seed`, `forward_snowball`, `backward_snowball`)
- `run_id` (identifica lo shot)
- `screening_decision` (`eligible`, `excluded`, `uncertain`)
- `exclusion_reason` (valorizzata se excluded)
- `screened_at`

---

## 2) Snowballing da molti feed

### Feed raccomandati (seed + discovery)

- Scopus
- Web of Science
- Dimensions
- OpenAlex
- Crossref
- Google Scholar (verifica manuale/assistita)
- SSRN / RePEc (se rilevante)
- Semantic Scholar

### Strategia

1. Definisci un set iniziale di query (keyword + sinonimi multilingua).
2. Esegui raccolta seed su tutti i feed.
3. Per ogni paper seed/eligible:
   - **Backward snowballing**: esplora riferimenti citati.
   - **Forward snowballing**: esplora articoli che lo citano.
4. Inserisci i candidati in coda screening.

---

## 3) Layer di eleggibilità

## Criterio principale
Un paper è **eligible** se tratta in modo sostanziale il tema:

> forme, meccanismi, canali, impatti o misurazione dell'infiltrazione criminale nell'economia legale.

### Decision tree minimo

1. Il paper tratta criminalità organizzata/economia criminale?  
   - Se no → `excluded`.
2. Esamina interazione con **settori/attori dell'economia legale**?  
   - Se no → `excluded`.
3. L'infiltrazione è elemento analitico centrale (non solo menzione marginale)?  
   - Se no → `excluded`.
4. Se sì a tutti → `eligible`.

### Stato `uncertain`
Usare `uncertain` quando mancano informazioni (es. solo abstract ambiguo), e forzare revisione manuale.

---

## 4) Ragioni di esclusione (obbligatorie)

Ogni `excluded` deve avere `exclusion_reason` standardizzata.

### Tassonomia suggerita

- `TOPIC_OFF_SCOPE` – Tema non pertinente.
- `NO_LEGAL_ECONOMY_LINK` – Nessun legame con economia legale.
- `CRIME_NOT_ORGANIZED` – Focus su reati non coerenti con il perimetro.
- `MENTION_ONLY` – Menzione superficiale, non analisi.
- `DOCUMENT_TYPE_EXCLUDED` – Tipo documento fuori perimetro (se definito).
- `LANGUAGE_EXCLUDED` – Lingua non coperta (se definita).
- `FULL_TEXT_UNAVAILABLE` – Non valutabile per mancanza testo.

Aggiungere anche un campo libero `exclusion_comment` (1-2 frasi).

---

## 5) Saturation per execution

Per ogni run (shot) calcolare:

- `N_screened_run`: paper valutati nel run.
- `N_new_eligible_run`: nuovi eligible aggiunti nel run.
- `saturation_rate_run`:  
  \[
  \text{saturation_rate_run} = \frac{N\_new\_eligible\_run}{N\_screened\_run}
  \]

Interpretazione: più è bassa, più il funnel è vicino alla saturazione.

---

## 6) Saturazione come incremento % sul totale eligible

Mantenere un cumulato storico:

- `N_eligible_total_before_run`
- `N_eligible_total_after_run`

Calcolo:

\[
\text{eligible_growth_pct_run} = \frac{N\_eligible\_total\_after\_run - N\_eligible\_total\_before\_run}{N\_eligible\_total\_before\_run} \times 100
\]

### Nota edge case
Se `N_eligible_total_before_run = 0`, usare baseline speciale:
- impostare `eligible_growth_pct_run = NA` nel primo run;
- riportare solo il valore assoluto `N_new_eligible_run`.

---

## 7) Schema dati minimo (tabelle)

### `papers`
- `paper_id` (PK)
- `doi`
- `title`
- `authors`
- `year`
- `source`
- `first_seen_run_id`

### `paper_screening`
- `screening_id` (PK)
- `paper_id` (FK)
- `run_id` (FK)
- `decision` (`eligible`, `excluded`, `uncertain`)
- `exclusion_reason` (nullable)
- `exclusion_comment` (nullable)
- `reviewer`
- `screened_at`

### `runs`
- `run_id` (PK)
- `run_started_at`
- `run_ended_at`
- `n_screened_run`
- `n_new_eligible_run`
- `saturation_rate_run`
- `eligible_total_before_run`
- `eligible_total_after_run`
- `eligible_growth_pct_run`

---

## 8) Soglie operative consigliate

Definire stop rule dopo almeno 3 run consecutivi, ad esempio:

- `saturation_rate_run < 0.05` (meno del 5% di nuovi eligible sui valutati del run)
- `eligible_growth_pct_run < 2%`

Se entrambe vere per 3 run consecutivi, considerare saturazione raggiunta.

---

## 9) Output di reporting per ogni run

- Conteggi: screened / eligible / excluded / uncertain
- Top ragioni di esclusione
- Nuovi eligible dal run
- Saturation rate run
- Growth % cumulata eligible
- Trend ultime 5 esecuzioni

---

## 10) Prossimo passo pratico

Implementare un primo foglio (o DB) con le tre tabelle indicate e automatizzare il calcolo delle metriche a fine run; in parallelo, finalizzare le query seed iniziali per ciascun feed.

## 11) Domain governance (allowlist)

Prima di ogni nuova execution, controllare `docs/domain_allowlist_registry.md`.

Regole operative:
- usare solo domini già autorizzati nel registry;
- se serve un nuovo dominio, proporlo nella sezione candidate e ottenere approvazione esplicita prima dell'uso;
- per ogni dominio autorizzato mantenere: purpose, feed type, automation status, risk level, first execution, notes.

Questa regola vale per tutte le fasi: discovery, snowballing, metadata enrichment e full-text verification.
