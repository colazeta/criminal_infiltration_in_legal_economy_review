# Inizia da qui

Questo è l'indice pratico del progetto. Per una versione ancora più breve puoi
leggere la [guida rapida](docs/GUIDA_RAPIDA_IT.md).

Lo scopo è uno solo: mantenere una raccolta affidabile e consultabile dei paper
sull'infiltrazione criminale nell'economia legale.

## Le tre parti del progetto

1. **Biblioteca pubblica** — il sito dove chiunque può cercare i paper che hanno
   completato il controllo e la pubblicazione.
2. **Spazio di revisione** — i record, le decisioni e le etichette usati per
   stabilire che cosa appartiene alla review.
3. **Memoria della ricerca** — la storia delle fonti interrogate, dei risultati,
   dei duplicati e delle parti di letteratura che potrebbero ancora mancare.

Le tre parti restano separate. Un risultato di ricerca non è automaticamente un
paper rilevante; un paper rilevante non è automaticamente pubblico.

## Collegamenti principali

- [Consulta la biblioteca pubblica](https://colazeta.github.io/criminal_infiltration_in_legal_economy_review/)
- [Apri il pannello di curatela](https://colazeta.github.io/criminal_infiltration_in_legal_economy_review/curate.html)
- [Leggi come viene ampliata la letteratura](docs/methodology/expansion.md)
- [Leggi che cosa conta come infiltrazione criminale](docs/methodology/eligibility.md)
- [Proponi un paper](https://github.com/colazeta/criminal_infiltration_in_legal_economy_review/issues/new?template=candidate_intake.yml)
- [Consulta tutta la documentazione](docs/README.md)

## Che cosa vuoi fare?

| Obiettivo | Dove andare | Che cosa succede |
|---|---|---|
| Cercare un paper già approvato | [Biblioteca pubblica](https://colazeta.github.io/criminal_infiltration_in_legal_economy_review/) | Puoi cercare e filtrare i record pubblicati |
| Capire come viene cercata la letteratura | [Strategia di espansione](docs/methodology/expansion.md) | Trovi i sei passaggi usati per cercare, unire e valutare i paper |
| Cambiare il tema di un paper | [Pannello di curatela](https://colazeta.github.io/criminal_infiltration_in_legal_economy_review/curate.html) | GitHub prepara una modifica controllata senza richiedere l'editing manuale dei CSV |
| Escludere un paper | [Pannello di curatela](https://colazeta.github.io/criminal_infiltration_in_legal_economy_review/curate.html) | La decisione e la motivazione vengono aggiunte alla storia; il paper resta fuori dal sito |
| Unire due record duplicati | [Pannello di curatela](https://colazeta.github.io/criminal_infiltration_in_legal_economy_review/curate.html) | Un record rimane quello principale; identificatori e provenienze vengono conservati |
| Correggere titolo, DOI o autore | [Modulo per i metadati](https://github.com/colazeta/criminal_infiltration_in_legal_economy_review/issues/new?template=metadata_correction.yml) | Viene preparata una correzione sostenuta da una fonte |
| Aggiungere un possibile paper | [Modulo candidato](https://github.com/colazeta/criminal_infiltration_in_legal_economy_review/issues/new?template=candidate_intake.yml) | Il paper entra nella coda di revisione; non viene incluso automaticamente |
| Eseguire un ciclo completo di ricerca | [Modulo ciclo E1–E3](https://github.com/colazeta/criminal_infiltration_in_legal_economy_review/issues/new?template=review_cycle.yml) | Le ricerche nelle fonti e nelle citazioni vengono documentate insieme |
| Pubblicare un aggiornamento | [Guida alla pubblicazione](docs/operations/release.md) | I test ricostruiscono il sito dai record approvati e GitHub Pages lo pubblica |

## Parole usate nel repository

| Parola | Significato nel progetto |
|---|---|
| Candidato | Paper trovato da una ricerca o proposto da una persona; non è ancora stata presa una decisione di rilevanza |
| Lavoro | L'opera scientifica sottostante, anche se più DOI o pagine editoriali la descrivono |
| Record principale | L'unico record scelto per rappresentare quel lavoro |
| Manifestazione | Un altro DOI, formato o edizione dello stesso lavoro |
| Screening | Lettura delle prove necessarie per decidere se il lavoro rientra nella review |
| Tema | Etichetta principale mostrata per un paper pubblicato |
| Trattenuto | Record conservato ma non mostrato nella biblioteca corrente |
| Escluso | Lavoro valutato fuori ambito, con una ragione registrata |
| Duplicato | Record che descrive un lavoro già rappresentato da un altro record |
| Record pubblico | Paper che ha superato i controlli di identità, screening, classificazione e pubblicazione |

## Il percorso di un paper

1. Una ricerca o una persona trova un possibile paper.
2. Titolo, autori, anno e identificatori vengono controllati.
3. I record ripetuti vengono ricondotti allo stesso lavoro.
4. Una persona valuta il paper usando la regola di inclusione.
5. La persona registra una decisione e soltanto le etichette sostenute dalle
   prove esaminate.
6. Un'azione esplicita del curatore stabilisce se il record può essere pubblico.
7. I test automatici ricostruiscono e pubblicano il sito.

Nei passaggi 4–6 il sistema può preparare il lavoro, ma non può inventare o
nascondere la decisione scientifica.

## Dove sono conservate le informazioni

| Area | Significato pratico |
|---|---|
| [`data/registry/`](data/registry/README.md) | Fonte ufficiale dei record correnti e della loro storia |
| [`docs/methodology/`](docs/README.md#methodology) | Regole di ricerca, inclusione e misurazione |
| [`docs/operations/`](docs/README.md#operations) | Funzionamento del pannello, delle automazioni, delle release e del sito |
| [`scripts/`](scripts/) | Programmi che preparano le modifiche, costruiscono la biblioteca e cercano errori |
| [`tests/`](tests/) | Prove automatiche che obbligano il sistema a fermarsi quando una regola è violata |
| [`site/`](site/) | Sito pubblico e file scaricabili generati |
| [`.github/`](.github/) | Moduli, controlli automatici e pubblicazione |

## Che cosa può fare l'automazione

Può:

- interrogare le fonti accademiche autorizzate;
- preparare i record candidati;
- riconoscere identificatori identici e segnalare possibili duplicati;
- applicare un'istruzione esplicita inviata dal pannello del curatore;
- controllare il risultato e preparare una modifica GitHub visibile;
- pubblicare record che hanno già completato l'intero percorso.

Non può:

- inventare metadati, prove o motivazioni mancanti;
- trattare una somiglianza come prova che due record sono lo stesso lavoro;
- decidere la rilevanza usando soltanto un titolo o un punteggio;
- nascondere una ricerca fallita;
- pubblicare un candidato irrisolto;
- cancellare o sovrascrivere una decisione precedente.

Le regole tecniche degli agenti sono in [`AGENTS.md`](AGENTS.md). Per l'uso
normale del progetto, questo indice è il punto di partenza.
