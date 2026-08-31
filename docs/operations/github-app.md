# GitHub App del curatore

La GitHub App consente di leggere la coda e inviare una decisione direttamente
da `curate.html`. GitHub continua a essere il registro autenticato
dell'istruzione: la App crea una issue strutturata attribuita al curatore e il
workflow esistente prepara una pull request. Non modifica direttamente i CSV,
non promuove un candidato e non effettua merge.

## Architettura

| Componente | Funzione | Dati persistenti |
|---|---|---|
| GitHub Pages | interfaccia, conteggi aggregati e codici controllati | nessun candidato e nessun segreto |
| Worker `curator-app/` | OAuth, controlli di sessione, lettura della coda e creazione dell'issue | nessun database |
| GitHub App user-to-server | attribuisce letture e scritture all'utente autorizzato | token GitHub temporaneo, massimo otto ore |
| GitHub Actions | applica il parser governato, valida e apre la PR | coda corrente e azioni append-only dopo il merge |

Il backend usa il flusso web OAuth della GitHub App con PKCE. Il token GitHub
in chiaro resta nel Worker. Il browser riceve una sessione cifrata e autenticata
con AES-GCM, conservata soltanto in `sessionStorage`; la pagina elimina
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

1. Copiare `curator-app/wrangler.example.jsonc` in
   `curator-app/wrangler.jsonc`.
2. Accedere a Cloudflare con `npx wrangler@latest login`.
3. Eseguire un primo deploy per ottenere l'hostname `workers.dev`; in questa
   fase `/health` può rispondere `configuration_required`.
4. Registrare la GitHub App con la callback esatta del Worker e installarla sul
   solo repository selezionato.
5. Inserire il Client ID in `wrangler.jsonc` e sostituire
   `GITHUB_CALLBACK_URL` con l'URL esatto.
6. Configurare i due segreti senza scriverli in file versionati:

   ```bash
   cd curator-app
   npx wrangler@latest secret put GITHUB_CLIENT_SECRET
   openssl rand -base64 32 | npx wrangler@latest secret put SESSION_SECRET
   ```

7. Eseguire il deploy definitivo con `npx wrangler@latest deploy`.
8. Verificare che `https://<worker-host>/health` risponda con
   `{"status":"ok"}`.
9. Inserire l'origine HTTPS verificata in `site/curator-config.js`, quindi
   validare e pubblicare il sito attraverso una pull request.

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

Le API accettano richieste browser soltanto dall'origine della pagina
configurata, non usano cookie cross-site e richiedono un bearer di sessione. Le
mutazioni richiedono inoltre un valore anti-CSRF e un submission ID UUID usato
come marcatore di idempotenza. Il Worker verifica che la scheda sia ancora
aperta, abbia la label di coda e contenga il candidate ID selezionato.

## Validazione locale

```bash
node --check curator-app/src/index.js
node --test curator-app/test/*.test.js
python3 scripts/curation/build_curator_options.py
python3 scripts/validation/validate_site.py
```

I test coprono cifratura e scadenza della sessione, PKCE, controllo CORS,
combinazioni dei campi, parsing delle schede, idempotenza e creazione della
decisione. Non contattano GitHub.

## Comportamento fail-closed

La richiesta viene bloccata se account, repository, installazione, origine,
sessione, scheda, label, candidate ID, combinazione dei campi o conferma non
sono verificabili. Una decisione inviata correttamente può soltanto avviare il
workflow già governato. Il parser Python resta l'autorità finale sui codici
correnti e nessun errore del backend è trasformato in una decisione implicita.
