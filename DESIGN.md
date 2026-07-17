# Design

This document records *why* the tool is shaped the way it is. Each section is a decision, its rationale,
and the trade-off accepted.

## Core principle

The elevation transect is a **single-path** visualization: `x` = along-track distance along **one ordered
walk**, `y` = elevation. A date-range is a *selector*, not automatically a single profile. What you do with
the selected observations depends on how the walks relate to each other:

- **Survey mode (default)** — repeated visits to the *same* path (the 二格山 ridge, revisited on different
  days). Output is **one transect per walk + a journey index**. Merging days would overlay the same trail
  on itself, which is meaningless — so **never a cross-day merge**.
- **Trek mode** (`"mode": "trek"`) — a *point-to-point* route where consecutive days form **one continuous
  path** (a multi-day Himalayan trek). Here a cross-day merge is exactly right: all observations, in time
  order, become **one continuous transect** (x = cumulative trek distance).

Trek mode is a **deliberate, config-gated exception** to the no-merge rule — valid only when the walks
*progress along a route*, not *retrace one*. This distinction is the central generalization insight: the
original tool assumed the survey case; a real trek forced the mode to be named explicitly rather than
letting a date-range silently decide.

If observations are neither a repeated survey nor a continuous route (scattered points), a trail profile is
the wrong tool — use a map or an elevation distribution instead.

## Walk segmentation

A new walk starts on a **new calendar day** or when the **intra-day time gap** exceeds `walk_gap_min`
(default 120 min). This generalizes the original ridge's single mid-day break. Trek mode ignores
segmentation entirely (the whole journey is one path).

**Trade-off:** sparse, bursty data (a casual trek logged as a few photos per day) over-segments into
degenerate 1–2 point "walks". Trek mode sidesteps this by not segmenting; for surveys, tiny walks are a
known rough edge.

## GPS quality control is accuracy-based, not distance-based

`gps.correct` only touches fixes whose `positional_accuracy > 100 m`, snapping them to the
time-interpolated position between their nearest reliable neighbours. It deliberately does **not** treat a
large jump between points as an error.

This is what lets the same QC generalize from a dense 100-point ridge (points metres apart) to a trek
(points kilometres apart): on a trek, consecutive observations *are* far apart and must be left alone. A
distance-based "de-jitter" would have mangled every trek leg. Interpolated points are flagged (`fl`) and
drawn distinctly so the correction is visible, not hidden.

## Taxonomy: Taiwan vs the world

Family/genus enrichment has two sources, chosen per journey by `config.taxonomy`:

- **`taicol`** — the Taiwan Catalogue of Life. Adds Chinese names *and* Taiwan endemism + IUCN/Red-List
  status. Correct and richer **inside Taiwan**.
- **`inat`** — family/genus read from each taxon's `/v1/taxa` ancestors on iNaturalist. The global
  authority, and it's already our data source.

TaiCoL is Taiwan-scoped: for an overseas journey it returns nothing *and* would hammer the Taiwan API once
per unknown species. So overseas journeys use `inat`. The `new_journey.py` scaffolder auto-selects: Taiwan
place → `taicol`, else `inat`. The endemism/Red-List badges are Taiwan concepts and simply don't render for
`inat` journeys.

## It's biodiversity, not just vegetation

The original tool was framed as a "vegetation" transect (the ridge was all Plantae). A real trek logs
**mixed taxa** — birds, mammals, fungi, butterflies. The family/genus filter and the render are therefore
**taxon-agnostic**: any iNaturalist observation with coordinates is a point on the profile and a marker on
the map. The framing shifted from *vegetation* to *biodiversity*.

## Adaptive scale & the summary cards

- The x-axis switches from **metres to kilometres** at ≥ 2 km, so a 636 m ridge and a 162 km trek both read
  cleanly with the same code.
- Card 6 is **mode-aware**: a survey shows **net climb** (start → end of a there-and-back-along-a-ridge
  walk); a trek shows **peak elevation + total ascent**, because net start→end is ~0 for an out-and-back
  and badly undersells a climb to 5600 m.

## Off-trail outliers are surfaced, never auto-removed

Treks often include stray observations far from the route (a transit point, a return to the capital). These
would blow out the x-axis and the map. The tool **flags** candidates (`new_journey.py` warns about points
> 50 km from the cluster) but only excludes what the config's `scope.exclude_obs_ids` names. Removing data
is the author's explicit choice, made by re-running with the flagged IDs — never a silent heuristic.

## Self-contained pages

Each page inlines its data and pulls only libraries (Chart.js, Leaflet), map tiles, and photos over the
network. Benefits: no build step, every page is one portable file, and it works on plain static hosting.
**Trade-off:** the page needs network at view time for tiles/photos (the same model the original chart
already used for its CDN scripts).

## The observation map is an MVP: obs-points, not a GPX route

The orange track line connects observations **in time order** — it is *not* a recorded GPS track. On a
dense ridge it looks like the trail; on a sparse trek you see straight "shortcut" segments cutting across
terrain. This is an accepted MVP limitation, stated on the page and in the docs. The honest fix is **Tier 2
(ingest an optional `track.gpx`)**, which also makes the transect's distance axis accurate — but it needs a
user-supplied GPX, so it's deferred rather than faked.

Basemap is **OpenTopoMap** (free, contour aesthetic matching a Strava-style map, CC-BY-SA) rather than a
keyed provider, to keep the tool dependency-free.

## Linked hover shares one array

Because the chart and the map render the *same* ordered point array, linking is by **index** — no fragile
coordinate matching. Hovering either view drives the other; the hovered map marker is raised above its
neighbours so it isn't hidden in dense clusters. It's a desktop hover feature; touch (tap → popup/card) is
unaffected.

## No backend: static site + a workflow form

The published site is static, so a "create a journey" form *on the website* is impossible — generation must
run Python, hit APIs, write files, and push. The UI is therefore a **GitHub Actions `workflow_dispatch`
form**: it runs the real pipeline in CI and auto-deploys, needs zero local setup, and works from anywhere
(including a phone). The trade-off is GitHub's generic inputs form rather than a custom-styled page; the
same `new_journey.py` scaffolder also runs locally as a CLI for those who prefer it.

## Caching

`caches/` holds cross-journey elevation, TaiCoL, and iNat-taxa results keyed by coordinate / species / taxon
id. Regeneration only hits the network for *new* coordinates and taxa, so re-running a journey (or adding a
nearby one) is cheap. Caches are gitignored — they're derived data, rebuilt on demand (including on a fresh
CI runner).

## Branding

Built originally for a conservation NGO; its green palette is kept for visual continuity, but the
organization name was removed from every rendered page at the owner's request. The colours are just colours
now — no attribution text.
