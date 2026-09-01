# Guida rapida al progetto

Questo repository mantiene un archivio della letteratura scientifica sulla
presenza e sull'influenza di interessi criminali nell'economia legale.

## Le tre parti del progetto

1. **Biblioteca pubblica.** È il sito consultabile dai lettori. Contiene soltanto
   i paper che hanno completato il percorso di controllo e pubblicazione.
2. **Spazio di revisione.** Contiene i record, le decisioni e le classificazioni
   usate per stabilire quali lavori appartengono alla review.
3. **Memoria della ricerca.** Conserva le fonti interrogate, le query, le
   citazioni esplorate, i duplicati e gli eventuali errori di recupero.

Un paper trovato non è automaticamente rilevante. Un paper giudicato rilevante
non è automaticamente pubblicato sul sito.

## I collegamenti principali

- [Biblioteca pubblica](https://colazeta.github.io/criminal_infiltration_in_legal_economy_review/)
- [Raccolta AML più ampia](https://colazeta.github.io/criminal_infiltration_in_legal_economy_review/aml.html)
- [Statistiche giornaliere](https://colazeta.github.io/criminal_infiltration_in_legal_economy_review/stats.html)
- [Pannello di curatela](https://colazeta.github.io/criminal_infiltration_in_legal_economy_review/curate.html)
- [Strategia di espansione spiegata semplicemente](methodology/expansion.md)
- [Regola di inclusione](methodology/eligibility.md)
- [Indice completo del progetto](../INDEX.md)

## Che cosa puoi fare dal workspace

Il workspace mostra i conteggi della coda e apre le singole schede nell'area
GitHub autenticata. Non devi modificare a mano i file CSV.

La coda iniziale contiene 55 candidati materializzati: 2 con metadati da
correggere, 9 da valutare manualmente, 25 da leggere almeno a livello di
abstract/full text e 19 vecchi rigetti da ricontrollare. Questi ultimi non sono
considerati esclusioni finché una persona non registra una nuova decisione.

Per un candidato puoi registrare inclusione core o contestuale, necessità di
full text, esclusione con codice governato, fonte non accademica, irreperibilità
o duplicato confermato. Il sistema aggiorna soltanto la coda e prepara una pull
request: non assegna automaticamente un paper ID e non pubblica il lavoro.

Se un articolo è `not_eligible` per la review sull'infiltrazione ma resta
importante per antiriciclaggio o criminalità economico-finanziaria, puoi anche
selezionare `broader_aml` e spiegare separatamente questa rilevanza. L'articolo
resta escluso dal corpus principale; diventa visibile nella pagina AML solo dopo
verifica canonica e una seconda approvazione editoriale.

Quando un batch giornaliero contiene candidati, GitHub prepara una pull request
che li trasferisce nella coda editoriale conservando fonti, query, conflitti e
azione umana richiesta. Dopo il merge compaiono come schede individuali. Questo
passaggio non decide se il paper è eleggibile.

Per i paper già canonici puoi inoltre cambiare il tema principale, escludere un
record o unirlo a un duplicato confermato. GitHub conserva sempre la storia
precedente e non effettua auto-merge.

## Come cresce la letteratura

Ogni ciclo completo comprende:

1. ricerche nelle fonti accademiche;
2. esame delle bibliografie dei paper rilevanti;
3. ricerca dei lavori successivi che li citano;
4. eliminazione delle copie senza perdere la provenienza;
5. screening umano;
6. misurazione di ciò che è stato trovato e di ciò che può ancora mancare.

La guida completa, ma leggibile, è in
[`docs/methodology/expansion.md`](methodology/expansion.md). I dettagli tecnici
necessari alla riproducibilità sono conservati separatamente nella
[reference metodologica](methodology/expansion-reference.md).

## Come leggere le statistiche quotidiane

La pagina delle statistiche distingue quattro livelli: risultati restituiti,
risultati unici, lavori già conosciuti e nuovi candidati inviati alla revisione.
Segnala separatamente una giornata completa, parziale o fallita. Perciò un errore
di una fonte non viene contato come una giornata con zero paper.

Questi numeri descrivono la scoperta, non l'eleggibilità. Le formule e gli esempi
sono nella [guida alle statistiche](operations/daily-metrics.md).

## Il punto essenziale

L'automazione svolge il lavoro ripetitivo: ricerca, controlli, preparazione dei
record e aggiornamento del sito. Le scelte interpretative restano visibili e
attribuibili. Il sistema non include, esclude o fonde silenziosamente un paper.
