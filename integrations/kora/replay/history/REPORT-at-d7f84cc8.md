# Kora __setup__: schema fragments, 19 settembre 2026

## Prova nativa ricevuta

Il proprietario ha riferito l'esecuzione nativa sul commit 631068912c29561a76279229dc36107abd7ccb22: arresto in __setup__, testCount=0, codice UNSUPPORTED_CONSTRUCT e messaggio `Process type 'ActivationInput' schema fragments must declare an explicit 'type'.` Non e' stato allegato il risultato JSON completo. La prova ha eseguito **zero delle 154 fixture**, non 154 test falliti e non un test della logica di starvation. Evidenza registrata in native-setup-63106891.json come user-reported.

## Frammenti precisi

Nel file processes/cile-hourly-control-plane.yaml, sotto ciascuno dei due percorsi:

- types.ActivationInput.properties.identity_preflight_evidence.properties
- types.ActivationWithFrontier.properties.identity_preflight_evidence.properties

si trovavano queste due dichiarazioni:

```yaml
pending_observation_count: {type: [integer, 'null'], minimum: 0}
oldest_pending_age_seconds: {type: [number, 'null'], minimum: 0}
```

Sono quattro frammenti in totale. Il primo in ordine sorgente e' pending_observation_count di ActivationInput, seguito dall'eta'. La diagnostica ricevuta non contiene un JSON path del compilatore: l'identificazione puntuale deriva dall'ispezione del bundle e dalla regola pubblicata dalla CLI, non da uno stack trace server.

`type` non manca materialmente: e' una sequenza YAML anziche' uno scalare. `kora schema get process --json`, CLI 0.13.0, pubblica per i frammenti il tipo scalare string/integer/number/boolean/object/array/null. La forma array non appartiene a quell'elenco. L'errore nativo e' coerente con il compilatore che non riconosce un tipo esplicito in quella rappresentazione.

Il solo schema della risorsa Process accetta anche la vecchia forma annidata: i livelli interni non sono ricorsivamente ristretti dalla superficie pubblicata. Questo spiega perche' i precedenti controlli offline non avevano intercettato il blocco. Il nuovo controllo visita i soli veri frammenti di schema, senza aggiungere type a properties, required, enum o ad altri contenitori.

## Correzione limitata e semantica

```yaml
pending_observation_count: {type: integer, nullable: true, minimum: 0}
oldest_pending_age_seconds: {type: number, nullable: true, minimum: 0}
```

Applicata esattamente quattro volte, in entrambi i tipi. Nessun altro cambiamento allo schema, verificato invertendo esclusivamente queste quattro sostituzioni e confrontando l'intero documento con quello archiviato. I due sottoschemi identity_preflight_evidence restano identici.

Le proprieta' restano opzionali, senza default e senza coercizione. Null resta ammesso solo nei due valori numerici; non viene esteso all'oggetto evidence, alla natura dell'attivita' o al riferimento. Il conteggio resta intero non negativo; l'eta' numero non negativo, anche frazionario. Minimum, required, enum, minLength e additionalProperties:false restano invariati. Dati assenti/null conservano il comportamento undetermined del preflight quando sono necessari; non sono convertiti in zero o false. Router, preflight, fixture e attesi non sono cambiati.

La [documentazione AJV](https://ajv.js.org/json-schema.html#nullable-openapi) descrive type scalare + nullable:true come equivalente all'unione con null; questo e' verificato anche dal confronto locale. Lo schema risorsa CLI ammette la dichiarazione scalare e le parole chiave aggiuntive. **Non e' una prova che il compilatore/runtime server Kora conservi nullable**: tale compatibilita' resta da confermare con la nuova esecuzione nativa. La sorgente del compilatore non e' inclusa nella CLI installata; non e' stato effettuato accesso a repository privati o al dominio browser negato per ottenerla. Non dichiariamo risolto il setup nativo prima di quella prova.

## Verifiche offline eseguite ora

- 85 frammenti ispezionati: tutti dichiarano un type scalare ammesso; la versione precedente presenta esattamente i quattro frammenti array sopra.
- 542/542 asserzioni indipendenti su entrambi i tipi: prodotto incrociato di omissione/null/numeri validi/negativi/frazionari/stringhe/booleani/oggetti/array, piu' required, chiavi extra, enum e minLength. Vecchio e nuovo schema hanno gli stessi esiti; l'atteso e' scritto separatamente, non ricavato dal SUT.
- Accettazione invariata per tutti i 164 input esistenti; schema intero invariato salvo le quattro dichiarazioni.
- Replay completi 164/164, starvation 64/64, precedenze/frontier 35/35.
- 154/154 fixture native valide offline; 154/154 passate tramite funzioni pure locali sui medesimi input/check YAML. Non sono esecuzioni Kora/SDK/sandbox.
- Archivio dei due casi originali integro. Nessuna modifica agli attesi, ai gate o alle regole degli exit code.

check-fixtures.mjs richiama ora anche check-process-types.mjs. La nuova verifica e' un controllo offline mirato, non una riproduzione del compilatore Kora. Risultati in process-type-checks.json; schema CLI acquisito in evidence/kora-process-schema-0.13.0.json; originale in history/process-schema-63106891.yaml.

## Nuovo tentativo nativo e selezione

Lo script PowerShell consegnato separatamente fissa il nuovo commit, verifica un checkout separato pulito ed esegue l'ispettore del bundle prima dei test. Non modifica il checkout 63106891 gia' usato dal proprietario. Il bundle contiene ancora 167 file e **154 fixture** sotto integrations/kora/control-plane/tests. Nessun --name e nessun --release; archivio storico escluso. Il comando resta kora test suite --workspace <checkout>/integrations/kora/control-plane --environment production --org oltre --json.

**Nuove esecuzioni native effettuate dall'assistente: 0.** Il prossimo tentativo deve prima superare __setup__; solo un risultato con fixture effettivamente eseguite puo' verificare null, vincoli e routing in Kora. Non si deduce un native pass dalla validazione offline.

## Questioni separate

I controlli generali del repository restano distinti: rieseguiti sulla copia isolata con lo schema aggiornato, 20/22 comandi passati; Python 757 test, 1 failure e 4 errori; Node 336 test, 330 passati e 6 falliti, negli stessi gruppi gia' documentati nella baseline. Non sono attribuiti a questo setup Kora e non sono mascherati.

Policy di rete ancora aperta: deny nel manifest locale/PR, allow + inheritManaged=true nell'export acquisito della release rel_4wbyk58gsiuzfh8f. Origine server e runtime/IR effettivo non verificati; nessun ampliamento permessi o aggiramento del diniego browser. La release esistente non incorpora questa correzione; le sue vecchie validazioni non convalidano il nuovo codice.

Nessun dato della review, registro, decisione scientifica o servizio privato modificato. Nessuna nuova release, merge, deploy, scheduler o esecuzione live.


La relazione precedente, inclusa la separazione archivio/suite corrente, e' conservata in [history/REPORT-at-63106891.md](history/REPORT-at-63106891.md).
