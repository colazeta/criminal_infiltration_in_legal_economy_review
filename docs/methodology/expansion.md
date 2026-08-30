# Come cresce l'archivio della letteratura

Questa è la versione operativa e leggibile della strategia di ricerca. Spiega
che cosa viene fatto, in quale ordine e quali decisioni restano umane. La
[reference tecnica](expansion-reference.md) conserva i dettagli necessari per
audit, metriche e riproducibilità.

## La versione breve

L'archivio cresce attraverso sei passaggi:

1. **Verificare la ricerca.** Controlliamo che ritrovi paper già noti e che non
   confonda l'infiltrazione con temi soltanto vicini.
2. **Cercare in più fonti.** Usiamo parole e strumenti diversi perché nessun
   database e nessuna espressione coprono da soli l'intero campo.
3. **Unire i risultati ripetuti.** Conserviamo ogni luogo in cui un paper è stato
   trovato, ma mostriamo al revisore un solo lavoro invece di molte copie.
4. **Seguire bibliografie e citazioni.** Guardiamo i lavori citati dai paper
   rilevanti e quelli più recenti che li citano.
5. **Leggere e classificare.** Una persona decide se il lavoro è rilevante e
   quali etichette sono davvero sostenute dal materiale esaminato.
6. **Misurare ciò che può mancare.** I risultati indicano dove deve concentrarsi
   il ciclo successivo.

Trovare un paper non significa includerlo. Includere un paper non significa
renderlo automaticamente pubblico.

## Le tre fasi di ogni ciclo

Nel repository compaiono le sigle E1, E2 ed E3:

| Fase | Significato semplice | Attività |
|---|---|---|
| **E1** | Cercare nelle fonti scientifiche | Eseguire ricerche documentate in database e strumenti accademici |
| **E2** | Guardare indietro | Esaminare le bibliografie dei paper rilevanti |
| **E3** | Guardare avanti | Cercare i lavori successivi che citano i paper rilevanti |

Un ciclo formale è completo soltanto quando tutte e tre le fasi sono state
eseguite e gli eventuali errori sono stati registrati. Un avviso rapido di un
motore di ricerca è utile, ma non equivale a un ciclo completo.

## Che cosa cerchiamo

La sola espressione “criminal infiltration” è troppo stretta. Un paper rilevante
può parlare invece di controllo di imprese, partecipazione nell'economia legale,
proprietà criminale, espansione territoriale, società di facciata o influenza
stabile su un mercato.

Ogni ricerca combina alcune di queste domande:

| Domanda | Esempi di parole utili |
|---|---|
| Chi porta l'interesse criminale? | organised crime, mafia, criminal network, illicit actor |
| Qual è la relazione? | control, ownership, participation, influence, embeddedness, capture |
| Dove avviene? | company, business, market, procurement, supply chain, professional service |
| Attraverso quale posizione? | owner, shareholder, director, manager, employee, intermediary, subcontractor |
| Che cosa si può osservare? | cambiamenti nella governance, concorrenza distorta, assegnazione di contratti, risultati d'impresa |
| Quali termini locali vengono usati? | mafia transplantation, condizionamento economico e termini equivalenti in altre lingue |

Riciclaggio, corruzione, investimento passivo e criminalità d'impresa vengono
cercati quando aiutano a riconoscere i confini del tema. Non vengono inclusi se
il paper non studia una relazione continuativa tra un interesse criminale e
l'economia legale.

## Le sette aree da coprire

Ogni ciclo formale controlla queste aree. Se una non è pertinente al ciclo, il
registro di ricerca ne spiega la ragione.

1. Paper che usano esplicitamente il linguaggio dell'infiltrazione.
2. Proprietà, controllo e governo delle imprese.
3. Mercati, appalti pubblici e singoli settori economici.
4. Espansione territoriale e presenza locale stabile.
5. Metodi, dati e indicatori usati per osservare il fenomeno.
6. Paesi, lingue e termini locali trascurati dalle ricerche precedenti.
7. Nuove pubblicazioni e nuovo vocabolario emersi dall'ultimo ciclo.

## Perché servono più fonti

Ogni strumento ha un compito diverso. Ripetere la stessa query ovunque non basta.

| Fonte | Compito principale nel progetto |
|---|---|
| Consensus | Cercare paper peer-reviewed e controllare i dettagli dei candidati |
| OpenAlex | Eseguire ricerche strutturate e ripetibili; mappare autori, temi e citazioni |
| Exa | Trovare lavori che descrivono lo stesso fenomeno con un linguaggio molto diverso |
| Scite | Aggiungere ricerca scientifica e contesto delle citazioni quando l'accesso dell'account è disponibile |
| Crossref | Verificare DOI e dati bibliografici |
| Semantic Scholar | Controllare un secondo grafo di paper e citazioni |
| OpenCitations | Aggiungere collegamenti di citazione aperti basati sui DOI |
| Unpaywall | Trovare, quando esiste, una versione ad accesso aperto lecita |

Nessuna fonte decide l'inclusione. Un ordine dei risultati, un'etichetta di
citazione o un punteggio di somiglianza sono soltanto indizi da esaminare.

## Passaggio 1: verificare la ricerca prima di fidarsi

Si parte con due piccoli insiemi di riferimento:

- paper già confermati come rilevanti;
- paper su argomenti vicini che non devono essere inclusi senza prove ulteriori.

Il primo gruppo mostra se una query perde lavori importanti già noti. Il secondo
mostra se la ricerca sta scivolando verso riciclaggio, corruzione o criminalità
d'impresa in generale. Il registro indica quali paper di riferimento ciascuna
fonte riesce o non riesce a trovare.

È un controllo pratico di qualità, non la prova che la ricerca abbia trovato
tutto ciò che esiste.

## Passaggio 2: registrare bene ogni ricerca

Per ogni fonte e query si conservano:

- data;
- query o prompt esatto;
- filtri, limiti temporali e tetti ai risultati;
- numero di risultati restituiti;
- errori o pagine non accessibili;
- identificatore della fonte e DOI, quando disponibili;
- fotografia o checksum, quando le regole della fonte lo permettono.

Se un servizio restituisce soltanto i primi risultati, la ricerca viene marcata
come limitata. Non può essere descritta come completa.

## Passaggio 3: gestire i risultati ripetuti

Lo stesso lavoro può comparire in molte ricerche e attraverso diversi DOI o
record editoriali. Ogni occorrenza viene conservata; poi si decide se i record
rappresentano la stessa opera.

L'identità viene controllata in questo ordine:

1. DOI identico;
2. altro identificatore scientifico stabile;
3. titolo normalizzato e anno;
4. somiglianza approssimativa del titolo, usata soltanto per segnalare un dubbio.

Quando due record sono davvero lo stesso lavoro, il curatore sceglie quello che
resta principale. Gli altri identificatori e le occorrenze di ricerca vengono
collegati a esso, non cancellati in silenzio.

## Passaggio 4: seguire bibliografie e citazioni

Dopo il primo screening:

- E2 controlla le bibliografie dei paper rilevanti;
- E3 cerca i lavori successivi che li citano;
- ogni nuovo paper rilevante entra nel ciclo di citazioni successivo;
- eventuali differenze tra fornitori di citazioni restano registrate.

Una ricerca di citazioni fallita resta un errore aperto. Non viene contata come
una ricerca con zero risultati.

## Passaggio 5: valutare ogni lavoro

Il revisore controlla:

1. che sia un lavoro scientifico;
2. che identità e metadati di base siano affidabili;
3. che sia riconoscibile un interesse criminale;
4. che esista un obiettivo nell'economia legale;
5. che il paper analizzi accesso, partecipazione, influenza, controllo o presenza
   stabile;
6. che questa relazione sia una parte sostanziale dell'analisi.

Se titolo e abstract non bastano, il lavoro resta in attesa finché non può essere
esaminato il testo completo. Etichette e ragioni di esclusione devono essere
sostenute dal materiale realmente letto.

## Passaggio 6: scegliere la ricerca successiva

Alla fine di un ciclo completo si chiede:

- Quale fonte ha trovato paper davvero nuovi?
- Quali query hanno restituito quasi soltanto lavori già noti?
- Quanti paper esaminati erano effettivamente rilevanti?
- È apparso un nuovo settore, meccanismo, metodo, paese o risultato?
- Esistono ancora errori tecnici che nascondono una parte della letteratura?
- Quale area resta coperta debolmente?

Le risposte determinano il ciclo successivo. Una copertura debole è una ragione
per cercare meglio, non una prova che la letteratura non esista.

## Quando può rallentare la ricerca?

Il sistema non dichiara mai che la letteratura sia completa. Può soltanto
richiedere una decisione umana di arresto dopo **tre cicli completi consecutivi**
nei quali:

- i paper eleggibili aumentano di meno del 2%;
- meno del 2% dei nuovi paper esaminati risulta eleggibile;
- non compare nessuna nuova etichetta controllata;
- non rimane aperto nessun errore importante di recupero.

Anche dopo questa decisione, gli avvisi periodici continuano a cercare nuovi
lavori.

## Che cosa può fare l'automazione

L'automazione può interrogare fonti approvate, togliere le ripetizioni esatte da
un gruppo di candidati e preparare una issue. Non può decidere l'eleggibilità,
inventare metadati mancanti, unire identità dubbie o pubblicare un paper.

Il [pannello di curatela](../operations/curation.md) offre al proprietario un
percorso autenticato in GitHub per cambiare un tema, escludere un lavoro o unire
un duplicato confermato senza modificare manualmente i CSV.

## Checklist del primo ciclo completo

- [ ] I paper rilevanti e quelli di confine usati per il controllo sono documentati.
- [ ] Tutte le sette aree hanno un piano di ricerca o una ragione di esclusione.
- [ ] Le ricerche E1 sono complete e i loro limiti sono visibili.
- [ ] DOI e dati bibliografici sono stati verificati.
- [ ] E2 copre le bibliografie dei paper rilevanti scelti.
- [ ] E3 copre le citazioni successive dello stesso insieme.
- [ ] Ogni nuovo lavoro unico ha uno stato di screening corrente.
- [ ] Errori e record non accessibili restano visibili.
- [ ] Il ciclo riporta paper nuovi, paper eleggibili, sovrapposizioni e nuove etichette.
- [ ] L'eventuale pubblicazione è una decisione separata del curatore.

Per campi specifici dei fornitori, identificatori, metriche e standard di
rendicontazione, consulta la [reference tecnica](expansion-reference.md).
