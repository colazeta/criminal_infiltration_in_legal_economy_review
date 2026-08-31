# GitHub App del curatore

La GitHub App consente di leggere la coda e inviare una decisione dalla console
`curate.html` servita dal Worker su un'origine dedicata. La pagina omonima su
GitHub Pages resta l'ingresso pubblico e vi rimanda senza ricevere credenziali.
GitHub continua a essere il registro autenticato dell'istruzione: la App crea
una issue strutturata attribuita al curatore e il
workflow esistente prepara una pull request. Non modifica direttamente i CSV,
non promuove un candidato e non effettua merge.

## Architettura

| Componente | Funzione | Dati persistenti |
|---|---|---|
| GitHub Pages | ingresso pubblico, conteggi aggregati e codici controllati | nessun candidato e nessuna sessione |
| Worker `curator-app/` | origine isolata della console, OAuth, lettura della coda e creazione dell'issue | sessione cifrata soltanto nel browser della propria origine |
| Durable Object | serializza un singolo `submissionId` e conserva il risultato | fingerprint e riferimento alla issue; mai token, evidenza o candidato |
| GitHub App user-to-server | attribuisce letture e scritture all'utente autorizzato | token GitHub temporaneo, massimo otto ore |
| GitHub Actions | applica il parser governato, valida e apre la PR | coda corrente e azioni append-only dopo il merge |

Il backend usa il flusso web OAuth della GitHub App con PKCE. Il token GitHub
in chiaro resta nel Worker. La console gira sul dominio dedicato del Worker,
non sull'origine condivisa `colazeta.github.io`. Il browser riceve una sessione
cifrata e autenticata con AES-GCM, conservata soltanto nel `sessionStorage` di
quell'origine isolata; la pagina elimina
immediatamente il frammento di callback dalla barra degli indirizzi. La sessione
non è rinnovata e scade entro otto ore. Il logout chiede anche a GitHub di
revocare il token.

## Permessi della GitHub App

Registrare la App sull'account `colazeta` e installarla soltanto sul repository
`criminal_infiltration_in_legal_economy_review`.

- Repository permission **Issues: Read and write**.
- Metadata: accesso in sola lettura implicito.
- Nessun permesso Contents, Actions, Pull requests o Administration.
- Webhook non necessario; può restare disattivato.
- Scadenza dei token user-to-server attiva.
- Callback URL esatta: `https://<worker-host>/auth/callback`.
- Homepage URL: la pagina pubblica `curate.html`.

La App opera esclusivamente con un **user access token**. Non genera token di
installazione e non necessita di App ID o private key. Questa scelta mantiene
l'issue attribuita a `colazeta`, requisito controllato anche da
`candidate-curation.yml`.

## Configurazione del Worker

Il backend è scritto per Cloudflare Workers e non usa dipendenze runtime.
Il file Wrangler include la migrazione SQLite iniziale `v1` del coordinatore;
non rimuoverla o rinominarla dopo il primo deploy.

1. Copiare `curator-app/wrangler.example.jsonc` in
   `curator-app/wrangler.jsonc`.
2. Accedere a Cloudflare con `npx wrangler@latest login`.
3. Eseguire un primo deploy per ottenere l'hostname dedicato `workers.dev`; in
   questa fase `/health` può rispondere `configuration_required`. Il Worker
   pubblica soltanto gli asset necessari alla console, pur usando `site/` come
   directory sorgente.
4. Registrare la GitHub App con la callback esatta del Worker e installarla sul
   solo repository selezionato.
5. Inserire il Client ID in `wrangler.jsonc`, sostituire `SITE_URL` con
   `https://<worker-host>/curate.html` e `GITHUB_CALLBACK_URL` con la callback
   esatta sulla stessa origine.
6. Configurare i due segreti senza scriverli in file versionati:

   ```bash
   cd curator-app
   npx wrangler@latest secret put GITHUB_CLIENT_SECRET
   openssl rand -base64 32 | npx wrangler@latest secret put SESSION_SECRET
   ```

7. Eseguire il deploy definitivo con `npx wrangler@latest deploy`.
8. Verificare che `https://<worker-host>/health` risponda con
   `{"status":"ok"}`.
9. Inserire l'URL completo della console verificata nel solo campo
   `secureAppUrl` di `site/curator-config.js`; lasciare `apiBaseUrl` vuoto sulla
   copia GitHub Pages. Validare e pubblicare il collegamento attraverso una
   pull request.

`curator-app/wrangler.jsonc`, `.dev.vars` e ogni variante locale contenente
credenziali restano esclusi da Git. Il Client ID non è segreto; il client secret
e `SESSION_SECRET` lo sono.

## Contratto HTTP

| Endpoint | Metodo | Funzione |
|---|---|---|
| `/health` | GET | verifica configurazione senza restituire valori |
| `/auth/login` | GET | avvia OAuth con state cifrato e PKCE |
| `/auth/callback` | GET | verifica account, installazione e repository |
| `/api/session` | GET | convalida la sessione corrente |
| `/api/candidates` | GET | legge le issue aperte con label `curation:queue` |
| `/api/decisions` | POST | verifica la scheda e crea l'issue `curation:decision` |
| `/auth/logout` | POST | revoca il token GitHub e termina la sessione locale |

Le API accettano richieste browser soltanto dalla stessa origine isolata della
console, non usano cookie cross-site e richiedono un bearer di sessione. Le
mutazioni richiedono inoltre un valore anti-CSRF e un submission ID UUID. Un
Durable Object distinto per UUID serializza le richieste concorrenti, rifiuta
riusi con contenuto diverso e conserva soltanto fingerprint e risultato. Il
Worker verifica che la scheda sia ancora aperta, abbia la label di coda e
contenga il candidate ID selezionato.

## Validazione locale

```bash
node --check curator-app/src/index.js
node --check curator-app/src/worker.js
node --test curator-app/test/*.test.js
python3 scripts/curation/build_curator_options.py
python3 scripts/validation/validate_site.py
```

I test coprono cifratura e scadenza della sessione, PKCE, isolamento degli asset,
controllo dell'origine, combinazioni dei campi, parsing delle schede, concorrenza
idempotente e creazione della decisione. Non contattano GitHub.

## Comportamento fail-closed

La richiesta viene bloccata se account, repository, installazione, origine,
sessione, scheda, label, candidate ID, combinazione dei campi o conferma non
sono verificabili. Una decisione inviata correttamente può soltanto avviare il
workflow già governato. Il parser Python resta l'autorità finale sui codici
correnti e nessun errore del backend è trasformato in una decisione implicita.
