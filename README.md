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

## Add a journey / 新增旅程

- **Hosted form** — GitHub → **Actions** → **Create journey** → *Run workflow*. Fill in user, place
  (name or `place_id`), dates, and mode; it resolves the place, generates, commits, and deploys. The run
  log lists candidate place_ids and any off-trail outlier observations to exclude on a re-run.
- **Local CLI** — same scaffolder:
  ```bash
  python3 new_journey.py --user bunnytailgrass --place "Yushan" --d1 2024-10-05 --d2 2024-10-07 --mode trek
  python3 generate.py --journey <id>
  python3 build_site_index.py
  ```
- **Regenerate one** — `python3 generate.py --journey erge-2026-04-25`

Deployment is automatic: any push touching `site/**` redeploys GitHub Pages.

## Instances / 實例

| Journey | Mode | Summary |
|---|---|---|
| **二格山稜線 2026-04-25** | survey | 93 樣點 / 63 種（長期物候典藏另存於 `../2G 二格/iNAT in Erge/`） |
| **尼泊爾 2023 喜馬拉雅健行** | trek | 16-day query → one continuous transect · 103 pts / 87 spp / 161.8 km / peak 5628 m |

## Status / 狀態

| Phase | Scope | Status |
|---|---|---|
| P1–P3 | fetch + walk segmentation · GPS-QA + SRTM elevation + along-track distance + taxonomy · transect HTML + journey index | ✅ |
| P4 | generalization: trek mode, overseas taxonomy (iNat), adaptive m↔km axis, global index, GitHub Pages | ✅ |
| Map | observation map (Leaflet + OpenTopoMap) below the transect · linked hover (map ↔ profile) | ✅ |
| Form | "Create journey" workflow_dispatch + `new_journey.py` scaffolder | ✅ |
| Map · GPX | ingest an optional `track.gpx` for the real recorded route line (needs user-supplied GPX) | ⏳ |

## Documentation

- **[ARCHITECTURE.md](ARCHITECTURE.md)** — modules, data flow, caching, deployment.
- **[DESIGN.md](DESIGN.md)** — the core principle and the design decisions behind each choice.
- **[SPEC.md](SPEC.md)** — config schema, output layout, and the create-journey form.
- **[CLAUDE.md](CLAUDE.md)** — working notes / conventions for the coding agent.

## Data sources & attribution

iNaturalist API (observations · places · taxa) · elevation SRTM 30 m via Open Topo Data · Taiwan
taxonomy TaiCoL 臺灣物種名錄 · basemap © OpenStreetMap, SRTM | © OpenTopoMap (CC-BY-SA) · charts Chart.js ·
maps Leaflet · photos from the iNaturalist CDN. Colours use a minimalist green palette.

🤖 Built with [Claude Code](https://claude.com/claude-code).
