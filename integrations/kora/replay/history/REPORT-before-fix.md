# Replay del pilota Kora — 19 settembre 2026

**Esito: 80 casi sintetici eseguiti localmente, 68 superati e 12 discrepanze. Nessuna dichiarazione di readiness.** La suite nativa è stata tentata ma non ha eseguito nodi: errore di accesso al lock della sessione. Due ricostruzioni da evidenze pubbliche sono parziali e non sono state trasformate in attivazioni inventate.

## Perimetro verificato

- Contratto corrente letto da `main` fissato a `9b0a6211b33950509c5e63180ad71af0c2f3d48f`: AGENTS.md, two-lane-delivery.md, completion-first-v5.md, hourly-hybrid-v4.md. URL e blob SHA in [source-manifest.json](evidence/source-manifest.json); copie dei documenti in `evidence/`.
- Pilota: sorgente congelata esportata dalla release **rel_4wbyk58gsiuzfh8f**, workspace **oltre**, environment **production**. Esportazione riuscita: 15 file sorgente, più metadato locale `.kora/release-source.json`.
- PR #779 osservata aperta/draft al commit `1a62fd94149063999289c35220e2bfeade4600f6`.
- Il checkout originale è stato inizialmente verificato in detached HEAD su `dd212442dec3f02278f24c8c004f51d04f725f9a` con le tre correzioni dei timestamp locali. Non è stato modificato. Il controllo Git finale è stato rifiutato per ownership del sandbox: non è stata cambiata la configurazione `safe.directory`.
- I quattro script della release sono identici byte per byte ai file locali. Operazioni, processo e organizzazione sono semanticamente equivalenti dopo parsing YAML; il manifest `kora.yaml` invece differisce. Hash e confronto in [source-comparison.json](source-comparison.json).
- Nessun accesso a storage/API privati della review, nessun aggiornamento GitHub, registro, decisione scientifica, dato o servizio della review. Nessuna nuova release, deploy, automazione o esecuzione live. I file prodotti sono solo in questa cartella di output e nell'area di lavoro temporanea.

## Metodo e indipendenza degli attesi

[prepare.mjs](prepare.mjs) definisce esplicitamente input e attesi a partire dai documenti di contratto fissati sopra. Non importa né chiama le funzioni sotto test. [cases.json](cases.json) conserva input, attesi, provenienza sintetica, clausola e note di interpretazione.

[replay.mjs](replay.mjs) esegue il vero `evaluateFrontier`, passa il suo risultato al vero `routeActivation` e confronta l'output con gli attesi già definiti. La composizione riproduce il passaggio di stato tra i due nodi; non esegue il motore del workflow, il gateway o i wrapper runtime SDK. Sono verificati anche gli schemi input/output e l'assenza di mutazioni dell'input.

Per i fixture nativi del router, il frontier in ingresso è scritto nella tabella indipendente degli attesi, non ricavato eseguendo il frontier sotto test. Gli assert usano `gate: true`; le discrepanze non sono convertite in warning né escluse. I sette input invalidi sono testati localmente con il JSON schema del processo: non sono fixture Kora dichiarate falsamente superate.

## Copertura ed esiti

| Gruppo | Eseguiti localmente | Ambito |
|---|---:|---|
| Catena frontier → router | 52 | Tutte le 8 rotte; Lane A e B; ENGINEER ammesso solo per B; precedenze e collisioni |
| Frontier | 21 | NONE, F0–F7, separazione Completed/Validated, requisiti mancanti, incoerenze e versioni non correnti |
| Rifiuto input da schema | 7 | WIP negativo/frazionario, lane sconosciuta, timestamp oggetto, booleano stringa, proprietà extra, writer mancante |
| Totale | **80** | **68 pass, 12 discrepanze** |

WIP: 0, 5, 6 e 7 su entrambe le lane; 6 consente COMPLETE, 7 blocca il percorso ordinario. Writer assente: NOOP. Ripetizione invariata: COMPLETE bloccato; nel caso sintetico accoppiato il cambiamento di prerequisito lo riabilita. Un'altra strategia sicura di calibrazione resta selezionabile: il flag non equivale a un blocco globale di ogni lavoro.

Tutti i 52 output di routing mantengono `side_effect_authorized=false` e `pilot_mode=observe_only`, anche nei casi discrepanti. Ciò prova l'output dei router, non l'efficacia di un sandbox di rete o l'autorizzazione di future integrazioni.

Sono pronti **76 fixture nativi**: i 3 originali e 73 nuovi. Tutti passano la verifica offline dello schema Kora Test, dello schema input del nodo e del timestamp come stringa con parser YAML 1.1. [fixture-validation.json](fixture-validation.json) contiene l'esito. Questo non sostituisce l'esecuzione nativa.

## Discrepanze da mantenere visibili

| Casi | Osservazione | Interpretazione e limite |
|---|---|---|
| 2: A/B-starvation-over-complete | Atteso RESOLVE, ottenuto COMPLETE | V4 impone RESOLVE per debito più vecchio di 24 ore o coda ≥20 prima di nuova ricerca. V5 mantiene la starvation guard. Il test interpreta `identity_debt_due=true` come guard obbligatoria scattata; la struttura non espone età/coda né distingue nuova ricerca da lavoro già avviato. È una discrepanza condizionata a questa mappatura, non la prova che ogni debito debba precedere COMPLETE. |
| 4: A/B-scout-wip-collision e persist-wip-collision | Atteso BLOCKED secondo la promessa del pilota; ottenuto SCOUT/PERSIST con WIP=7 | Il pilota dichiara blocco per WIP >6. Il contratto review dà priorità allo scouting dovuto e richiede di terminare scritture sicure. La precedenza è da chiarire: bloccare automaticamente PERSIST potrebbe violare la chiusura transazionale. Questi fallimenti misurano la promessa non qualificata del pilota, non prescrivono una correzione automatica. |
| 4: A/B-inconsistent-scout e inconsistent-persist | Atteso BLOCKED, ottenuto SCOUT/PERSIST nonostante `frontier_consistent=false` | Il router esegue i due ritorni prioritari prima del controllo di coerenza. Anche qui il perimetro del blocco globale va conciliato con scouting e chiusura delle scritture. L'output di osservazione non autorizza comunque effetti. |
| 2: validated-without-ready e validated-stale-versions | `validation_accepted=true` insieme a incoerenza | Il frontier propaga `validated` senza subordinare l'etichetta di accettazione ai prerequisiti correnti. Atteso false secondo il significato di F7 corrente. Il router ordinario può bloccare, ma l'evidenza emessa dal frontier resta contraddittoria. Non è stata modificata alcuna reale accettazione scientifica. |

Gli attesi dei 12 casi non sono stati riscritti per farli passare. Le collisioni interpretative e i limiti dello schema devono essere risolti prima di trattare questa suite come contratto definitivo di rilascio. Risultati completi con atteso/ottenuto in [local-results.json](local-results.json).

### Differenza separata: manifest della release

Il manifest esportato della release ha `metadata.name=oltre`, `network.defaultAction=allow`, `inheritManaged=true` e limiti macchina aggiunti. Il manifest locale del pilota ha `metadata.name=cile-review-control-plane` e `network.defaultAction=deny`. Solo `kora.yaml` differisce semanticamente; gli altri YAML differiscono per serializzazione.

La release esportata quindi **non conferma la promessa di rete deny del sorgente locale**. Non è stato determinato se la causa sia normalizzazione/esportazione della piattaforma o il percorso di creazione precedente; non si deduce da questo alcun traffico di rete né un deploy. Nessuna modifica alla policy è stata applicata. Le operazioni esaminate chiamano solo le funzioni locali e non dichiarano secret/extension bindings.

## Evidenze reali: ricostruzione limitata

Sono stati letti i 171 commenti pubblici restituiti dal connettore per issue #696. La ricerca è circoscritta a questo thread e ai documenti correnti, non è un censimento di tutte le esecuzioni. Sono conservati soltanto due checkpoint operativi pertinenti, con URL, in [public-checkpoints.json](evidence/public-checkpoints.json).

1. [Checkpoint CAND-…-009](https://github.com/colazeta/criminal_infiltration_in_legal_economy_review/issues/696#issuecomment-5695849306): Lane A, metadata verificati, primo gate mancante F1, scouting già soddisfatto, percorso di retention/claim non disponibile.
2. [Checkpoint F2→F3](https://github.com/colazeta/criminal_infiltration_in_legal_economy_review/issues/696#issuecomment-5703165562): Lane A, candidato `CAND-ACADEMIC-2026-09-09-002` riportato a F2, confronto F3 non eseguibile per dispatch autorizzato mancante, scouting già soddisfatto.

Questi sono resoconti storici pubblici, non ricevute private verificate ora. Non sono stati confusi con il diverso CAND-…-EXTRA-…-002 menzionato dal contratto. In entrambi mancano **17 campi richiesti** per un input completo, tra cui istante esatto, WIP, scritture in corso e rotte concorrenti. I valori mancanti restano assenti. Il resoconto non consente di assegnare un output router univoco.

**Replay reali completi eseguiti: 0. Ricostruzioni parziali documentate: 2.** [reconstructed-cases.json](evidence/reconstructed-cases.json) espone la mappatura dei soli fatti attestati; [completeness-audit.json](evidence/completeness-audit.json) elenca ogni campo mancante. Nessun caso sintetico viene conteggiato come progresso di un paper, calibrazione o evidenza di attività reale.

## Esecuzione nativa e limite di accesso

All'inizio della sessione `kora auth whoami --json` ha confermato `oltre`, ruolo owner; `release source` è riuscito. Il successivo comando:

```text
kora test suite --workspace outputs/kora-replay/pilot --environment production --org oltre --json
```

è terminato con exit code 1 prima dei test: `EPERM` aprendo `session.json.refresh.lock` nella directory Kora protetta dal sandbox. [native-results.json](native-results.json) conserva la risposta. È un blocco locale di accesso al rinnovo sessione, non un test fallito del nodo e non la prova che le credenziali siano invalide. Nessun aggiramento del lock o del controllo d'accesso, nessun retry con override.

**Test nativi eseguiti in questa sessione: 0; gatePassed non disponibile.** I precedenti 3/3 e la validazione della release della conversazione non sono sostituiti da un nuovo risultato e non coprono questi replay. Non sono stati avviati run live, usati saved-run refs, ricreate release o effettuati deploy.

## Limiti funzionali non provati dal replay

- Il pilota riceve booleane già calcolate. Non verifica concretamente timezone/finestra dovuta, terminali/idempotenza, proprietà dei candidati, claim/fencing, età/coda d'identità, receipt/hashes o accettazione umana.
- L'anti-repeat qui è un segnale fornito dall'esterno; non esiste nel pilota uno storico di strategia/prerequisito per verificarlo. Non prova il blocco di ripetizioni di scouting, calibrazione o engineering né la persistenza attraverso attivazioni.
- Il limite WIP non distingue completamento di un paper attivo, parcheggio, nuovo pull e micro-batch di calibrazione.
- Il significato di “deepest owned paper” è assunto dall'input: non vengono selezionati candidati reali.
- Nessuna prova del motore Kora, del gateway, dell'esecuzione dei wrapper SDK, di rete/runtime o di progressi duraturi sui dati. Tutte le rotte finali del pilota terminano in nodi `none`.
- Le decisioni scientifiche non sono state validate da queste booleane né da fixture sintetici.

## Riproducibilità e file

La cartella contiene il pilota esportato con i soli fixture aggiuntivi, oracle, runner, fonti pubbliche e risultati. Le dipendenze del controllo locale sono `yaml=2.9.1` e `ajv=8.20.0`; Node della sessione è v24.17.0. Installazione e controlli locali sono stati eseguiti direttamente dall'agente usando una cache nell'area di lavoro, senza modificare dipendenze del repository originale.

Per riprodurre in un ambiente autorizzato, nella cartella estratta: installare le dipendenze con `npm ci --ignore-scripts`, usare `npm run generate`, `node check-fixtures.mjs`, `npm run replay`. Il replay restituisce volutamente exit code 1 finché le 12 discrepanze restano aperte. Il comando nativo sopra è documentato come tentativo bloccato, non come operazione completata né come richiesta di deploy. Nessuna modifica al codice del pilota è inclusa per mascherare gli esiti.
