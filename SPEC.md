# Spec

Reference for journey inputs, generated outputs, and the create-journey form.

## I/O contract

| | |
|---|---|
| **Input** | an iNaturalist query: **user × place × date-range**, plus a mode |
| **Process** | fetch → (segment / merge) → GPS-QA → SRTM elevation → along-track distance → taxonomy → render |
| **Output** | self-contained HTML: an elevation transect **+** an observation map, and a journey index |

## `journeys/<id>/config.json`

```jsonc
{
  "id": "nepal-2023-trek",          // required · URL slug (folder under site/)
  "label": "尼泊爾 2023 · 喜馬拉雅健行", // required · display title
  "user_login": "bunnytailgrass",   // required · iNaturalist observer
  "place_id": 7335,                 // required · iNaturalist numeric place id
  "d1": "2023-10-01",               // required · start date (YYYY-MM-DD, inclusive)
  "d2": "2023-10-16",               // required · end date  (YYYY-MM-DD, inclusive)

  "mode": "trek",                   // optional · "trek" | absent (= survey)
  "taxonomy": "inat",               // optional · "inat" | "taicol" (default: taicol)
  "walk_gap_min": 120,              // optional · survey segmentation gap, minutes (default 120)

  "scope": {                        // optional · data cleaning
    "exclude_obs_ids": ["185668064", "185668091"],  // drop these observation ids
    "time_before": "14:56"          // drop observations at/after this local time
  },

  "snapshot": "2023/10 · Khumbu"    // optional · footer note only
}
```

### Field reference

| Field | Type | Required | Notes |
|---|---|---|---|
| `id` | string | ✅ | Slug; becomes `site/<id>/` and the Pages path. Must be unique. |
| `label` | string | ✅ | Page/title text. May be Chinese. |
| `user_login` | string | ✅ | iNaturalist username. |
| `place_id` | integer | ✅ | Resolve a name via `/v1/places/autocomplete` (or `new_journey.py`). |
| `d1`, `d2` | `YYYY-MM-DD` | ✅ | Inclusive range; filters iNaturalist `d1`/`d2`. |
| `mode` | `"trek"` \| absent | — | `trek` = one continuous transect. Absent = survey (one transect per walk + index). |
| `taxonomy` | `"inat"` \| `"taicol"` | — | Family/genus source. Omitted ⇒ `taicol`. Use `inat` outside Taiwan. |
| `walk_gap_min` | integer | — | Survey only. New walk on new day **or** gap > this (default 120). |
| `scope.exclude_obs_ids` | string[] | — | Observation ids to drop (off-trail outliers, bad points). |
| `scope.time_before` | `"HH:MM"` | — | Drop observations at/after this local (CST) time. |
| `snapshot` | string | — | Cosmetic footer label. |
| `elevation`, `brand` | any | — | Ignored by the engine (legacy metadata). |

### Mode behaviour

- **survey** (no `mode`): observations are segmented into walks; **each walk → one transect** at
  `site/<id>/<walk>/index.html`, plus a journey index at `site/<id>/index.html`. Card 6 = net climb.
- **trek** (`"mode":"trek"`): segmentation is skipped; **all observations → one continuous transect** at
  `site/<id>/index.html` (x = cumulative trek distance). Card 6 = peak elevation + total ascent.

## Generated output

```
site/index.html                 global landing — lists every journey (treks first, then surveys)
site/<id>/index.html            trek: the transect   ·   survey: the journey index
site/<id>/<walk>/index.html     survey only: one walk's transect (walk id = its date, e.g. 2026-04-25)
site/<id>/journey.json          manifest (see below)
```

Each transect page contains, top to bottom: title + summary cards + family/genus filters → **elevation
transect** (Chart.js) → **observation map** (Leaflet + OpenTopoMap) → footer. Both views share one point
array and are linked by hover; the 科/屬 filter drives both. Pages are responsive (cards reflow, map
480→360 px on mobile).

### `journey.json`

```jsonc
// trek
{ "id", "label", "mode": "trek", "generated_at",
  "d1", "d2", "days", "points", "species", "trail_km", "peak_m", "low_m", "climb_m" }

// survey
{ "id", "label", "generated_at",
  "walks": [ { "walk_id", "date", "start", "end", "n", "species" }, … ] }
```

`build_site_index.py` consumes these to build the global index.

## Create-journey form

GitHub → **Actions** → **Create journey** → *Run workflow* (or `gh workflow run create-journey.yml -f …`).
Backed by `new_journey.py`; the same script runs locally as a CLI.

| Input | Default | Meaning |
|---|---|---|
| `user_login` | `bunnytailgrass` | iNaturalist observer |
| `place` | — | Place **name** (resolved via iNat) or a numeric `place_id` |
| `d1`, `d2` | — | Date range (`YYYY-MM-DD`) |
| `mode` | `trek` | `trek` \| `survey` |
| `taxonomy` | `auto` | `auto` (Taiwan→`taicol`, else `inat`) \| `inat` \| `taicol` |
| `exclude_ids` | — | Comma-separated observation ids to drop |
| `label` | place name | Display label |
| `id` | derived | URL slug; derived as `<slug>-<year>-<mode>` if blank |
| `gap_min` | `120` | Survey walk-gap minutes |

**Scaffolder behaviour (`new_journey.py`):**

- **Place resolution** — numeric input is used as-is; a name is looked up via
  `/v1/places/autocomplete`. Name matches are ambiguous, so the run log **lists the top candidates**
  (id + display name) and warns which one was picked; re-run with the numeric `place_id` to correct.
- **`taxonomy: auto`** — `taicol` if the resolved place is in Taiwan (`, TW` / Taiwan / 臺灣 / 台灣),
  else `inat`.
- **Probe** — reports obs count, walk count, and flags observations **> 50 km** from the cluster as
  possible off-trail outliers, printing the ids to feed back into `exclude_ids` on a re-run.
- **Output** — writes `journeys/<id>/config.json` and emits `journey_id` for the workflow's later steps.

The workflow then runs `generate.py` + `build_site_index.py`, commits, and deploys to Pages in one run.

## Invariants / gotchas

- An observation needs coordinates to appear (no-geo observations are dropped by `profile.build`).
- `taxonomy` defaults to `taicol` when omitted — **set `inat` for overseas journeys** or families come
  back empty. (`new_journey.py`/the form always write it explicitly.)
- `id` must be unique; reusing one overwrites that journey.
- Dates are treated in **CST (UTC+8)**.
- Any push touching `site/**` redeploys Pages; docs/config-only changes do not.
