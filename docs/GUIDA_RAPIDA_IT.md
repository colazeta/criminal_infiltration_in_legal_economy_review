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
- [Statistiche giornaliere](https://colazeta.github.io/criminal_infiltration_in_legal_economy_review/stats.html)
- [Pannello di curatela](https://colazeta.github.io/criminal_infiltration_in_legal_economy_review/curate.html)
- [Strategia di espansione spiegata semplicemente](methodology/expansion.md)
- [Regola di inclusione](methodology/eligibility.md)
- [Indice completo del progetto](../INDEX.md)

## Che cosa puoi fare dal pannello

Il pannello ti porta a un modulo GitHub riservato a chi ha permessi di scrittura
sul repository. Non devi modificare a mano i file CSV.

Puoi chiedere di:

- cambiare il tema principale assegnato a un paper;
- escludere un paper indicando la ragione;
- unire un record duplicato al record corretto.

GitHub prepara la modifica, esegue tutti i controlli e apre una modifica
tracciabile. Le decisioni precedenti non vengono cancellate.

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
