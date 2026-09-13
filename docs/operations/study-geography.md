# Study geography and country statistics

Owner request, 13 September 2026: recover the geographical entity analysed by each paper and expose country statistics in the existing statistics section.

## Source and interpretation

The source is the existing, current, identity-checked public research projection (`GET /api/public-paper-research?id=...`), not title keywords, author affiliations, publisher location or the nationality of criminal actors. Geography remains study-local: the original `studies[].geography` value, its source locators, consultation coverage and update timestamp are retained. The same geographical fact is already visible in each research sheet under its study. `site/study-geography.js` adds a country/territory view and a per-paper source drill-down to Statistics.

This is a read-only presentation change. It recovers geography already present in stored source-linked research proposals. It does not claim to have completed a new source-reading backfill, retrieved every missing country, activated a model or validated an extraction scientifically. When a current extraction acquires geography, the next page load or refresh incorporates it without another Pages build. Missing or narrative-only geography still requires the existing governed extraction/review process; the browser does not manufacture a research fact.

Only `reported` facts attributed to `source`, with resolvable public evidence-span/source links, enter country normalisation. Analyst-only interpretations and ambiguous facts remain visible but do not enter the bars. Every result remains an unreviewed proposal with its actual abstract-only, partial-text or full-text consultation boundary.

## Normalisation

The renderer uses a fixed ISO 3166-1 alpha-2 allowlist, English/Italian country and territory names from the browser's locale data, and bounded explicit aliases. Whole recognised names/lists are required: it does not scan arbitrary prose for country keywords. List separators, directional subnational qualifiers and simple parenthetical local detail are supported conservatively. Full country names such as South Africa and North Macedonia take precedence over directional qualifiers.

Original geographical text is always retained. Cities/regions without a safely identified parent country are not guessed; ambiguous names such as bare Georgia or Congo are unresolved. Mixed country and unspecified-region expressions remain unresolved instead of presenting a partial list as exhaustive. Broad scopes such as Europe, the European Union or global analysis are not expanded to countries. Country/territory labels describe statistical geography and do not assert sovereignty. Browser locale aliases may differ; conservative unresolved results are preferable to a fabricated match.

No new governed table, scientific decision or stored classification is introduced. The semantic source remains `ontology/modules/public-paper-research.json`, including the study geography slot mapped to `extraction_geography`. The transient UI diagnostics are display states, not new review, eligibility or access states.

## Counting and scope

The default remains the evaluated corpus. The existing “Includi record ancora da analizzare” toggle adds the pending/needs-full-text register. The geographical panel follows exactly that selection and does not silently broaden it. A provisional register entry is counted as a record, not asserted to be a canonically unique scholarly work.

Each selected record contributes at most once per country, even when several of its studies concern that country. A multinational record contributes once to each identified country. Consequently national totals and percentages are overlapping and must not be summed. Percentages use all records in the selected view, including uncoded records. The panel separately reports records with at least one country, multinational records, partially coded multi-study records and the various missingness states. These are counts of literature coverage, not estimates of criminal infiltration prevalence.

The full sorted country ranking uses horizontal bars from a common zero baseline, with explicit record counts and percentages. Original study geography and source locators remain inspectable below the chart. Missingness distinguishes no extraction, no structured study, not reported, not verifiable, not applicable, unresolved scope, stale/withheld projections, failed requests and unattempted records. Failed requests never become evidence that a paper lacks geographical information.

## Delivery and verification

The existing public endpoint and `CILEPaperResearch.selectRecord` supply identity checks. Reads omit credentials, bypass the cache, time out and use at most four concurrent requests with a circuit breaker. Refresh replaces previous observations, including revisions with unchanged record counts. Changing the selected scope while requests run cannot restore an old selection. No private endpoint, new store, source grant, schedule or model call is introduced.

The test fixtures are synthetic software checks, not research observations or calibration evidence. Tests cover normalisation exclusions, multinational/multiple-study counting, denominators, provenance, identity errors, distinct missingness, bounded scans, refresh and delayed scope changes. Full repository/site validation remains required on the exact PR head before a maintenance merge. Deployment acceptance and public served-asset verification are separate from proof that all papers have populated geography.
