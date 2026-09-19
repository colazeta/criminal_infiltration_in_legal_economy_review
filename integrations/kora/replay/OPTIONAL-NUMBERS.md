# Contratto Kora: numeri opzionali, non nullable

## Evidenza e scelta della rappresentazione

Il proprietario riferisce sul commit d7f84cc8ba9539b8e39b48e36a605c0beddb36ee: UNSUPPORTED_CONSTRUCT, `Process type 'ActivationInput' uses unsupported schema keyword 'nullable' on 'integer' schemas.`, __setup__, testCount=0. Nessuna delle 154 fixture e' stata eseguita. La precedente prova 63106891 aveva gia' respinto i type array. Entrambe le diagnostiche sono conservate come user-reported, non come risultati ottenuti dall'assistente.

Non si propone un'altra unione. La CLI 0.13.0, `kora schema get process --json`, documenta type scalari integer/number e oggetti con properties e required. Il bundle usa gia' questi costrutti per active_wip_count e campi facoltativi come assessment_distance_to_f5/inconsistency_code. La rappresentazione scelta usa solo quel vocabolario, senza nuovi keyword: due proprieta' numeriche NON elencate in required. Non e' una deduzione del supporto Kora dall'accettazione di AJV. La prova nativa minima deve comunque verificarne il funzionamento sul server attuale.

In entrambi ActivationInput e ActivationWithFrontier:

```yaml
pending_observation_count: {type: integer, minimum: 0}
oldest_pending_age_seconds: {type: number, minimum: 0}
```

Sono state rimosse esattamente le quattro occorrenze di nullable. Il confronto dell'intero documento con history/process-schema-d7f84cc8.yaml prova che non ci sono altre modifiche di schema. I due sottoschemi condivisi restano identici. Restano minimum=0, conteggio intero, eta' anche frazionaria, enum, minLength, additionalProperties:false e tutti gli altri required.

## Cambiamento esplicito del contratto

| Input numerico | Significato e trattamento |
|---|---|
| Proprieta' omessa | Dato non disponibile; non e' implicitamente zero o false |
| 0 | Valore noto: conteggio nullo della coda oppure eta' zero |
| null | Input invalido del workflow: rifiuto nello schema, prima del router |
| Negativo, stringa, booleano, oggetto, array | Rifiuto; per il conteggio anche i frazionari restano invalidi |

Per nuova ricerca, se mancano prove necessarie a escludere o stabilire le soglie, il preflight resta undetermined e il router restituisce BLOCKED. Una soglia dimostrata puo' bastare anche se l'altra misura manca. Una coda osservata pari a zero resta distinta da una coda sconosciuta. F3 non implica nuova ricerca, il lavoro gia' in corso non viene prevaricato. Priorita', writer, WIP/frontier e anti-repeat restano invariati.

**Non esiste alcun normalizzatore null-to-omission.** Non e' stato implementato ne' presunto un adapter a monte. I produttori devono emettere un payload conforme con omissioni per i dati non disponibili; payload con null sono invalidi. Il controllo difensivo aggiunto al helper produce invalid_queue_evidence/undetermined se il helper viene chiamato direttamente con null, ma non e' una conversione e non precede la validazione Kora. Nessun servizio produttore privato e' stato contattato o modificato.

## Test e tracciabilita'

I quattro casi A/B-starvation-null-age/count conservano esattamente gli input precedenti ma diventano test schema-rejection con atteso valid=false. Il motivo e' il cambiamento esplicito del contratto, non un adattamento all'esito del router. Le vecchie fixture native e i loro attesi BLOCKED/undetermined sono archiviate integralmente in history/null-native-d7f84cc8; tutti i vecchi 164 casi in history/cases-d7f84cc8.json. Il generatore elimina dal tests/ attivo solo le copie identiche a quell'archivio.

160 attesi precedenti restano invariati. Si aggiungono quattro casi di routing: nelle due lane, eta'=0 con conteggio=19 => COMPLETE/not_required; eta'=0 con conteggio omesso => BLOCKED/undetermined. Restano i test omissione di una o entrambe le misure, count=0 e age omessa, soglie esatte 86400 secondi/20 osservazioni, immediatamente inferiori, attivita' ongoing/non-research e tutti i rifiuti preesistenti. I due originali storici attesi RESOLVE rimangono intatti nel loro archivio.

Verificato localmente:

- 540/540 asserzioni di schema su entrambi i tipi, con matrice numeri/null/omissione/tipi invalidi e vincoli oggetto. Le 30 differenze di accettazione nella matrice sono precisamente combinazioni prima ammesse con null, ora respinte. Non si dichiara equivalenza sul dominio null.
- 168/168 casi correnti: 130 pipeline, 21 frontier, 17 rifiuti schema. Tutti sintetici.
- 68/68 nel sottoinsieme starvation (include i quattro rifiuti null); 35/35 sulle precedenze/frontier.
- 154/154 fixture native validate offline e 154/154 sui corrispondenti input/check tramite funzioni pure locali. Quattro vecchie fixture null escono dal bundle eseguibile; quattro nuovi casi zero vi entrano. Il totale resta 151 fixture replay eseguibili + 3 originarie = 154; i 17 rifiuti schema sono locali, non ulteriori test nativi.
- 6/6 verifiche OFFLINE del controllo dello script nativo: errori setup, zero test anche con exit 0, gate falso, JSON invalido bloccano la suite; un singolo test passato la abilita; errori della suite completa restano errori. I comandi git/node/kora sono simulati per questo controllo; nessuna chiamata Kora.

I runner mantengono gli exit code di errore. Vecchi esiti, schemi e rapporti sono archiviati, non riscritti come successi. Confronto storico del vecchio router sulla matrice corrente esplicita: 30/62 errori; non confrontare il numero con 32/62 della vecchia matrice, che conteneva i casi null ora fuori contratto.

## Prova nativa minima, poi suite

Il nuovo script run-native.ps1 verifica SHA completo, checkout separato pulito e bundle (167 file, 154 Test YAML). Prima esegue sullo STESSO bundle:

```powershell
kora test suite --workspace $workspace --name replay-A-starvation-missing-both --environment production --org oltre --json
```

E' una sola fixture di route-activation con entrambe le misure numeriche omesse: atteso BLOCKED e identity_starvation_status=undetermined. La compilazione del medesimo processo deve includere le dichiarazioni di entrambi i tipi; non viene usato un bundle semplificato che nasconda il problema.

La suite completa viene avviata SOLO se il risultato minimo ha exit=0, status=passed, testCount=1, gatePassed=true e gateable=gatePassing=1. __setup__/testCount=0 o qualsiasi risultato ambiguo interrompe lo script. Dopo il superamento:

```powershell
kora test suite --workspace $workspace --environment production --org oltre --json
```

La seconda chiamata seleziona tutte le 154 fixture sotto <checkout>/integrations/kora/control-plane/tests, senza --name o --release. L'archivio replay/history e' fuori dal bundle. Il wrapper consegnato negli outputs fissa il nuovo commit. Non viene modificato il checkout precedente del proprietario.

L'assistente non ha eseguito il probe nativo ne' la suite completa: l'ambiente ha il precedente blocco di scrittura dello stato sessione Kora nel sandbox, senza percorso di escalation autorizzato. Non sono stati copiati token/sessioni, cancellati lock o aggirati dinieghi. **Il superamento del probe nativo e della suite completa resta da verificare tramite il comando manuale.** Gli esiti locali non lo sostituiscono.

## Separazione dagli altri problemi

Controlli generali AGENTS.md rieseguiti sulla copia isolata con schema/preflight aggiornati: 20/22 comandi passati; Python 757 test, 1 failure e 4 errori; Node 336 test, 330 passati e 6 falliti. Sono gli stessi gruppi della baseline, con i limiti locali gia' documentati; non sono un nuovo risultato CI verde e non spiegano il setup Kora.

Policy di rete ancora aperta: deny nel manifest locale/PR contro allow + inheritManaged=true nell'export precedente di rel_4wbyk58gsiuzfh8f. Origine server e policy runtime non verificate, nessun ampliamento permessi o workaround browser. La release esistente non incorpora le correzioni e le sue vecchie validazioni non valgono per questa sorgente.

Nessun dato della review, record, registro o decisione scientifica modificato; nessun servizio privato interrogato. Nessuna nuova release, merge, deploy, scheduler o esecuzione live.
