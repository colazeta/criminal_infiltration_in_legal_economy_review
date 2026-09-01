# Publishing the archive with GitHub Pages

## What is already configured

The repository uses a custom GitHub Actions workflow rather than Jekyll.

- Public URL: <https://colazeta.github.io/criminal_infiltration_in_legal_economy_review/>
- Broader AML collection: <https://colazeta.github.io/criminal_infiltration_in_legal_economy_review/aml.html>
- Site source: `site/`
- Public curator entrypoint: `site/curate.html`
- Isolated authenticated console and backend: `curator-app/` (deployed separately)
- Daily statistics page: `site/stats.html`
- Aggregate metrics ledger: [GitHub issue #30](https://github.com/colazeta/criminal_infiltration_in_legal_economy_review/issues/30)
- Workflow: `.github/workflows/archive.yml`
- Publishing branch: `main`
- GitHub Pages source: **GitHub Actions**
- HTTPS: enforced on the default `colazeta.github.io` domain

The live repository setting was verified on 2026-08-30. Do not click GitHub's
“Configure Jekyll” or “Configure Static HTML” suggestions: the project already
has its own governed build and deploy workflow.

## How the first public deployment happens

1. Confirm that every scientific decision in the release was explicitly made by
   an authorised curator. A maintenance-only release may proceed under continuing
   owner authority.
2. Confirm the PR's **Validate and publish archive** workflow is green.
3. Merge the validated PR into `main`. Registry/publication changes are never
   auto-merged; documentation, code and site maintenance may be merged by an
   authorised agent when the owner has already granted continuing authority.
4. The push to `main` starts `.github/workflows/archive.yml`.
5. The `quality` job validates the repository, tests, deterministic export,
   archive, site and JavaScript.
6. Only after quality succeeds, the `deploy` job uploads the `site/` artifact and
   publishes it to GitHub Pages.
7. Open **Actions → Validate and publish archive** and verify both jobs are green.
8. Open **Settings → Pages** and use **Visit site**, or open the public URL above.

GitHub states that a first publication or update can take several minutes. The
Pages artifact remains static and contains no server-side secret or curator
session. Once `site/curator-config.js` contains the reviewed `secureAppUrl`, the
public page links to the separately deployed console described in
[`github-app.md`](github-app.md). The console and API share a dedicated Worker
origin; reusable authorization values never enter `colazeta.github.io`. If the
console is absent, the page fails closed and exposes the authenticated GitHub
issue form as a fallback.

During deployment only, the workflow uses its short-lived GitHub token to read
aggregate comments from metrics ledger #30. No token is included in the site
artifact.

## What happens on later updates

Every reviewed merge to `main` repeats the same sequence. The workflow rebuilds
`site/data/archive.json` and `site/data/archive.csv` from the governed registry;
it does not publish candidate intake or reviewer notes. A separate deterministic
builder creates `site/data/secondary-collections.json` and CSV only from
canonical `review_excluded` works with a current `not_eligible` decision and an
independent secondary-publication approval. Those records appear on `aml.html`
and never enter the core archive counts or saturation measures. Another
deterministic step derives `site/data/curator-stats.json` from the curation layer
using a closed allowlist of aggregate counts only: open/completed totals, work
lanes, legacy/daily origin totals and routed secondary-collection totals.

The workflow also runs once per day after the surveillance automation. It reads
ledger #30, accepts only comments by the configured repository owner, validates
their schema and creates `site/data/research-stats.json`. A read, author or
validation failure stops deployment, leaving the previous valid site online.
The committed statistics file is an empty deterministic baseline used by pull
request checks; the deployed artifact is enriched from the ledger.

A public archive with zero records is a valid release when no work currently
passes the independent publication gate, including while review is pending or
records are withheld or withdrawn. The interface, aggregate editorial counts
and methodology remain available.

## Local preview before merge

```bash
python3 scripts/validation/validate_repository.py
python3 -m unittest discover -s tests -p 'test_*.py'
python3 scripts/build_archive.py
python3 scripts/build_secondary_collections.py
python3 scripts/metrics/build_research_stats.py
python3 scripts/curation/build_curator_stats.py
python3 scripts/curation/build_curator_options.py
python3 scripts/validation/validate_archive.py
python3 scripts/validation/validate_site.py
node --check site/app.js
node --check site/aml.js
node --check site/stats.js
node --check site/curator.js
node --check site/curator-config.js
node --check curator-app/src/index.js
node --check curator-app/src/worker.js
node --test curator-app/test/*.test.js
python3 -m http.server 8000 --directory site
```

Open <http://localhost:8000>. The build itself performs no network request.

## Troubleshooting

| Symptom | Check | Safe response |
|---|---|---|
| Public URL returns 404 before the first release | Is the workflow present on `main` and has its deploy job run? | Merge only after review, then inspect the first `main` run |
| `quality` fails | Open the failing step and reproduce it locally | Fix in a new reviewed commit; do not bypass the job |
| `configure-pages` fails | Settings → Pages → Source must be GitHub Actions | Restore that setting; do not add a second template workflow |
| Artifact upload fails | `site/index.html` and generated data must exist | Rebuild and validate the `site/` directory |
| Deployment permission fails | Deploy job needs `pages: write` and `id-token: write` | Repair the pinned workflow permissions in a reviewed PR |
| Site is stale | Compare deployed workflow SHA with current `main` | Wait for the current run or re-run the failed job |
| Statistics are stale | Inspect ledger #30 and the last scheduled workflow | Repair an invalid or missing authorised ledger comment; never invent a zero |
| Statistics deployment fails | Check comment author, schema and reconciled totals | Correct the ledger explicitly; do not weaken validation |
| Site is empty | Check governed publication rows and archive counts | Treat zero as valid unless an approved published row is missing |
| A link breaks under the project URL | Avoid root-relative `/...` links | Use paths relative to the `site/` directory |

## Optional custom domain

A custom domain is not required. If one is later chosen, configure it in
**Settings → Pages**, add the required DNS records and retain HTTPS. This is an
owner decision because it changes public routing; do not add a `CNAME` file or
change DNS automatically.

Official GitHub guidance:

- [Configuring a Pages publishing source](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site)
- [Creating a GitHub Pages site](https://docs.github.com/en/pages/getting-started-with-github-pages/creating-a-github-pages-site)
- [Using custom Pages workflows](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages)
