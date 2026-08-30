# Publishing the archive with GitHub Pages

## What is already configured

The repository uses a custom GitHub Actions workflow rather than Jekyll.

- Public URL: <https://colazeta.github.io/criminal_infiltration_in_legal_economy_review/>
- Site source: `site/`
- Curator help page: `site/curate.html`
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
site is static: it needs no server, database, token or secret at runtime. The
public curator page therefore contains instructions and links only; the
write-capable form remains inside authenticated GitHub Actions.

## What happens on later updates

Every reviewed merge to `main` repeats the same sequence. The workflow rebuilds
`site/data/archive.json` and `site/data/archive.csv` from the governed registry;
it does not publish candidate intake or reviewer notes.

A public archive with zero records is a valid release when no work currently
passes the independent publication gate, including while review is pending or
records are withheld or withdrawn. The interface, aggregate editorial counts
and methodology remain available.

## Local preview before merge

```bash
python3 scripts/validation/validate_repository.py
python3 -m unittest discover -s tests -p 'test_*.py'
python3 scripts/build_archive.py
python3 scripts/validation/validate_archive.py
python3 scripts/validation/validate_site.py
node --check site/app.js
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
