# Inizia da qui

Questo è l'indice pratico del progetto. Lo scopo attivo è unico: mantenere una
raccolta affidabile e consultabile della letteratura scientifica sulla
**criminal infiltration in the legal economy**.

Il progetto non cura più una raccolta separata su AML, riciclaggio o criminalità
economico-finanziaria. Questi fenomeni entrano nella review soltanto quando il
lavoro analizza la relazione di infiltrazione definita dal codebook.

## Le tre parti del progetto

1. **Biblioteca pubblica** — i lavori che hanno completato screening e gate di
   pubblicazione.
2. **Spazio di revisione** — candidati, decisioni ed etichette usati per
   stabilire che cosa appartiene alla review.
3. **Memoria della ricerca** — fonti, query, risultati, duplicati, gap e
   provenance necessari a rendere la living review verificabile.

Le tre parti restano separate. Un risultato di ricerca non è automaticamente un
paper rilevante; un paper rilevante non è automaticamente pubblico.

## Collegamenti principali

- [Consulta la biblioteca pubblica](https://colazeta.github.io/criminal_infiltration_in_legal_economy_review/)
- [Consulta le statistiche](https://colazeta.github.io/criminal_infiltration_in_legal_economy_review/stats.html)
- [Apri il pannello di curatela](https://colazeta.github.io/criminal_infiltration_in_legal_economy_review/curate.html)
- [Leggi come viene ampliata la letteratura](docs/methodology/expansion.md)
- [Leggi che cosa conta come infiltrazione criminale](docs/methodology/eligibility.md)
- [Proponi un paper](https://github.com/colazeta/criminal_infiltration_in_legal_economy_review/issues/new?template=candidate_intake.yml)
- [Consulta tutta la documentazione](docs/README.md)

## Che cosa vuoi fare?

| Obiettivo | Dove andare | Che cosa succede |
|---|---|---|
| Cercare un paper già approvato | [Biblioteca pubblica](https://colazeta.github.io/criminal_infiltration_in_legal_economy_review/) | Puoi cercare e filtrare i record pubblicati |
| Capire il perimetro scientifico | [Eligibility codebook](docs/methodology/eligibility.md) | Trovi il test in quattro parti per distinguere infiltrazione da fenomeni adiacenti |
| Capire come viene cercata la letteratura | [Strategia di espansione](docs/methodology/expansion.md) | Trovi le regole per ampliare la ricerca senza cambiare lo scope |
| Capire i numeri della sorveglianza | [Statistiche](docs/operations/daily-metrics.md) | Distingue risultati, lavori già noti, candidati e profondità effettivamente eseguita |
| Vedere i candidati da esaminare | [Workspace di curatela](https://colazeta.github.io/criminal_infiltration_in_legal_economy_review/curate.html) | I record pending restano distinti dal corpus valutato |
| Registrare una decisione | [Workspace di curatela](https://colazeta.github.io/criminal_infiltration_in_legal_economy_review/curate.html) | La decisione aggiorna la coda; non pubblica automaticamente il paper |
| Correggere titolo, DOI o autore | [Modulo metadati](https://github.com/colazeta/criminal_infiltration_in_legal_economy_review/issues/new?template=metadata_correction.yml) | Viene preparata una correzione sostenuta da una fonte |
| Aggiungere un possibile paper | [Modulo candidato](https://github.com/colazeta/criminal_infiltration_in_legal_economy_review/issues/new?template=candidate_intake.yml) | Il paper entra nella coda; non viene incluso automaticamente |
| Pubblicare un aggiornamento | [Guida alla pubblicazione](docs/operations/release.md) | I test ricostruiscono il sito dai record approvati |

## Parole usate nel repository

| Parola | Significato nel progetto |
|---|---|
| Candidato | Lavoro trovato o proposto, prima della decisione di rilevanza |
| Lavoro | L'opera scientifica sottostante, anche se più manifestazioni la descrivono |
| Record principale | L'unico record scelto per rappresentare un lavoro |
| Manifestazione | Un altro DOI, formato o edizione dello stesso lavoro |
| Screening | Lettura delle prove necessarie per decidere se il lavoro rientra nella review |
| Tema | Etichetta principale mostrata per un paper pubblicato |
| Escluso | Lavoro valutato fuori dal perimetro della criminal infiltration, con una ragione registrata |
| Duplicato | Record che descrive un lavoro già rappresentato da un altro record |
| Record pubblico | Paper che ha superato identità, screening, classificazione e pubblicazione |

Campi storici relativi a collezioni secondarie possono restare nei vecchi
snapshot o nello schema per compatibilità, ma non rappresentano una funzione
editoriale attiva.

## Il percorso di un paper

1. Una ricerca o una persona trova un possibile lavoro e lo registra nell'intake.
2. Il record viene materializzato nella coda e i metadati vengono controllati.
3. DOI e altri identificatori vengono riconciliati conservativamente; i possible
   duplicate non sono fusi automaticamente.
4. Una persona valuta il lavoro usando la regola di inclusione sulla criminal
   infiltration.
5. Se il lavoro è `eligible_core` o `eligible_contextual`, le etichette sostenute
   dall'evidenza possono essere registrate e il lavoro può proseguire verso i
   gate canonici e di pubblicazione.
6. Se è `not_eligible`, la ragione resta nell'audit. Non viene spostato in una
   raccolta AML parallela.
7. I test automatici ricostruiscono e pubblicano soltanto lo stato governato.

## Dove sono conservate le informazioni

| Area | Significato pratico |
|---|---|
| [`data/registry/`](data/registry/README.md) | Fonte ufficiale dei record correnti e della loro storia |
| [`data/curation/`](data/curation/README.md) | Coda dei candidati e storia append-only delle decisioni |
| [`docs/methodology/`](docs/README.md#methodology) | Regole di ricerca, inclusione e misurazione |
| [`docs/operations/`](docs/README.md#operations) | Automazioni, curatela, release e sito |
| [`scripts/`](scripts/) | Build e validatori deterministici |
| [`tests/`](tests/) | Controlli automatici sui contratti |
| [`site/`](site/) | Sito pubblico ed export generati |
| [`.github/`](.github/) | Moduli, workflow e pubblicazione |

## Che cosa può fare l'automazione

Può interrogare le fonti autorizzate, preparare candidati, deduplicare in modo
conservativo, conservare provenance e materializzare istruzioni già governate.
Non può inventare metadati, decidere autonomamente l'eleggibilità scientifica,
nascondere errori, fondere possible duplicate o ampliare il progetto a un tema
adiacente senza una modifica esplicita del protocollo.

Le regole tecniche degli agenti sono in [`AGENTS.md`](AGENTS.md).
