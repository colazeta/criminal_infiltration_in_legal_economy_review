# Workspace di curatela

Il workspace separa due attività diverse:

1. la revisione dei **candidati**, che aggiorna soltanto la coda editoriale;
2. la manutenzione dei **record canonici**, che modifica i registri governati.

Nessuna delle due attività effettua auto-merge. Una decisione di screening non
equivale a promozione canonica e non approva la pubblicazione.

## Perché le decisioni avvengono dentro GitHub

GitHub Pages è un sito statico e pubblico. Non può custodire una password o un
personal access token capace di modificare il repository. La pagina
[`curate.html`](https://colazeta.github.io/criminal_infiltration_in_legal_economy_review/curate.html)
mostra quindi soltanto conteggi aggregati e collegamenti. Le schede e i moduli
che possono preparare una modifica si aprono nell'area GitHub autenticata.
I conteggi vengono ricostruiti da una proiezione pubblica chiusa che non contiene
titoli, identificatori, note, decisioni o identità del curatore.

## Coda dei candidati

La coda corrente è in `data/curation/review_queue.csv`. Il suo nucleo legacy
contiene 55 record distinti e resta verificabile separatamente anche quando la
coda cresce:

| Stage | Record | Significato |
|---|---:|---|
| `metadata_fix` | 2 | metadati bibliografici da riparare |
| `manual_review` | 9 | decisione umana sullo scope o sul valore contestuale |
| `abstract_full_text_review` | 25 | il titolo non basta; occorre abstract o full text |
| `legacy_rejection_review` | 19 | rigetto del pilot da ricontrollare con la regola corrente |

I due lavori già importati nel registro canonico non sono duplicati nella coda.
Le raccomandazioni legacy restano dichiarazioni storiche: non sono trasformate
in esclusioni, inclusioni o conferme di identità.

Il workflow `.github/workflows/materialize-curation.yml` crea una issue
idempotente per ogni scheda mancante e applica etichette di stage. Dopo il merge
di una decisione aggiunge alla scheda un collegamento all'azione, la chiude se
lo screening è concluso oppure la mantiene aperta se serve il full text. Non
interpreta l'evidenza e non prende decisioni.

## Dai batch giornalieri alla coda

Quando la sorveglianza crea una issue con titolo esatto
`[INTAKE][ACADEMIC] ACADEMIC-YYYY-MM-DD`, il workflow
`.github/workflows/intake-to-curation.yml` prepara il passaggio alla coda. Il
workflow accetta soltanto una issue aperta dal proprietario del repository e
convalida:

- identità del batch coerente tra titolo, modulo e manifesti;
- forma chiusa dei record e provenienza delle query Consensus/Exa;
- metadati, URL, identificatori, possibili duplicati e conflitti dichiarati;
- presenza dell'assessment di intake e dell'azione umana richiesta;
- salvaguardie contro screening e pubblicazione automatici.

La modifica entra in una pull request separata. Soltanto dopo il merge le nuove
righe producono schede individuali nella coda autenticata. Un record con
metadati parziali o conflittuali va in `metadata_fix`; gli altri vanno in
`abstract_full_text_review`. L'assessment dell'intake resta una traccia di
triage, non una decisione di eleggibilità.

## Registrare una decisione su un candidato

1. Aprire la [coda delle schede](https://github.com/colazeta/criminal_infiltration_in_legal_economy_review/issues?q=is%3Aissue+is%3Aopen+label%3A%22curation%3Aqueue%22).
2. Scegliere un candidato e leggere la sua provenienza.
3. Aprire il [modulo di decisione](https://github.com/colazeta/criminal_infiltration_in_legal_economy_review/issues/new?template=candidate_decision.yml).
4. Copiare il `candidate_id` e compilare stage, decisione, evidenza, motivazione
   e confidenza.
5. Per un'esclusione usare un codice esatto da
   `data/registry/exclusion_reasons.csv`.
6. Per `eligible_core` o `eligible_contextual` usare un tema già presente nella
   tassonomia.
7. Per `duplicate` indicare il candidato o paper che sopravvive e la prova di
   identità.
8. Scrivere `APPLY` nel campo di conferma e inviare la issue.

Soltanto una issue creata dal proprietario del repository e dotata
dell'etichetta `curation:decision` viene elaborata. Il workflow
`.github/workflows/candidate-curation.yml`:

1. legge il modulo senza eseguire testo contenuto nella issue;
2. verifica ID, combinazione dei campi e codici controllati;
3. aggiorna la proiezione corrente in `review_queue.csv`;
4. aggiunge una riga immutabile a `data/curation/actions.csv`;
5. esegue tutti i test e i controlli del sito;
6. prepara una branch e una pull request visibile;
7. collega la pull request alla issue che contiene l'istruzione umana.

La pull request registra file modificati, comandi e risultati, conteggi,
retrieval esterno e decisioni ancora irrisolte. Il merge resta umano.

### Decisioni disponibili

- `eligible_core`
- `eligible_contextual`
- `maybe_full_text_needed`
- `not_eligible`
- `duplicate`
- `not_academic`
- `not_retrievable`

Una decisione eleggibile richiede un tema governato. `not_eligible` richiede un
codice di esclusione coerente. `not_academic`, `not_retrievable` e `duplicate`
usano rispettivamente `NOT_ACADEMIC_SOURCE`, `FULL_TEXT_UNAVAILABLE` e
`DUPLICATE_RECORD`.

## Che cosa non fa una decisione sul candidato

Il workflow dei candidati non:

- assegna un `paper_id`;
- trasferisce automaticamente metadati nel registro canonico;
- modifica screening o pubblicazioni già registrati;
- dichiara verificato un DOI;
- pubblica il candidato nel sito;
- unisce la propria pull request.

Verifica dei metadati, promozione canonica e approvazione della nota pubblica
restano cambi distinti.

## Operazioni sui record canonici

La [console dei record canonici](https://github.com/colazeta/criminal_infiltration_in_legal_economy_review/actions/workflows/curation.yml)
continua a supportare tre operazioni.

### `change_topic`

Cambia il tema principale di un paper già rappresentato nel manifesto di
pubblicazione. Richiede `paper_id`, `topic_code`, motivazione ed evidenza. Una
nuova versione sostituisce soltanto la riga corrente; la storia resta intatta.

### `exclude_work`

Registra l'esclusione di un paper canonico usando un reason code governato,
motivazione, evidenza e confidenza. Il record resta nell'audit ed è trattenuto
dalla biblioteca corrente.

### `merge_duplicate`

Unisce due record canonici dopo una conferma esplicita di identità. Sposta
identificatori e occorrenze sul record sopravvissuto, mantiene la storia del
record ritirato e registra la relazione `duplicate_of`.

Per usare la console canonica selezionare **Run workflow**, compilare soltanto i
campi pertinenti e scrivere `APPLY`. Il workflow prova ad aprire una pull
request; quando il token automatico non può farlo, fornisce un collegamento
prefilled con lo stesso audit.

## Confine umano

Il software verifica la coerenza dell'istruzione, ma non interpreta il paper.
Stage, evidenza, motivazione, decisione, tema e identità del duplicato restano
attribuibili alla persona che compila il modulo. Nessuna informazione mancante
viene inventata e nessun esito legacy viene promosso silenziosamente.
