# Expedition Story — CLAUDE.md

Generalized tool that turns an iNaturalist query (user × place × date-range) into a
vegetation **elevation-transect** site. Generalized from the 二格山 ridgeline transect.
SOW (荒野保護協會) tool.

## Core principle (don't violate)
The elevation transect is a **single-path** visualization (x = along-track distance on
ONE ordered walk). A date-range is a *selector*, not a single profile → output is
**one transect per walk**, never a cross-day merge. If a true multi-day aggregate is
ever needed, use a map / elevation-distribution, not a trail profile.

## Architecture
```
journeys/<id>/config.json   # per-journey input: user_login, place_id, d1, d2, walk_gap_min, scope, snapshot, brand
lib/                        # shared engine
  walks.py                  # fetch(user,place,d1,d2) + segment(obs, gap_min) -> walks   [DONE]
  (todo) gps_qa.py          # sort-by-time, jump detect, >100 m neighbour interpolation
  (todo) elevation.py       # SRTM 30 m (Open Topo Data), cached
  (todo) taicol.py          # TaiCoL name/family·genus 中拉/endemism/Red List, cached
  (todo) track.py           # cumulative along-track distance
  (todo) templates/         # transect HTML template (port from erge-iNAT build_transect_html.py)
caches/                     # cross-journey shared: elevation, taicol, photos
generate.py --journey <id>  # config -> fetch -> segment -> per-walk render -> site/<id>/
site/<id>/journey.json      # walk manifest (P1)
site/<id>/<walk>/index.html # per-walk transect (P3); site/index.html lists journeys
```

## Phases
- **P1 [done]** `lib/walks.py` + `generate.py` write `site/<id>/journey.json` (walk manifest).
- **P2** port GPS-QA + elevation + along-track distance + TaiCoL into `lib/` (reuse erge-iNAT logic).
- **P3** render per-walk transect HTML + journey index; deploy (GitHub Pages).
- **P4** migrate 二格山 2026-04-25 to be journey #1 here; its long-term phenology archive stays in `../2G 二格/iNAT in Erge/`.

## Reuse source (port, don't re-invent)
`../2G 二格/iNAT in Erge/` already has working: GPS correction (build_profile.py),
SRTM elevation (Open Topo Data), TaiCoL enrichment (taicol.py + shared cache), and the
transect template (build_transect_html.py: cards, 科/屬 filter, GPS-distance shapes,
photo tooltip, intersect:true hover). Port these into `lib/` parameterized by config.

## Conventions
- Brand = SOW palette (`../brand/sow_palette.css`): 荒野綠 #587A30 等. Minimalist, Noto Sans TC.
- Self-contained HTML (CDN Chart.js/fonts; data inlined; photos from iNat CDN).
- 中文 family/genus from TaiCoL; dates in CST (UTC+8).
- Walk segmentation: new walk on new calendar day OR intra-day gap > `walk_gap_min` (default 120 min).
- Pure stdlib where possible; no secrets in repo.

## Run
```bash
python3 generate.py --journey erge-2026-04-25
```
