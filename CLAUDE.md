# Expedition Story — CLAUDE.md

Generalized tool that turns an iNaturalist query (user × place × date-range) into a
vegetation **elevation-transect** site. Generalized from the 二格山 ridgeline transect.
SOW (荒野保護協會) tool.

## Core principle
The elevation transect is a **single-path** visualization (x = along-track distance on
ONE ordered walk). A date-range is a *selector*; the output depends on what the walks
are relative to each other:

- **Survey mode (default)** — repeated surveys of the *same* path (e.g. the 二格山 ridge
  revisited on different days). Output is **one transect per walk** + a journey index;
  **never a cross-day merge** (merging would overlay the same trail on itself).
- **Trek mode** (`"mode": "trek"`) — a *point-to-point* journey where consecutive days
  form **one continuous path** (e.g. a multi-day Himalayan trek). Here a cross-day merge
  is correct: all kept observations, time-ordered, become **one continuous transect**
  (x = cumulative trek distance). This is a deliberate, config-gated exception to the
  no-merge rule — only valid when the walks progress along a route, not retrace one.

If neither fits (scattered, non-path observations), use a map / elevation-distribution,
not a trail profile.

## Architecture
```
journeys/<id>/config.json   # per-journey input: user_login, place_id, d1, d2, walk_gap_min,
                            #   scope, snapshot, brand, mode("trek"?), taxonomy("inat"|"taicol")
lib/                        # shared engine
  walks.py                  # fetch(user,place,d1,d2) + segment(obs, gap_min) -> walks
  gps.py                    # accuracy-based QC: snap >100 m-accuracy fixes to time-interp position
  elevation.py              # SRTM 30 m (Open Topo Data, bilinear), cached
  taicol.py                 # Taiwan-scope: TaiCoL 中拉 family/genus + endemism/Red List, cached
  inat_taxa.py              # global-scope: family/genus (中拉) from iNat /v1/taxa ancestors, cached
  geo.py / profile.py       # haversine cumulative distance / per-walk point build
  render.py                 # transect HTML template (adaptive m↔km axis, optional nav, peak vs climb)
caches/                     # cross-journey shared: elevation.json, taicol.json, inat_taxa.json
generate.py --journey <id>  # config -> fetch -> segment -> per-walk render -> site/<id>/
site/<id>/journey.json      # walk manifest (P1)
site/<id>/<walk>/index.html # per-walk transect (P3); site/index.html lists journeys
```

## Phases
- **P1–P3 [done]** fetch + walk-segmentation, GPS-QA + SRTM elevation + along-track distance +
  TaiCoL, per-walk transect HTML + journey index. Baseline journey `erge-2026-04-25` reproduces
  the known 93 pts / 63 spp.
- **P4 [done]** generalization demos: (a) **trek mode** — `nepal-2023-trek` proves a point-to-point
  multi-day trek collapses to one continuous transect (103 pts, 161.8 km, 5628 m peak); added
  global `inat_taxa.py` (TaiCoL is Taiwan-only), adaptive m↔km axis, peak-vs-climb card.
- **Next** global `site/index.html` listing all journeys; GitHub repo + Pages.

## Reuse source (port, don't re-invent)
`../2G 二格/iNAT in Erge/` already has working: GPS correction (build_profile.py),
SRTM elevation (Open Topo Data), TaiCoL enrichment (taicol.py + shared cache), and the
transect template (build_transect_html.py: cards, 科/屬 filter, GPS-distance shapes,
photo tooltip, intersect:true hover). Port these into `lib/` parameterized by config.

## Conventions
- Brand = SOW palette (`../brand/sow_palette.css`): 荒野綠 #587A30 等. Minimalist, Noto Sans TC.
- Self-contained HTML (CDN Chart.js/fonts; data inlined; photos from iNat CDN).
- Taxonomy source by scope: `taicol` (Taiwan, adds 中文名 + 特有/保育) vs `inat` (anywhere else;
  family/genus 中拉 from iNat ancestors, no Taiwan endemism/Red-List badges). dates in CST (UTC+8).
- Walk segmentation: new walk on new calendar day OR intra-day gap > `walk_gap_min` (default 120 min).
  Trek mode ignores segmentation (whole journey = one path).
- Data is not always all-Plantae — an overseas trek logs mixed taxa (birds, mammals, fungi); the
  科/屬 filter and render are taxon-agnostic.
- Pure stdlib where possible; no secrets in repo.

## Run
```bash
python3 generate.py --journey erge-2026-04-25
```
