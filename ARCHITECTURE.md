# Architecture

Expedition Story is a **static-site generator**: a small Python pipeline turns an iNaturalist query into
self-contained HTML, committed into the repo and served by GitHub Pages. There is no runtime backend — the
generator runs locally or in CI, and the published pages are pure HTML/JS that call third-party APIs
(map tiles, photo CDN) directly from the browser.

## Repository layout

```
journeys/<id>/config.json   input: one file per journey (the only thing you author)
lib/                        the engine (pure-stdlib Python)
  walks.py                  iNat fetch (paginated) + segment obs into walks
  geo.py                    haversine + cumulative along-track distance
  gps.py                    accuracy-based GPS quality control
  elevation.py              SRTM 30 m sampling (Open Topo Data), disk-cached
  taicol.py                 Taiwan taxonomy (TaiCoL): 中拉 family/genus + endemism/Red List
  inat_taxa.py              global taxonomy: family/genus from iNat /v1/taxa ancestors
  profile.py                one walk's obs → transect points (scope → QA → elev → distance)
  render.py                 points → self-contained HTML (transect chart + observation map)
generate.py                 orchestrator: config → fetch → (trek | survey) → site/<id>/
build_site_index.py         scans site/*/journey.json → site/index.html (global landing)
new_journey.py              scaffolder: resolve place + write a config + probe (form/CLI)
caches/                     cross-journey caches (gitignored): elevation / taicol / inat_taxa
site/                       generated output (committed; this is what Pages serves)
.github/workflows/          pages.yml (deploy) · create-journey.yml (the form)
```

`site/` is **committed** so Pages can serve it directly; `caches/` and `_*.json` are gitignored.

## The pipeline

`generate.py --journey <id>` reads `journeys/<id>/config.json` and runs:

1. **Fetch** — `walks.fetch(user, place_id, d1, d2)` pages the iNaturalist observations endpoint
   (`order_by=observed_on`, `per_page=200`, `locale=zh-TW`) into one list.
2. **Branch on mode**:
   - **trek** → `run_trek()`: treat *all* observations as one ordered path.
   - **survey** → `walks.segment(obs, walk_gap_min)`: a new walk starts on a new calendar day **or**
     when the intra-day time gap exceeds `walk_gap_min` (default 120 min). Each walk is rendered
     separately.
3. **Build points** — `profile.build(obs, scope, cache_dir)` for each walk / the whole trek:
   - apply **scope** (`exclude_obs_ids`, `time_before`),
   - **`gps.correct`** — flag fixes with `positional_accuracy > 100 m` and snap them to the
     time-interpolated position between their nearest reliable neighbours,
   - **`elevation.sample`** — SRTM 30 m (bilinear) per coordinate, disk-cached,
   - **`geo.cumdist`** — cumulative along-track distance (metres),
   - emit a point dict per observation; backfill any missing elevation by distance interpolation.
4. **Enrich taxonomy** — `enrich_points()` dispatches on `config.taxonomy`:
   - `"taicol"` → `taicol.enrich` (Taiwan: 中拉 family/genus + endemism + IUCN/Red List),
   - `"inat"` → `inat_taxa.enrich` (global: family/genus from each taxon's `/v1/taxa` ancestors).
5. **Render** — `render.transect_html(meta, pts)` produces one self-contained page.
6. **Write** — `site/<id>/…` + a `journey.json` manifest.

Then `build_site_index.py` regenerates `site/index.html` from every `journey.json`.

### Point dict (the shared data model)

Both the chart and the map render the **same** ordered array, so they link by index:

| key | meaning |
|---|---|
| `n` | 1-based order along the walk |
| `t` | time `HH:MM` (CST) |
| `x` / `y` | along-track distance (m) / elevation (m) |
| `lat` / `lng` | GPS-corrected coordinates (for the map) |
| `fl` | 1 if the fix was low-accuracy and interpolated |
| `s` / `c` | scientific name / common name |
| `g` | quality grade (`research` / needs-ID) |
| `a` | positional accuracy (m) |
| `famSci`/`famZh`/`genSci`/`genZh` | family & genus (Latin + 中文), from taxonomy enrichment |
| `end` / `threat` | Taiwan endemism / Red-List code (taicol only; null for inat) |
| `u` / `ph` | iNaturalist observation URL / photo URL |

### `journey.json` manifest

- **trek**: `{id, label, mode, generated_at, d1, d2, days, points, species, trail_km, peak_m, low_m, climb_m}`
- **survey**: `{id, label, generated_at, walks:[{walk_id, date, start, end, n, species}, …]}`

`build_site_index.py` reads these to list journeys (treks first, then surveys).

## Rendering

`render.py` inlines the point array into an HTML template with two views:

- **Elevation transect** (Chart.js + zoom plugin): line + area, points coloured by quality grade,
  GPS-flagged points drawn as red diamonds, external photo tooltip, click → iNaturalist. The x-axis is
  **adaptive** (metres for a short ridge, km for a long trek); card 6 shows **peak + total ascent** for
  treks vs **net climb** for surveys.
- **Observation map** (Leaflet + OpenTopoMap): an orange track polyline through the points, circular
  photo markers (dots when a photo is missing), popups → iNaturalist.
- **Linked hover**: hovering a chart point rings + raises its map marker; hovering a marker activates the
  chart point and pops its photo card. The 科/屬 filter syncs both and clears stale highlights.

Pages are **self-contained**: data is inlined; only libraries (Chart.js, Leaflet from CDN), map tiles,
and photos are fetched live. This keeps every page a single portable file with no build step.

## Output & URLs

```
site/index.html                     global landing (all journeys)
site/<id>/index.html                trek: the transect  ·  survey: the journey index
site/<id>/<walk>/index.html         survey: one walk's transect
site/<id>/journey.json              manifest
```

On Pages these map to `…/expedition-story/<id>/`, etc. All internal links are relative.

## Deployment (GitHub Pages + Actions)

- **`pages.yml`** — on push to `main` touching `site/**` (or manual dispatch): upload `site/` as the Pages
  artifact and deploy (`build_type=workflow`).
- **`create-journey.yml`** — `workflow_dispatch` form → `new_journey.py` (scaffold) → `generate.py` →
  `build_site_index.py` → commit → deploy, all in one run. Inputs are passed via env vars (not inlined)
  to avoid shell injection.

A commit pushed by `GITHUB_TOKEN` does not re-trigger `pages.yml`, so `create-journey.yml` performs its
own Pages deploy step rather than relying on the push trigger.

## External dependencies

| Dependency | Used for | Notes |
|---|---|---|
| iNaturalist API | observations, place resolution, global taxonomy | no key; `locale=zh-TW` for 中文 names |
| Open Topo Data (SRTM 30 m) | elevation | 100 locations/request, ~1 req/s; disk-cached |
| TaiCoL API | Taiwan taxonomy | seeded from the sibling phenology skill cache |
| OpenTopoMap tiles | map basemap | free, CC-BY-SA attribution required |
| Chart.js / Leaflet | chart / map libs | loaded from CDN at view time |

Everything else is Python standard library. Caches make re-generation cheap: only new coordinates and
new taxa hit the network.
