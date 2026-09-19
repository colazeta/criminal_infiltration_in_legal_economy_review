# Kora replay — suite corrente e archivio storico separati

Decisione esplicita del proprietario: conservare integralmente i due casi originali e gli attesi RESOLVE nell'archivio, e creare versioni correnti conformi al contratto dei dati insufficienti. Nessuna modifica al router, al preflight, al manifest o alla logica degli exit code in questa revisione.

## Risultati verificati ora

| Controllo | Esito |
|---|---|
| Suite locale corrente | 164/164, exit 0 |
| Starvation, due lane | 64/64: 62 casi espliciti gia' presenti + 2 versioni correnti |
| Precedenze/frontier mirati | 35/35 |
| Validazione fixture YAML native | 154/154, offline |
| Funzioni pure sui medesimi input/check YAML | 154/154, offline, exit 0 |
| Conservazione originali e identita' input | 2/2 verificati |
| Confronto regressioni con vecchio router | 32/62 errori dimostrati sulla matrice esplicita, corretti nella sessione precedente |
| Test nativi Kora | 0 eseguiti qui; runtime/SDK/gatePassed non verificati |

164 e' il numero di casi correnti, non comprende i due record originali archiviati. Comprende 130 pipeline, 21 frontier, 13 rifiuti schema. Le fixture native sono 151 casi eseguibili piu' le 3 fixture originarie: 154. I 13 rifiuti schema locali non sono 13 ulteriori esecuzioni native.

I runner mantengono la stessa regola process.exitCode = report.failed ? 1 : 0. Nessun fallimento e' convertito globalmente in successo, nessun gate disabilitato. L'exit 0 corrente deriva dall'esito delle asserzioni contrattuali revisionate esplicitamente dal proprietario.

## I due casi, senza riscrivere la storia

| Archivio, atteso invariato | Versione corrente | Atteso corrente |
|---|---|---|
| A-starvation-over-complete: RESOLVE | A-starvation-insufficient-evidence | BLOCKED; identity_starvation_status=undetermined |
| B-starvation-over-complete: RESOLVE | B-starvation-insufficient-evidence | BLOCKED; identity_starvation_status=undetermined |

Le versioni correnti conservano gli input completi identici, incluso activation_id. Esplicitano inoltre reason=new_research_safety_not_established e identity_starvation_reason=missing_preflight_evidence. historical_case_id collega ogni nuova versione all'originale. L'assenza di evidenze non dimostra che una soglia sia raggiunta e non puo' autorizzare nuova ricerca: da questo contratto deriva l'atteso BLOCKED, non dal risultato del SUT.

Originali completi: history/starvation-original-cases.json e history/cases-before-starvation.json. Fixture YAML originali, inclusi tutti i gate e l'atteso RESOLVE: history/native-original/replay-A-starvation-over-complete.yaml e corrispondente B. Risultati precedenti: history/local-results-before-starvation.json e history/local-results-at-182ce657.json. Quest'ultimo conserva i due esiti BLOCKED contro attesi RESOLVE e la suite non verde. Relazione precedente in history/REPORT-at-182ce657.md. Questi file sono evidenza storica, non test correnti saltati a runtime.

Il generatore crea le due nuove fixture e ritira soltanto le vecchie copie nel tests/ attivo dopo aver verificato identita' byte-per-byte con l'archivio. La verifica check-history-preservation.mjs confronta integralmente gli oggetti originali e gli input correnti. I 94 altri attesi della baseline da 96 restano invariati. I test espliciti RESOLVE a 24h esatte o 20 osservazioni restano attivi e invariati in entrambe le lane, cosi' come quelli immediatamente inferiori e sul lavoro gia' in corso.

## Quale suite seleziona lo script nativo

Verificato offline con la CLI installata 0.13.0, richiamando la sua vera funzione readWorkspaceTestEntries. Il comando test suite passa i file del --workspace indicato; --name sarebbe un filtro, ma lo script non lo usa. Non usa --release.

Bundle locale ispezionato: outputs/kora-replay/pilot. Contiene 167 file impacchettati, di cui tutte le 154 fixture Test YAML in pilot/tests. Non invia la cartella sorella replay/history. Inventario completo e hash in native-suite-selection.json; codice riproducibile in inspect-native-selection.mjs.

Sul checkout fissato al nuovo commit, il percorso selezionato e':

    <checkout>/integrations/kora/control-plane/tests/

Quindi il comando seleziona **solo i test presenti nel bundle indicato, che nel nuovo commit sono proprio tutte le 154 fixture correnti**. Non seleziona le sole 3 fixture della release vecchia, ne' i 164 casi JSON locali, ne' l'archivio storico. Il conteggio di esecuzioni effettivamente svolte dal server resta non verificato finche' non si esegue manualmente il comando e si legge il risultato nativo.

run-native.ps1 accetta obbligatoriamente lo SHA completo, usa un checkout separato, verifica HEAD e stato pulito e poi esegue l'ispettore sul bundle effettivo prima dell'autenticazione. Se non trova esattamente 154 fixture, i due casi correnti e i quattro test delle soglie esatte, si ferma. Lo script consegnato negli outputs fissa il parametro al nuovo commit; gli script precedenti restano riferiti a versioni precedenti.

Comando finale interno: kora test suite --workspace <checkout>/integrations/kora/control-plane --environment production --org oltre --json. Non avvia un workflow live e non crea una release. Script preparato e analizzato sintatticamente, non eseguito qui. Nessun tentativo di aggirare il precedente EPERM sul refresh lock o il diniego browser.

## Fallimenti generali separati, non nuovi risultati verdi

La precedente sessione ha eseguito i 22 comandi AGENTS.md sulla copia isolata: 20 passati; Python 757 test con 1 failure e 4 errori; Node 336 test con 330 passati e 6 falliti. Gli stessi gruppi erano gia' riprodotti nella baseline, con problemi locali di byte/line-ending e contesto Git. Non sono stati cancellati ne' riclassificati come successi. Non sono stati rieseguiti in questa revisione di fixture/documentazione, che non modifica codice di produzione. Le evidenze rimangono repository-checks.json e repository-baseline-checks.json; non costituiscono un risultato CI sul nuovo commit.

## Policy di rete ancora aperta e release distinta

Manifest locale/PR: deny, invariato. Export della release rel_4wbyk58gsiuzfh8f acquisito in precedenza: allow + inheritManaged=true. La precedente analisi offline indica allow gia' nella risposta server; restano non verificate l'origine sul server e la policy effettiva runtime/IR. Nessun ampliamento permessi, nuova ispezione browser o percorso alternativo al diniego.

La release non incorpora le correzioni. I precedenti 3/3 nativi, releaseReady=true/diagnostics=[] e production deployments=[] sono evidenze storiche, non verifiche della nuova sorgente e non sono stati ripetuti ora.

## Riproduzione e limiti

npm ci --ignore-scripts prepara le dipendenze (gia' disponibili, non reinstallate in questa sessione). Eseguire poi npm run generate; node check-history-preservation.mjs; node compare-starvation-baseline.mjs; node check-fixtures.mjs; node replay.mjs --starvation; node replay.mjs --targeted; npm run replay; node check-native-offline.mjs. Questi generatori e controlli locali sono stati eseguiti e sono passati nella sessione corrente.

La regola sostanziale resta quella di hourly-hybrid-v4.md:37, conservata da v5 e precisata dal proprietario: soglia eta' >=86400 secondi OR coda >=20, prima di aprire nuova ricerca; non prevarica attivita' gia' in corso. L'identificazione di F3 non prova nuova ricerca. Il preflight calcola required/not_required/undetermined dalle osservazioni fornite, senza raccogliere dati privati o verificare le fonti referenziate. Dati necessari mancanti restano undetermined. Le precedenze SCOUT/PERSIST, blocchi applicabili, writer e anti-repeat sono invariate.

Tutti i casi correnti sono sintetici. Zero replay reali completi: i due checkpoint pubblici parziali mantengono 17 input obbligatori mancanti ciascuno; nessuna misura di coda o dato mancante inventato. Pilota observe_only, side_effect_authorized=false. Nessun record della review, decisione scientifica, registro o dato privato modificato. Nessuna nuova release, merge, deploy, scheduler o esecuzione live.
