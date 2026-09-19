# Consolidamento: stato verificato al 19 settembre 2026

**Il consolidamento richiesto non è concluso.** La migrazione delle estrazioni e
delle annotazioni è stata eseguita nell'archivio esistente; bibliografia,
coperture e supporti mantengono ancora autorità separate. La nuova proiezione
pubblica resta nella PR #797, in bozza, finché i controlli sul servizio attivo
non possono essere completati. Non è sufficiente unirla per dichiarare risolto
il problema complessivo.

## Implementazione ed evidenze

| Ambito | Esito verificato | Limite attuale |
|---|---|---|
| Modello | Ontologia riutilizzata; diagrammi, cardinalità, censimento fisico e matrice dei campi in `docs/architecture/` | Restano le incongruenze dei candidati V2 e delle autorità bibliografiche descritte sotto |
| Estrazioni | Migrazione 0007 eseguita su entrambe le proposte; ripetizione senza nuove scritture; lettori e scrittori usano fatti e relazioni normalizzati | Nessuna proposta è diventata una decisione scientifica |
| Conservazione privata | Backup cifrato e ripristino isolato verificati del database a 38 tabelle, 4.796 righe SQL e 419 elementi KV | Non è ancora riuscito un backup completo dello stato successivo a 46 tabelle |
| Annotazioni | Migrazione 0008 e acquisizione di 317 annotazioni eseguite; audit integrale a 46 tabelle riuscito | Il successivo controllo finale di acquisizione è fallito; l'attivazione del rilascio non è avvenuta |
| Proiezione pubblica | PR #797 sostituisce il lettore di commenti con API chiuse dell'archivio e definizioni condivise per schede, filtri e statistiche | Codice verificato localmente; nuova API e nuovo lettore non ancora pubblicati |
| Sito già pubblicato | Caricamento automatico limitato e rimozione dei collegamenti di menu AML, con verifica dei 294 identificativi | Stile conservato; i percorsi bibliografici storici e il vecchio lettore di annotazioni non sono ancora ritirati |
| Automazione esistente | Prompt aggiornato e riletto: verifica dello scrittore prima della ricerca, ricevuta e rilettura obbligatorie, niente conteggio di commenti come salvataggi | Orario e abilitazione invariati; nessun nuovo scheduler; la persistenza deve tornare disponibile |

Le ricevute dei primi tre passaggi sono in `runtime-evidence-2026-09-19.json`,
`extraction-migration-evidence-2026-09-19.json` e
`annotation-migration-evidence-2026-09-19.json`. Distinguono copie verificate,
migrazioni eseguite, ripetizioni, stato pubblico e controlli falliti.

La nuova verifica del sito delle **14:55 UTC** ha riletto tutti i 294 candidati
e i relativi supporti serviti, con zero identificativi mancanti o record diversi
dall'esportazione attesa. `published-site-evidence-2026-09-19.json` conserva
digest, versione e ricevuta. Il rilascio delle statistiche giornaliere è invece
fallito per debito di validazione; questo risultato non è nascosto dietro la
pubblicazione riuscita del registro. La PR #797 supera entrambi i controlli CI
sul commit `e9684d681d3bef99f3a4eaf16d368ed89478a37b`, oltre a 780 test Python e
401 test Node locali. Rimane in bozza per il blocco della persistenza attiva.

## Blocco tecnico osservato

La richiesta firmata al servizio restituisce HTTP 503,
`service_auth_nonce_get_unavailable`, prima dell'operazione richiesta. Il backup
preventivo fallisce alla lettura iniziale del catalogo e impedisce correttamente
gli ulteriori deploy. Non sono stati saltati conservazione o ripristino.

Il controllo protetto [35449240717](https://github.com/colazeta/criminal_infiltration_in_legal_economy_review/actions/runs/35449240717)
ha misurato, per l'account e il giorno UTC, 9.759.627 righe lette, 65.474 scritte
e 35.905.536 byte occupati. Sono contatori aggregati, non dati scientifici.
Il piano effettivo non è stato osservato: la causa «quota esaurita» rimane
un'inferenza, non una diagnosi confermata. I limiti del piano gratuito sono
5 milioni di letture e 100.000 scritture al giorno; il rinnovo giornaliero è alle
00:00 UTC secondo la [documentazione Cloudflare](https://developers.cloudflare.com/durable-objects/platform/pricing/).
La ricevuta chiusa è `storage-incident-evidence-2026-09-19.json`.

Sono state eliminate le scansioni private integrali dall'osservatore orario,
mantenendole nei controlli di migrazione/rilascio. La PR #797 usa ricerche
indicizzate per le relazioni delle annotazioni e pagine SQL del backup con
continuazione per rowid, evitando scansioni OFFSET crescenti. Nessun piano,
permesso, motore o servizio aggiuntivo è stato modificato. Queste correzioni non
costituiscono la prova di un ripristino del servizio già avvenuto.

## Popolazione conservata e riconciliazione

La copia degli ingressi delle 14:03 UTC comprende 797 issue/PR e 1.304 commenti,
senza duplicati di identificativo e con tutti i riferimenti ai genitori presenti.
Un'altra copia conserva 335 PR, 221 revisioni e 317 commenti di revisione.
Sono acquisizioni API in una finestra temporale, non snapshot atomici di GitHub;
non ricostruiscono contenuti modificati prima delle osservazioni disponibili.
Le copie e i registri privati sono accompagnati da digest e verifiche di ripristino.

La prova riproducibile `scripts/architecture/preflight_annotations.mjs` importa
e ripete tutti gli ingressi catturati, controlla tutte le schede, i filtri e le
statistiche dei 294 candidati e ripristina l'intera popolazione isolata. Risultato:
317 annotazioni, di cui 291 collegate a candidati attivi, 8 irrisolte e 18 relative
a identificativi non presenti nel registro corrente. Nessuna eccezione è eliminata
o collegata per similarità del titolo. La prova non contiene le due proposte
private reali e non equivale al backup corrente di produzione.

Il censimento `scripts/architecture/audit_intake_identities.py` usa gli stessi
validatori di intake/terminali, gli ingressi catturati e l'ascendenza Git locale.
Conserva ogni identificativo in un registro privato di migrazione, senza scrivere
candidati o decisioni. `intake-identity-census-2026-09-19.json` registra:

| Unità | Numero | Significato |
|---|---:|---|
| Identificativi nel registro operativo | 294 | Tutti presenti anche in intake interpretabili |
| Identificativi distinti negli intake interpretabili | 343 | Comprendono identità d'ingresso non materializzate |
| Identificativi d'ingresso assenti dal registro | 49 | Non equivalgono a 49 opere mancanti |
| Di questi, da ingressi validati nella copia | 14 | Tutti con possibili corrispondenze operative già esistenti; nessuna identità canonica stabilita |
| Di questi, con terminale assente | 14 | Dodici con possibili corrispondenze, due senza |
| Di questi, con terminale/contesto non valido | 21 | Sette con possibili corrispondenze, quattordici senza |
| Intake non interpretabili e conservati | 2 | Gli originali rimangono disponibili; nessun contenuto inventato |

La conservazione di queste 49 identità e delle relazioni proposte deve rientrare
nella migrazione dei candidati. Una corrispondenza DOI o bibliografica osservata
non è una decisione di identità scientifica. Gli input con terminali mancanti o
non validi non autorizzano automaticamente nuova registrazione.

## Passaggi ancora necessari

1. Ripristinare l'accesso al servizio esistente e ottenere il backup/ripristino
   completo dello stato a 46 tabelle. Ripetere acquisizione, idempotenza e audit
   integrale; poi verificare sul servizio attivo l'API e ogni candidato della
   nuova proiezione. Il deploy deve precedere il passaggio del sito.
2. Completare la conservazione degli altri ambiti: stato del
   `SubmissionCoordinator`, metadati dei deployment e manifest esterno unico.
   Il connettore GitHub disponibile rifiuta l'endpoint `deployments` come non
   supportato; questo limite non viene mascherato come copia completa.
3. Trasferire autorità, scrittori e lettori di candidati, bibliografia, coperture,
   sintesi e registri scientifici nel database esistente. Il percorso attuale
   CSV → esportazione Pages → target Worker è ancora circolare. I JSON di
   supporto e gli override non sono stati rinominati artificiosamente «derivati».
4. Correggere il vincolo V2 che permette un solo candidato per opera e rendere
   esplicite le asserzioni bibliografiche concorrenti, le identità d'ingresso,
   le supersessioni e le revoche negli altri domini. La scelta dell'ultima
   proposta strutturata per timestamp rimane una regola da sostituire.
5. Dopo verifiche complete, ritirare i vecchi scrittori e pubblicare le sole
   esportazioni ricostruibili. Verificare aggiornamento e ritiro attraverso
   l'intera catena anche per fonti, documenti e approvazioni, oltre alle annotazioni.

Le decisioni umane mancanti riguardano identità canoniche, conflitti scientifici,
valutazioni, calibrazione e autorizzazioni alla pubblicazione/redistribuzione.
I problemi di schema, servizio, migrazione e scrittura elencati sopra sono lavoro
tecnico ancora da completare: non vengono trasformati in richieste di approvazione
scientifica per giustificare una transizione incompleta.
