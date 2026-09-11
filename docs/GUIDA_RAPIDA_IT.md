# Guida rapida al progetto

Questo repository mantiene un archivio della letteratura scientifica sulla
**criminal infiltration in the legal economy**. Questo è l'unico perimetro
editoriale attivo.

## Le tre parti del progetto

1. **Biblioteca pubblica.** È il sito consultabile dai lettori. Contiene soltanto
   i paper che hanno completato il percorso di controllo e pubblicazione.
2. **Spazio di revisione.** Contiene i record, le decisioni e le classificazioni
   usate per stabilire quali lavori appartengono alla review.
3. **Memoria della ricerca.** Conserva fonti, query, citazioni esplorate,
   duplicati e problemi di recupero necessari all'audit.

Un paper trovato non è automaticamente rilevante. Un paper giudicato rilevante
non è automaticamente pubblicato sul sito.

## I collegamenti principali

- [Biblioteca pubblica](https://colazeta.github.io/criminal_infiltration_in_legal_economy_review/)
- [Statistiche](https://colazeta.github.io/criminal_infiltration_in_legal_economy_review/stats.html)
- [Pannello di curatela](https://colazeta.github.io/criminal_infiltration_in_legal_economy_review/curate.html)
- [Strategia di espansione](methodology/expansion.md)
- [Regola di inclusione](methodology/eligibility.md)
- [Indice completo del progetto](../INDEX.md)

## Che cosa puoi fare dal workspace

Il workspace apre le singole schede nell'area autenticata. Non devi modificare
a mano i file CSV.

Per un candidato puoi registrare inclusione core o contestuale, necessità di
full text, esclusione con codice governato, fonte non accademica, irreperibilità
o duplicato confermato. Il sistema aggiorna soltanto la coda e prepara una pull
request: non assegna automaticamente un paper ID e non pubblica il lavoro.

Se un articolo riguarda AML, riciclaggio, corruzione o criminalità
economico-finanziaria ma non soddisfa il test sulla relazione di infiltrazione,
resta `not_eligible` per questo progetto. Non viene spostato in una raccolta AML
separata.

Quando un batch giornaliero contiene candidati, GitHub prepara una pull request
che li trasferisce nella coda editoriale conservando provenance, identificatori,
conflitti e azione umana richiesta. Dopo il merge compaiono come schede
individuali. Questo passaggio non decide se il paper è eleggibile.

Per i paper già canonici puoi inoltre cambiare il tema principale, escludere un
record o unirlo a un duplicato confermato. GitHub conserva sempre la storia
precedente e non effettua auto-merge.

## Come cresce la letteratura

La ricerca espande termini, geografie, settori, metodologie, bibliografie e
citazioni, ma non cambia il perimetro scientifico. La guida completa è in
[`docs/methodology/expansion.md`](methodology/expansion.md). I dettagli tecnici
necessari alla riproducibilità sono nella
[reference metodologica](methodology/expansion-reference.md).

## Come leggere le statistiche

Le statistiche descrivono la discovery e la crescita del registro/corpus senza
trasformare automaticamente i candidati in lavori inclusi. Gli errori tecnici
restano auditabili ma le esecuzioni incomplete non vengono presentate come
osservazioni statistiche pubbliche.

Formule e definizioni sono nella [guida alle statistiche](operations/daily-metrics.md).

## Il punto essenziale

L'automazione svolge il lavoro ripetitivo: ricerca, controlli, preparazione dei
record e aggiornamento del sito. Le scelte interpretative restano visibili e
attribuibili. Il sistema non include, esclude o fonde silenziosamente un paper e
non amplia lo scope oltre la criminal infiltration senza una modifica esplicita
del protocollo.
