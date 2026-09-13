# Study geography in public research sheets and statistics

Owner request, 13 September 2026: retrieve the country and geographical entity
actually analysed by a paper and show a country chart in the statistics section.

## Source and interpretation

The existing governed `studies[].geography` fact remains the sole research source
(`schema/paper-enrichment.schema.json`, `schema/public-paper-research.schema.json`
and their existing ontology mappings). Geography is already a required extraction
field. No new research database, scheduler, scientific acceptance, identity
reconciliation or automatic inference is introduced by this display change.

Show each study's recorded territorial scope with its source references near the
top of the public sheet. Multiple studies remain separate. Countries are derived
only from current identity-checked public research projections whose geography
fact is `reported`, attributed to `source`, and has resolvable evidence references.
All these remain unreviewed research proposals, not validated geographical coding.

The shared `CILEPaperGeography` helper in `site/paper-sheet-research.js` performs conservative label normalisation, not general
named-entity recognition. It never scans the title, abstract, author affiliations,
publisher address or criminal-group nationality. Country/territory labels use a
closed ISO-style two-letter list, with explicit name aliases and Italian display
labels. A source naming a country with a city/region qualifier can contribute to
that country's count without implying national representativeness. Bare cities
and regions are retained, but no parent country is silently inferred. Historical
states are not allocated to modern successor states. Ambiguous names such as bare
Congo, Korea or Georgia do not automatically select a country.

Existing simple values such as `Italy`, `Italy; Germany`, `Northern Italy`, and
`Calabria (Italy)` are supported. Free prose that cannot safely be normalised
remains visible but is excluded from country counts. `Europe` and `Global` remain
separate coverage categories; they are never expanded into guessed country lists.
A recorded value can also use `Countries: Italy; Germany | Scope: local case studies`
when, and only when, every part is supported by the consulted research source.
This is an optional rendering convention within the existing fact, not a new
schema requirement or permission to rewrite immutable historical proposals.

For future source extraction, record all explicitly analysed countries and retain
cities, regions, study populations and geographical restrictions. Distinguish a
study's actual sample geography from background comparisons, a criminal group's
origin and the authors' locations. When a source supports only a city, region or
supranational area, record that level rather than inventing a country list. When
an abstract is insufficient, preserve missingness until adequate source evidence
is consulted. The existing extraction/calibration and publication gates remain
unchanged. This update does not activate currently disabled model extraction.

## Statistics

`site/bibliometrics.js` publishes its exact selected record population to the
read-only `site/geography-statistics.js` renderer. The existing pending toggle
continues to separate the assessed corpus from the provisional register. No
independent population or automatic DOI/title identity merge is used.

The renderer reads the same unauthenticated public research endpoint as a paper
sheet, omits credentials, checks the candidate snapshot and retains no persistent
copy. At most four requests run concurrently. Consecutive failures stop the scan;
partial coverage and transport failures remain explicit, and the user can retry.
An old response cannot overwrite a different bibliographic snapshot. Only current
selected records contribute to the plot, including when the toggle changes while
requests are in flight. Canonical records that cannot be linked by an existing
candidate ID remain explicitly unassociated; a relationship is never guessed.

A record counts at most once for each country, even across several studies.
Multi-country records count in each supported country. Percentages divide by the
number of selected records with at least one identified country; totals can exceed
100%. The page also reports country coverage over the entire selected population,
partial geographical coverage, missing extraction, ambiguous/not-normalisable
scope, supranational/global scope, stale/withheld projections and read failures.
Provisional bibliographic duplicates remain separate records until the governed
identity process resolves them; counts are not asserted to be unique canonical
scholarly works. Expanding a country lists contributing titles and study scopes.

## Checks

`python3 -m unittest discover -s tests -p 'test_study_geography.py'` covers multiple
countries/studies, repeated IDs, evidence requirements, missingness, ambiguous
names, source-only geography, population changes and public endpoint wiring.
Fixtures are synthetic software tests and are not scientific calibration evidence.
The existing full archive CI remains the validation and delivery path.
