# Focus starvation — 19 settembre 2026

Rieseguita la suite locale: 94/96; i soli due fallimenti sono A-starvation-over-complete e B-starvation-over-complete. Nessuna modifica al router o agli attesi. Input integrali in starvation-inputs.json; risultati in local-results.json. Entrambi i casi sono sintetici, non ricostruzioni di code reali.

| Caso | Input distintivo | Atteso | Ottenuto |
|---|---|---|---|
| A-starvation-over-complete | lane A; synthetic-A-starvation-over-complete; 2026-09-19T09:10:00+02:00 | RESOLVE | COMPLETE |
| B-starvation-over-complete | lane B; synthetic-B-starvation-over-complete; 2026-09-19T21:40:00+02:00 | RESOLVE | COMPLETE |

In entrambi: scouting_due=false; unfinished_safe_write=false; active_wip_count=3; candidate_present=true; writer_ready=true; identity_debt_due=true; repeat_without_changed_prerequisite=false. Frontier calcolato F2_PROPOSAL_PERSISTED, coerente, prossimo F3_INDEPENDENT_COMPARISON. Actual reason=deepest_owned_paper_has_executable_f0_f5_gate, priority=2. Atteso e ottenuto condividono side_effect_authorized=false e pilot_mode=observe_only.

## Regola esatta e limite dell'input

Fonte salvata: evidence/docs__operations__hourly-hybrid-v4.md, riga 37:

> Paper-stage progress remains the primary KPI, so executable `ENRICH` normally precedes `RESOLVE`. Identity debt may not starve: if the oldest pending CILE-IDENTITY-RESOLUTION-2 observation is at least 24 hours old, or the pending queue reaches 20 observations, the next non-scout activation with no unfinished safe write must choose `RESOLVE` before opening new enrichment research.

completion-first-v5.md conserva la guardia (righe 3, 90, 132), pur dando normalmente precedenza a COMPLETE. La citazione R1 del rapporto precedente puntava erroneamente a riga 42; la clausola si trova a riga 37.

Per ciascuno dei due casi, RESOLVE e' l'atteso indipendente sotto l'assunzione scritta nella fixture che identity_debt_due denoti la guardia obbligatoria. Il payload non dimostra questa assunzione: mancano soglia raggiunta e apertura di nuova ricerca. Non e' quindi ancora un difetto incondizionato dimostrato dal solo input. Il router non rappresenta comunque l'eccezione obbligatoria prima di COMPLETE.

## Modifica minima proposta, non implementata

Aggiungere un segnale distinto, ad esempio identity_starvation_preempts_new_research, ai due schemi di input. Il suo significato deve essere: debito pendente con eta' >=24h oppure coda >=20, e lavoro concorrente che aprirebbe nuova ricerca. Dopo SCOUT/PERSIST e i blocchi, prima di COMPLETE, selezionare RESOLVE se il segnale e' vero. Conservare identity_debt_due per il debito ordinario. Il segnale deve essere attestato dal preflight, non dedotto dal risultato del router; dati mancanti non equivalgono a prova di soglia non raggiunta.

Esempi ipotetici: una osservazione pendente da 2h e confronto F3 da iniziare => COMPLETE. Una osservazione pendente da 25h e confronto F3 da iniziare => RESOLVE. Un confronto gia' in corso, senza nuova ricerca, non sarebbe prevaricato da questa eccezione; un safe write incompleto conserva PERSIST.

Scelta da confermare: limitare l'eccezione alla nuova ricerca, come recita la clausola, oppure estenderla anche al lavoro gia' in corso (quest'ultima sarebbe una modifica della policy). Spostare semplicemente identity_debt_due prima di COMPLETE farebbe invece prevaricare anche il debito di sole 2h: non proposto.

I due casi originali e gli attesi RESOLVE restano invariati e aperti. Dopo la decisione si possono aggiungere fixture esplicite con il nuovo segnale e soglie documentate, mantenendo gli originali come evidenza della sottospecificazione, senza sostituire gli attesi con COMPLETE.

## Checkout e test nativi

Verificato leggendo .git/HEAD: C:\Users\nicol\cile-kora e' ancora detached a dd212442dec3f02278f24c8c004f51d04f725f9a. La cartella outputs/kora-replay/pilot contiene artefatti aggiornati, non e' un checkout Git verificato. work/cile-kora-ee553480 non esiste al momento della preparazione.

Lo script ../run-kora-native-ee553480.ps1 crea un checkout separato, verifica SHA completo ee5534802e83b0eabc5cefbd058a7499612fa5fc e assenza di modifiche, poi esegue kora test suite sul relativo integrations/kora/control-plane. Se la cartella esiste ma non corrisponde, si ferma senza reset. Sintassi del comando verificata con kora help test suite --json: esegue test sorgente senza avviare un run. Script preparato per esecuzione manuale, non eseguito qui. I replay locali non dimostrano il risultato nativo.

## Policy di rete ancora aperta

Manifest locale/PR: defaultAction=deny. Export salvato della release rel_4wbyk58gsiuzfh8f: defaultAction=allow, inheritManaged=true. L'analisi offline della CLI indica che allow e' gia' nella risposta sorgente del server; non prova se derivi dalla creazione o dalla ricostruzione dell'export, ne' quale policy sia nel runtime/IR. Il diniego di accesso browser resta rispettato. Nessun ampliamento permessi o aggiramento del lock. Nessuna nuova verifica live della release in questa sessione; la release non incorpora ee553480.

Nessuna nuova release, merge, deploy o esecuzione live.
