# Expedition Story

> 把任一段 iNaturalist 踏查（**使用者 × 地點 × 日期區間**）自動產成一個「海拔剖面圖 + 觀測點地圖」網站。
> Turn any iNaturalist survey (**user × place × date-range**) into an elevation-transect + observation-map site.

自包含、可部署的通用工具，由二格山稜線剖面圖一般化而來。
A self-contained, deployable generalization of the original 二格山 ridge transect.

**Live:** <https://bunnytailgra22.github.io/expedition-story/>

---

## Concept / 概念

Each journey is one `journeys/<id>/config.json`. The pipeline is:

```
iNaturalist query (user × place × d1–d2)
        │  fetch
        ▼
   walks: auto-segment by day + time gap
        │  per walk (or the whole trek)
        ▼
   profile: scope filter → GPS-QA → SRTM elevation → along-track distance
        │  enrich
        ▼
   taxonomy: family/genus 中拉名 (TaiCoL in Taiwan · iNaturalist elsewhere)
        │  render
        ▼
   self-contained HTML: elevation transect  +  observation map (below)
```

Two output shapes, chosen by config — see **[the core principle](DESIGN.md#core-principle)**:

- **Survey mode** (default) — repeated visits to the *same* path (e.g. the 二格山 ridge). Output is
  **one transect per walk + a journey index**. Never a cross-day merge.
- **Trek mode** (`"mode": "trek"`) — a *point-to-point* multi-day route (e.g. a Himalayan trek). The
  whole journey is **one continuous transect** (x = cumulative trail distance). A deliberate merge.

Every page carries an **observation map** below the profile (Leaflet + OpenTopoMap): the track, circular
photo markers, and **linked hover** — hover a profile point to highlight its map marker, and vice-versa.
The 科/屬 (family/genus) filter drives both views.

## Workflow: a complete journey from scratch / 從零做出一個完整旅程

A finished trek page has four sections — **地形/高程剖面圖** · **觀測點地圖** · **植群帶對照** (overseas
only) · **AI彙整，待查證** — and is listed on the landing page. Survey journeys (repeat visits to one path)
use steps 1, 3, 4 and 6.

### Inputs / 輸入

| Input | Required | Where it goes |
|---|---|---|
| iNaturalist account (`user_login`) · place (name or `place_id`) · dates `d1`–`d2` | ✅ | `journeys/<id>/config.json` |
| mode `trek` (point-to-point, one transect) or `survey` (same path, one transect per walk) | ✅ | config `mode` |
| taxonomy `auto` → `taicol` in Taiwan, `inat` elsewhere | ✅ (auto) | config `taxonomy` |
| title, e.g. `中央山脈南一段 2025 · South Section One` | optional | config `label` |
| per-day GPX files from the watch (trek) | recommended | merged → `journeys/<id>/track.gpx` |
| observations to drop (off-trail outliers, other trips, obscured coordinates) | as needed | config `scope.exclude_obs_ids` |
| the region's vegetation zones + a literature source (overseas) | overseas | `journeys/<id>/vegzones.json` |

### Process / 流程

1. **Scaffold the config** — Actions → **Create journey** (hosted form), or locally:
   ```bash
   python3 new_journey.py --user bunnytailgrass --place "Taiwan" --d1 2025-03-24 --d2 2025-03-28 \
       --mode trek --label "中央山脈南一段 2025 · South Section One"
   ```
   Place-name matches are ambiguous: the log lists candidate `place_id`s (Taiwan is `7887`) and
   off-trail outlier observations to pass back with `--exclude`.
2. **Attach the GPS track** (trek) — merge the per-day files, drop heart rate / cadence (the repo is
   public) and thin 1-second recordings, then add `"gpx": "track.gpx"` to the config:
   ```bash
   python3 merge_gpx.py D1.gpx D2.gpx … -o journeys/<id>/track.gpx --strip --every 5 --name "<label>"
   ```
3. **Generate the page** — `python3 generate.py --journey <id>` → `site/<id>/`. Check the
   `on GPX track: N by time, M by nearest point · offset …` line: a large offset or many nearest-point
   matches means a gap in the recording (e.g. a flat battery) or a misplaced observation. Obscured
   (sensitive-species) observations belong in `exclude_obs_ids`; re-run after any config change.
4. **Write the insights (AI彙整，待查證)**
   1. Gather the facts:
      ```bash
      python3 insights_data.py --journey <id> --zones 3300,3100,2500 --month 3
      ```
      The report groups observations by elevation zone × genus and lists each taxon's family, status
      (TaiCoL 特有 / IUCN / 紅皮書 / 原生·外來 in Taiwan; iNaturalist IUCN / national list / establishment
      means elsewhere), 花果期 peak months from iNaturalist *Flowers and Fruits* annotations, and what was in
      flower or fruit that month. It also lists excluded and obscured observations
      (full data: `caches/insights/<id>.json`).
   2. Curate `journeys/<id>/insights_spec.py` from the report: `KEY` (three findings, shown first),
      `HAB` (habitat × genus rows), `FAM` (科 · 屬 · 種 · 生態 · 花果期 · 狀態 rows) and an optional
      `HIDDEN` list for obscured observations. The format is documented in `build_insights.py`; copy an
      existing journey's spec as a template.
   3. Build the HTML fragment: `python3 build_insights.py --journey <id>` → `journeys/<id>/insights.html`
      (`--check` shows the diff without writing). Verify any claim the data does not show directly —
      the heading says 待查證 for a reason.
5. **Vegetation-zone comparison (植群帶對照, overseas only)** — write `journeys/<id>/vegzones.json`
   (Taiwan's zones per 蘇鴻傑 1984 and the region's, tree lines, axis, takeaway, source) and
   `vegzones.html` (3–5 differences from Taiwan), then draw the figure from the generated page's
   observation elevations:
   ```bash
   python3 vegzones.py --journey <id>     # needs matplotlib; writes journeys/<id>/vegzones.png
   ```
6. **Publish** — re-run `python3 generate.py --journey <id>` (inlines the insights, copies the PNG), then
   `python3 build_site_index.py`. Preview with `python3 -m http.server -d site`, and push to `main`: any
   change under `site/**` redeploys GitHub Pages. The hosted form does steps 1, 3 and 6 in one run.

### Outputs / 輸出

| File | Content |
|---|---|
| `journeys/<id>/config.json` · `track.gpx` | the journey's inputs (committed) |
| `journeys/<id>/insights_spec.py` → `insights.html` | curated insights: source data and the generated fragment |
| `journeys/<id>/vegzones.json` · `vegzones.html` · `vegzones.png` | overseas zone comparison: data, summary, figure |
| `site/<id>/index.html` | the self-contained page: profile + map (+ zones) + insights |
| `site/<id>/journey.json` | manifest: dates, days, points, species, km, peak, ascent, downsampled track |
| `site/index.html` | landing page: overview map of every track + list sortable by date / km / days / obs / spp |
| `caches/` (gitignored) | elevation, TaiCoL, iNaturalist taxa, phenology and per-journey insights data |

**Regenerate one journey** — `python3 generate.py --journey erge-2026-04-25`.

## Instances / 實例

| Journey | Mode | Summary |
|---|---|---|
| **二格山稜線 2026-04-25** | survey | 93 pts / 63 spp / 0.6 km（長期物候典藏另存於 `../2G 二格/iNAT in Erge/`） |
| **中央山脈南一段 2025 · South Section One** | trek + GPX | 5 days · 46 pts / 39 spp / 52.3 km / peak 3677 m |
| **中央山脈南二段 2024 · South Section Two** | trek + GPX | 8 days · 70 pts / 49 spp / 86.9 km / peak 3652 m |
| **中央山脈南三段 2025 · South Section Three** | trek + GPX | 8 days · 85 pts / 58 spp / 101.3 km / peak 3623 m (D6 morning and D8 after 11:36 not recorded: battery) |
| **路過島峰 2023 · Island Peak, Nepal** | trek + GPX | 11 days · 98 pts / 84 spp / 131.8 km / peak 6062 m · 植群帶對照 |
| **槍・穗高 2026 · Yari-Hotaka Circuit** | trek + GPX | 5 days · 89 pts / 72 spp / 53.0 km / peak 3189 m · 植群帶對照 |

## Status / 狀態

| Phase | Scope | Status |
|---|---|---|
| P1–P3 | fetch + walk segmentation · GPS-QA + SRTM elevation + along-track distance + taxonomy · transect HTML + journey index | ✅ |
| P4 | generalization: trek mode, overseas taxonomy (iNat), adaptive m↔km axis, global index, GitHub Pages | ✅ |
| Map | observation map (Leaflet + OpenTopoMap) below the transect · linked hover (map ↔ profile) | ✅ |
| Form | "Create journey" workflow_dispatch + `new_journey.py` scaffolder | ✅ |
| Map · GPX | optional `track.gpx` (trek): real route line, along-route distance + recorded elevation, obs placed by time · `merge_gpx.py` | ✅ |
| Sections | 地形/高程剖面圖 · 觀測點地圖 · 植群帶對照 (overseas, `vegzones.py`) · AI彙整，待查證 (`insights_data.py` → `insights_spec.py` → `build_insights.py`) | ✅ |

## Documentation

- **[ARCHITECTURE.md](ARCHITECTURE.md)** — modules, data flow, caching, deployment.
- **[DESIGN.md](DESIGN.md)** — the core principle and the design decisions behind each choice.
- **[SPEC.md](SPEC.md)** — config schema, output layout, and the create-journey form.
- **[CLAUDE.md](CLAUDE.md)** — working notes / conventions for the coding agent.

## Data sources & attribution

iNaturalist API (observations · places · taxa) · elevation SRTM 30 m via Open Topo Data · Taiwan
taxonomy TaiCoL 臺灣物種名錄 · phenology from iNaturalist *Flowers and Fruits*
annotations · basemap © OpenStreetMap, SRTM | © OpenTopoMap (CC-BY-SA) · charts Chart.js ·
maps Leaflet · photos from the iNaturalist CDN. Colours use a minimalist green palette.

🤖 Built with [Claude Code](https://claude.com/claude-code).
