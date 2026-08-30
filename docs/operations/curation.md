# Pannello di curatela

Il pannello permette al proprietario del repository di applicare modifiche
editoriali senza intervenire direttamente sui CSV.

## Perché il comando finale è dentro GitHub

GitHub Pages è un sito statico e pubblico. Non può custodire in sicurezza una
password o un token capace di modificare il repository. Per questo la pagina
[`curate.html`](https://colazeta.github.io/criminal_infiltration_in_legal_economy_review/curate.html)
spiega le operazioni, mentre il comando viene eseguito dal modulo autenticato di
[GitHub Actions](https://github.com/colazeta/criminal_infiltration_in_legal_economy_review/actions/workflows/curation.yml).

Non bisogna mai incollare un personal access token nel sito.

## Operazioni disponibili

### `change_topic`

Cambia il tema principale assegnato a un paper.

Compilare:

- `paper_id`: il record da modificare;
- `topic_code`: un codice già presente in `taxonomy.csv`;
- `reason`: perché il tema precedente non è adeguato;
- `evidence`: il punto del paper o della scheda di screening che sostiene il
  nuovo tema.

Il workflow crea una nuova versione della riga di pubblicazione e aggiorna il
codice tematico. La versione precedente resta nella storia.

### `exclude_work`

Registra che un paper non appartiene alla review.

Compilare:

- `paper_id`;
- `reason_code`: una ragione breve e stabile, per esempio `outside_scope`;
- `reason`: la motivazione specifica per quel paper;
- `evidence`: la base esaminata, con un riferimento breve al punto rilevante;
- `confidence`: quanto è solida la decisione.

Il workflow aggiunge una nuova decisione `not_eligible`, porta il record nello
stato `review_excluded` e assicura che resti fuori dalla biblioteca pubblica.

### `merge_duplicate`

Unisce due record che rappresentano lo stesso lavoro.

Compilare:

- `paper_id`: il record duplicato da ritirare;
- `target_paper_id`: il record corretto che deve sopravvivere;
- `reason`: perché si tratta dello stesso lavoro;
- `evidence`: DOI, titolo, edizione o altra prova di identità verificata.

Il workflow sposta identificatori, manifestazioni e occorrenze di ricerca sul
record sopravvissuto. Il record ritirato diventa `superseded` e una relazione
`duplicate_of` rende visibile l'unione. Le decisioni precedenti non vengono
cancellate.

## Come usare il pannello

1. Aprire la [Curator console in GitHub Actions](https://github.com/colazeta/criminal_infiltration_in_legal_economy_review/actions/workflows/curation.yml).
2. Selezionare **Run workflow**.
3. Scegliere l'operazione.
4. Compilare soltanto i campi pertinenti.
5. Scrivere `APPLY` nel campo di conferma.
6. Avviare il workflow.

Il workflow:

1. applica l'istruzione in una copia temporanea;
2. esegue validazione del repository, test, build e controlli del sito;
3. crea un branch dedicato;
4. prova ad aprire una pull request;
5. se GitHub impedisce al token automatico di aprire PR, mostra nella pagina
   della run il collegamento **Create pull request** già pronto.

Il sistema non applica un'operazione se `APPLY` manca, se un ID non esiste, se
il tema non appartiene alla tassonomia o se la modifica produrrebbe uno stato
incoerente.

## Che cosa resta umano

Il pannello non interpreta il paper al posto del curatore. La selezione
dell'operazione, la motivazione e l'evidenza sono la decisione umana. Il codice
si limita a trasformarla in una modifica coerente, controllata e ricostruibile.
