# Kora replay — guardia starvation basata su evidenze

Implementata la decisione del proprietario del 19 settembre 2026: RESOLVE precede COMPLETE soltanto se l'attivita' proposta aprirebbe nuova ricerca e la soglia contrattuale e' dimostrata. Non interrompe lavoro gia' in corso. F3 non implica nuova ricerca. Nessuna modifica alle precedenze SCOUT/PERSIST, ai blocchi applicabili, al writer o al controllo anti-repeat.

## Risultati di questa sessione

| Verifica | Risultato | Limite |
|---|---|---|
| Suite locale completa | 164 casi: 162 asserzioni determinate passate; 2 divergenze storiche sottospecificate | exit 1 conservato, non suite interamente verde |
| Matrice starvation nelle due lane | 62/62 nuovi casi di routing passati, oltre a 2 storici divergenti | sintetici |
| Nuovi controlli schema | 6/6 rifiuti corretti | inclusi nei 162 |
| Precedenze/frontier mirati | 35/35 | locali |
| Schema fixture native | 154/154 | non esecuzione Kora |
| Funzioni pure sugli input YAML nativi | 152/154; 2 divergenze storiche | non SDK/sandbox Kora; exit 1 |
| Confronto col vecchio router | 32/62 nuove asserzioni di rotta fallivano prima | attesi scritti senza importare il SUT |
| Repository, comandi AGENTS.md | 20/22 comandi passati | stessi gruppi Python/Node gia' falliti nella baseline |
| Test nativi aggiornati | 0 eseguiti qui | script manuale da fissare al nuovo commit, non ee553480 |

Python: 757 test, 1 failure e 4 errori. Node: 336 test, 330 passati e 6 falliti. Verifiche su copia isolata del repository con il pilota aggiornato, non un checkout completo del nuovo commit. Problemi locali di byte/line-ending e contesto Git gia' documentati dalla baseline precedente; nessuna dichiarazione di CI verde.

## Evidenze, calcolo e dati mancanti

Il nuovo identity-preflight.mjs riceve identity_preflight_evidence: pending_observation_count, oldest_pending_age_seconds, activity_kind ed evidence_ref. Produce required / not_required / undetermined e una motivazione. Nessun flag di risultato e' accettato come input. Nessun servizio viene interrogato.

Per nuova ricerca: eta' >=86400 secondi oppure coda >=20 => required; basta una soglia dimostrata. Per escluderle servono entrambe sotto soglia oppure una coda esplicitamente vuota. Un'eta' associata a coda vuota e' contraddittoria. Natura mancante/sconosciuta, riferimento mancante o prove insufficienti => undetermined. Prima di COMPLETE, required porta a RESOLVE e undetermined a BLOCKED. Lavoro attestato in_progress/non_research => not_required anche senza metriche di coda, che non sono necessarie per quell'attivita'. Il nome del gate non viene usato nella classificazione.

evidence_ref e' un riferimento opaco fornito dall'osservatore: il pilota ne richiede la presenza ma non verifica il contenuto o la freschezza di registri privati. Un eventuale adattatore futuro deve raccogliere e attestare misure coerenti dello stesso preflight e natura dell'attivita'; non e' stato collegato a servizi privati in questo lavoro. Tutti gli output restano observe_only, side_effect_authorized=false.

Test: 24h esatte, 86399 secondi e 86399.999 secondi; 20 osservazioni e 19; entrambe sopra soglia; ongoing/non-research sullo stesso F2->F3; campi assenti/null; natura unknown; prova sufficiente di una sola soglia; coda vuota e contraddizioni; priorita' e blocchi; tipi invalidi e tentativo di fornire il risultato del preflight.

## Conservazione e classificazione dei casi

Tutti i 96 attesi precedenti restano identici. I due input storici starvation restano identici. Gli scenari sintetici preesistenti che attendevano COMPLETE sono stati arricchiti esplicitamente con coda=1, eta'=3600 secondi e attivita'=new_research; sono scelte dichiarate di fixture, non dati reali e non inferenze da F3. Lo stesso chiarimento riguarda la fixture nativa originale router-complete. I confronti sono riproducibili con compare-starvation-baseline.mjs.

I due storici continuano ad attendere RESOLVE: prima ottenevano COMPLETE, ora BLOCKED/undetermined. Non sono contati come difetti dimostrati del nuovo codice. Rimangono nel runner e nelle fixture native con gate attivo: non sono saltati, rimossi o convertiti a pass. Per questo la suite completa mantiene exit 1. Le 32 regressioni dimostrate sono invece basate su nuovi input espliciti e risolte. La policy non e' piu' ambigua; gli input storici restano insufficienti.

Zero replay completi ricostruiti da dati reali. Restano soltanto due checkpoint pubblici parziali, con 17 campi obbligatori mancanti ciascuno e senza nuove prove di coda/attivita'. Nessun dato mancante inventato.

## Release, rete e test nativi

La release esistente rel_4wbyk58gsiuzfh8f non incorpora queste correzioni. La precedente validazione releaseReady=true/diagnostics=[] e la precedente lista production deployments=[] non sono state rieseguite ora e non validano il nuovo codice. I precedenti 3/3 nativi riguardavano la vecchia sorgente.

La discrepanza rete resta APERTA: manifest PR/locale deny; export precedentemente acquisito della release allow + inheritManaged=true. L'analisi offline precedente prova che allow era gia' nella risposta server, non che fosse inserito dalla CLI. Origine server (creazione o ricostruzione export) e policy runtime/IR effettiva restano non verificate. Nessuna variazione al manifest o ampliamento permessi.

Il blocco precedente EPERM sulla creazione del refresh lock di sessione e il diniego browser non sono stati aggirati; nessuna cancellazione lock, copia sessione, iniezione credenziali o percorso alternativo. Non si ripetono tentativi equivalenti. Lo script PowerShell manuale consegnato separatamente verifica SHA completo nuovo, directory separata e stato Git pulito; esegue soltanto kora test suite --workspace ... --environment production --org oltre --json. La suite include i due casi storici: non promettiamo gatePassed=true.

## Riproduzione

npm ci --ignore-scripts; npm run generate; node compare-starvation-baseline.mjs; node check-fixtures.mjs; node replay.mjs --starvation; node replay.mjs --targeted; npm run replay; node check-native-offline.mjs. I tre comandi che includono i due storici restituiscono exit 1, non mascherato. Non e' un motivo per ampliare permessi o creare release.

File principali: scripts/identity-preflight.mjs, scripts/router-core.mjs, schema del processo, contratto, fixture native; replay/starvation-cases.mjs contiene l'oracle separato dal SUT. Risultati in local-results.json, starvation-results.json, starvation-baseline.json e native-offline-results.json.

Nessuna modifica a dati della review, decisioni scientifiche o registri (0 record); nessun cambiamento ontologico. Solo letture del repository pubblico e test locali. Nessuna nuova release, merge, deploy, scheduler o esecuzione live.

## Regole contrattuali esatte

Documenti riletti nella sessione precedente dal `main` allora corrente `8288d5ea0fe8a01603e05d67a6ee88e41a532ff4`: i tre blob operativi coincidono con le copie archiviate. PR iniziale: `1a62fd94149063999289c35220e2bfeade4600f6`.

- **R1**, [hourly-hybrid-v4.md:37](https://github.com/colazeta/criminal_infiltration_in_legal_economy_review/blob/8288d5ea0fe8a01603e05d67a6ee88e41a532ff4/docs/operations/hourly-hybrid-v4.md#L37): “if the oldest pending CILE-IDENTITY-RESOLUTION-2 observation is at least 24 hours old, or the pending queue reaches 20 observations, the next non-scout activation with no unfinished safe write must choose `RESOLVE` before opening new enrichment research.” V5 conserva questa starvation guard; la clausola non equipara esplicitamente ogni `identity_debt_due=true` alla soglia obbligatoria.
- **R2**, [completion-first-v5.md:75](https://github.com/colazeta/criminal_infiltration_in_legal_economy_review/blob/8288d5ea0fe8a01603e05d67a6ee88e41a532ff4/docs/operations/completion-first-v5.md#L75): “Keep at most **6 ordinary assessment-completion papers project-wide** in active end-to-end WIP at once.” Il [contratto pilota originario:32](https://github.com/colazeta/criminal_infiltration_in_legal_economy_review/blob/1a62fd94149063999289c35220e2bfeade4600f6/integrations/kora/control-plane/docs/integration-contract.md#L32) promette “ordinary assessment WIP above six → `BLOCKED`”.
- **R3**, stesso contratto pilota:33: “inconsistent F0–F7 predicates → `BLOCKED`”.
- **R4**, [completion-first-v5.md:83](https://github.com/colazeta/criminal_infiltration_in_legal_economy_review/blob/8288d5ea0fe8a01603e05d67a6ee88e41a532ff4/docs/operations/completion-first-v5.md#L83): “A due owned scouting window still selects `SCOUT`. Outside scouting, resume unfinished safe writes first.” Da qui il conflitto precedente con la promessa incondizionata R2/R3.
- **R5**, [completion-first-v5.md:54–55](https://github.com/colazeta/criminal_infiltration_in_legal_economy_review/blob/8288d5ea0fe8a01603e05d67a6ee88e41a532ff4/docs/operations/completion-first-v5.md#L54): F6 richiede “all machine-verifiable prerequisites”; F7 è “the current assessment has the required accepted calibration/adjudication/human exact-head approval and remains current.” La riga 24 richiede che “current candidate/proposal/source/reference hashes and version guards still match.”
- **R6**, decisione del proprietario in questa sessione: “Consentire SCOUT/PERSIST se indipendenti dal frontier incoerente o dal WIP”. Attuazione conservativa: attestazione esplicita per la rotta selezionata; assenza/false non autorizzano l'eccezione. Nessun permesso di scrittura o rete implicato.


## Le 12 discrepanze originarie, aggiornate

| Caso | Regola | Atteso | Prima | Classificazione | Ora |
|---|---|---|---|---|---|
| A-starvation-over-complete | R1 | RESOLVE | COMPLETE | Fixture storica sottospecificata; policy ora decisa | BLOCKED, divergenza conservata |
| B-starvation-over-complete | R1 | RESOLVE | COMPLETE | Fixture storica sottospecificata; policy ora decisa | BLOCKED, divergenza conservata |
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


Cronologia completa conservata in history/REPORT-before-starvation.md e history/STARVATION-policy-proposal.md.
