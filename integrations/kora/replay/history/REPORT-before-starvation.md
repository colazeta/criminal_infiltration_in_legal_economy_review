# Kora replay — correzioni, 19 settembre 2026

**29/29 replay mirati; 94/96 nella suite completa.** Restano rossi i due casi di starvation. Gli 80 attesi originali sono invariati; sono stati aggiunti 16 casi per la decisione del proprietario sulle eccezioni SCOUT/PERSIST. La release **rel_4wbyk58gsiuzfh8f non contiene queste correzioni**. Nessuna release nuova, deploy, esecuzione live o modifica ai dati della review.

## Regole contrattuali esatte

Documenti riletti dal `main` corrente `8288d5ea0fe8a01603e05d67a6ee88e41a532ff4`: i tre blob operativi coincidono con le copie archiviate. PR iniziale: `1a62fd94149063999289c35220e2bfeade4600f6`.

- **R1**, [hourly-hybrid-v4.md:37](https://github.com/colazeta/criminal_infiltration_in_legal_economy_review/blob/8288d5ea0fe8a01603e05d67a6ee88e41a532ff4/docs/operations/hourly-hybrid-v4.md#L37): “if the oldest pending CILE-IDENTITY-RESOLUTION-2 observation is at least 24 hours old, or the pending queue reaches 20 observations, the next non-scout activation with no unfinished safe write must choose `RESOLVE` before opening new enrichment research.” V5 conserva questa starvation guard; la clausola non equipara esplicitamente ogni `identity_debt_due=true` alla soglia obbligatoria.
- **R2**, [completion-first-v5.md:75](https://github.com/colazeta/criminal_infiltration_in_legal_economy_review/blob/8288d5ea0fe8a01603e05d67a6ee88e41a532ff4/docs/operations/completion-first-v5.md#L75): “Keep at most **6 ordinary assessment-completion papers project-wide** in active end-to-end WIP at once.” Il [contratto pilota originario:32](https://github.com/colazeta/criminal_infiltration_in_legal_economy_review/blob/1a62fd94149063999289c35220e2bfeade4600f6/integrations/kora/control-plane/docs/integration-contract.md#L32) promette “ordinary assessment WIP above six → `BLOCKED`”.
- **R3**, stesso contratto pilota:33: “inconsistent F0–F7 predicates → `BLOCKED`”.
- **R4**, [completion-first-v5.md:83](https://github.com/colazeta/criminal_infiltration_in_legal_economy_review/blob/8288d5ea0fe8a01603e05d67a6ee88e41a532ff4/docs/operations/completion-first-v5.md#L83): “A due owned scouting window still selects `SCOUT`. Outside scouting, resume unfinished safe writes first.” Da qui il conflitto precedente con la promessa incondizionata R2/R3.
- **R5**, [completion-first-v5.md:54–55](https://github.com/colazeta/criminal_infiltration_in_legal_economy_review/blob/8288d5ea0fe8a01603e05d67a6ee88e41a532ff4/docs/operations/completion-first-v5.md#L54): F6 richiede “all machine-verifiable prerequisites”; F7 è “the current assessment has the required accepted calibration/adjudication/human exact-head approval and remains current.” La riga 24 richiede che “current candidate/proposal/source/reference hashes and version guards still match.”
- **R6**, decisione del proprietario in questa sessione: “Consentire SCOUT/PERSIST se indipendenti dal frontier incoerente o dal WIP”. Attuazione conservativa: attestazione esplicita per la rotta selezionata; assenza/false non autorizzano l'eccezione. Nessun permesso di scrittura o rete implicato.

## Classificazione individuale delle 12 discrepanze

“Prima” è il risultato originale, “ora” usa lo stesso atteso sul codice aggiornato. Le otto ambiguità di precedenza sono state risolte tramite R6, non riscrivendo gli attesi.

| Caso | Regola | Atteso | Prima | Classificazione | Ora |
|---|---|---|---|---|---|
| A-starvation-over-complete | R1 | RESOLVE | COMPLETE | Fixture sottospecificata; decisione aperta | COMPLETE, aperto |
| B-starvation-over-complete | R1 | RESOLVE | COMPLETE | Fixture sottospecificata; decisione aperta | COMPLETE, aperto |
| A-scout-wip-collision | R2/R4 → R6 | BLOCKED | SCOUT | Ambiguità risolta dal proprietario | BLOCKED, pass |
| B-scout-wip-collision | R2/R4 → R6 | BLOCKED | SCOUT | Ambiguità risolta dal proprietario | BLOCKED, pass |
| A-persist-wip-collision | R2/R4 → R6 | BLOCKED | PERSIST | Ambiguità risolta dal proprietario | BLOCKED, pass |
| B-persist-wip-collision | R2/R4 → R6 | BLOCKED | PERSIST | Ambiguità risolta dal proprietario | BLOCKED, pass |
| A-inconsistent-scout | R3/R4 → R6 | BLOCKED | SCOUT | Ambiguità risolta dal proprietario | BLOCKED, pass |
| B-inconsistent-scout | R3/R4 → R6 | BLOCKED | SCOUT | Ambiguità risolta dal proprietario | BLOCKED, pass |
| A-inconsistent-persist | R3/R4 → R6 | BLOCKED | PERSIST | Ambiguità risolta dal proprietario | BLOCKED, pass |
| B-inconsistent-persist | R3/R4 → R6 | BLOCKED | PERSIST | Ambiguità risolta dal proprietario | BLOCKED, pass |
| validated-without-ready | R5 | validation_accepted=false | true | Difetto dimostrabile | false, pass |
| validated-stale-versions | R5 | validation_accepted=false | true | Difetto dimostrabile | false, pass |

I due casi R1 sono errori di sufficienza dell'oracle/fixture: lo schema non porta età, numerosità della coda o distinzione tra nuova ricerca e gate già avviato. Non è dimostrato che RESOLVE sia sbagliato, ma il solo input non lo impone. Restano invariati e aperti, senza skip, warning o gate disabilitati. Serve decidere se `identity_debt_due` significhi sempre starvation obbligatoria o se occorra un segnale distinto. Nessuna modifica a quella precedenza è stata applicata.

L'attribuzione dei safeguards alla sezione “Side-effect boundary” nel materiale precedente era imprecisa: sono in **Routing contract**. Questa correzione del riferimento non altera gli attesi.

## Modifiche e prove

- `frontier-core.mjs`: accettazione derivata solo con `validated`, `validation_ready`, assessment completo e assenza di incoerenza. Non inventa ricevute scientifiche.
- `router-core.mjs`: rileva il blocco prima delle rotte prioritarie. Eccezione solo per la rotta con attestazione esattamente `true`.
- Processo: aggiunti i campi **opzionali** `scout_independent_of_frontier_and_wip` e `persist_independent_of_frontier_and_wip` all'input e allo stato intermedio. Non sono permessi di scrittura.
- Contratto del pilota aggiornato con R6, limite della starvation e differenza della release. Il manifest della PR resta **deny**, invariato.

L'indipendenza deve essere attestata da un preflight autorizzato: il pilota non la verifica accedendo a servizi privati. Se entrambe le rotte sono dovute, resta la priorità SCOUT; se la sua eccezione manca, non si presume automaticamente una rotta alternativa sicura.

| Controllo | Esito |
|---|---|
| Replay mirati | **29/29** |
| Suite completa | **94/96**, exit code 1 per i due R1 |
| Casi complessivi | 68 catene frontier→router, 21 frontier, 7 input respinti da schema |
| Fixture nativi controllati offline | **92/92**: 3 originali +89 nuovi; schema Test, input nodo, timestamp stringa YAML 1.1 |
| Attesi originali | Tutti gli 80 invariati |
| Output dei router | Sempre side_effect_authorized=false e pilot_mode=observe_only |

I 16 casi nuovi coprono le due lane, SCOUT/PERSIST, WIP, incoerenza, entrambi i blocchi, flag false e flag riferito alla rotta sbagliata. L'oracle resta separato dalla funzione testata: `prepare.mjs` non importa le funzioni del pilota. Il runner compone i veri due core; non esegue motore Kora/gateway/wrapper SDK.

[Risultati completi](local-results.json), [mirati](targeted-results.json), [fixture](fixture-validation.json), [casi](cases.json). [Rapporto originario](history/REPORT-before-fix.md) e [risultati prima delle correzioni](history/local-results-before-fix.json) sono conservati. `pilot/` rappresenta ora il sorgente proposto, **non** la release congelata.

## Origine del manifest allow: confine verificato

| Fonte | Configurazione |
|---|---|
| Locale e PR, prima/dopo | name=cile-review-control-plane; defaultAction=deny |
| Export acquisito di rel_4wbyk58gsiuzfh8f | name=oltre; defaultAction=allow; inheritManaged=true; limiti 5 USD / 900000 ms /24 turns |

[Manifest della release](evidence/release-kora.yaml), [confronto originario](history/source-comparison-before-fix.json). La CLI installata è **0.13.0**. L'ispezione del codice e un probe offline dimostrano:

1. `files.js:66–71,260–282`: import del manifest locale con deny, senza riscrittura.
2. `release-commands.js:120–140`: creazione da cartella trasmette i file. È il comportamento della CLI installata, non una cattura retroattiva della richiesta storica.
3. `api-client.js:568–573`: lettura del contenuto dall'endpoint release `/source`.
4. `release-commands.js:80–104`, `files.js:160–176`: export di `file.content` senza sintetizzare un manifest. Il probe offline conserva allow esattamente.

**Dimostrato:** allow era già nel contenuto restituito dal server per la sorgente della release; non lo aggiunge il writer CLI o il replay. È la configurazione nell'export della release. **Non determinato:** normalizzazione alla creazione oppure ricostruzione all'export; corrispondenza con il record/IR di esecuzione compilato. Mancano accesso corrente al record release e codice server. L'origine da un default dell'organizzazione resta un'ipotesi. Non è corretto certificare la policy runtime solo dal manifest esportato.

Nessun permesso ampliato, nessuna sostituzione silenziosa di allow nella release. [cli-diagnosis.json](evidence/cli-diagnosis.json) registra test offline e hash dei moduli, senza credenziali.

## Diagnosi lock e test nativi

L'utente di esecuzione è quello sandbox. L'ACL della directory della sessione concede al gruppo sandbox **ReadAndExecute**, non creazione/scrittura. Il lock risulta **assente** al controllo: nessun lock attivo o stantio identificato da rimuovere.

La CLI (`transport.js:388–389`) rinnova entro 60 secondi dalla scadenza o dopo 401. `session-store.js:61–80` acquisisce il lock tramite `open(...,"wx",0600)`; EPERM viene propagato, mentre solo EEXIST attiva l'attesa/stale-lock logic. La nuova prova `kora auth whoami --json` fallisce proprio con **EPERM**, prima del rinnovo coordinato. Ciò non prova un token invalido.

Non sono stati letti/esposti/iniettati token, copiate sessioni, cancellati lock, cambiati ACL/safe.directory o elevati comandi. La lettura della scheda browser Kora è stata rifiutata dalla policy perché l'accesso al dominio risulta negato; nessun browser/API alternativo è stato usato per aggirare il rifiuto.

**Esecuzioni native del codice aggiornato: 0.** Non è stata ripetuta inutilmente la suite già bloccata. Restano non verificati: runtime SDK, nodi nel sandbox Kora, gatePassed dei nuovi test, motore/gateway end-to-end, record/IR della policy rete. Serve un ambiente autorizzato a gestire la propria sessione e leggere la release; i replay locali non sostituiscono queste verifiche.

La precedente sessione aveva verificato releaseReady=true, diagnostics=[] e deployments=[] in production. Questi risultati riguardano soltanto la release immutabile originaria e non sono ripetuti né estesi al codice corretto. Nessuna nuova release, deploy o run live eseguito.

## Controlli repository aggiuntivi

I 22 comandi di AGENTS.md sono stati eseguiti su una **copia isolata** del checkout: 20 passano, 2 gruppi restano non verdi. Con Python UTF-8 e TEMP/TMP locali: **757 test Python, 1 failure e 4 errori; 336 test Node, 330 pass e 6 fail**. Anche ripristinando nella copia il pilota originario ricompaiono gli stessi due gruppi falliti; non si presenta questa situazione come CI verde o regressione dimostrata del fix.

I problemi comprendono confronti byte-identici CRLF/LF e contesto Git/esecuzione locale. Nessun dato immutabile o test estraneo è stato alterato per nasconderli. Validatori repository/ontologia/archive/site, generatori e dieci controlli sintattici risultano passati nell'esecuzione finale. Esiti separati in [repository-checks.json](repository-checks.json) e [baseline](repository-baseline-checks.json); log completi mantenuti nell'area di lavoro.

## Evidenze reali e riproducibilità

Restano **2 ricostruzioni storiche pubbliche parziali, 0 replay reali completi**. Ciascuna manca di 17 campi obbligatori; nessun riempimento inventato. [Ricostruzioni](evidence/reconstructed-cases.json) e [campi mancanti](evidence/completeness-audit.json). Nessun caso sintetico conta come progresso scientifico o calibrazione.

Record review modificati: **0**; nessun endpoint privato della review. Il checkout originale resta preservato. Gli unici aggiornamenti remoti autorizzati sono della PR #779, senza merge/force push. Le ambiguità residue restano aperte; nessuna readiness nuova dichiarata.

Per riprodurre il pacchetto: `npm ci --ignore-scripts`, `npm run generate`, `node check-fixtures.mjs`, `node replay.mjs --targeted`, `npm run replay`. Dipendenze fissate dal lockfile. L'ultimo comando restituisce intenzionalmente exit code 1 finché i due R1 non sono risolti. Nessuno di questi comandi avvia workflow live.

## Focus successivo sui due casi residui

Vedere [STARVATION.md](STARVATION.md) per input, esiti rieseguiti, proposta minima ancora non implementata e checkout manuale vincolato a ee553480. Policy di rete ancora aperta; nessuna verifica nativa aggiunta.

