#!/usr/bin/env python3
"""Scaffold a new journey config from simple inputs — backs the "Create journey"
GitHub Actions form, and is runnable locally as a CLI.

  python3 new_journey.py --user bunnytailgrass --place Yushan \
      --d1 2024-10-05 --d2 2024-10-07 --mode trek

Resolves place_id (name or numeric), auto-picks taxonomy (taicol inside Taiwan,
else inat), derives an id/label, writes journeys/<id>/config.json, and prints a
walk/outlier probe. Emits `journey_id` to $GITHUB_OUTPUT when run in Actions.
The caller then runs generate.py --journey <id> + build_site_index.py.
"""
import argparse, json, os, re, sys, unicodedata, urllib.parse, urllib.request, statistics

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from lib import walks as W, geo

API = "https://api.inaturalist.org"


def _get(path):
    return json.load(urllib.request.urlopen(API + path, timeout=40))


def resolve_place(place):
    place = place.strip()
    if place.isdigit():
        rec = _get(f"/v1/places/{place}")["results"][0]
        return int(place), rec.get("display_name", place)
    res = _get("/v1/places/autocomplete?" + urllib.parse.urlencode({"q": place})).get("results", [])
    if not res:
        sys.exit(f"::error::no iNaturalist place matches {place!r}")
    print(f"place candidates for {place!r}:")
    for r in res[:6]:
        print(f"  {r['id']:>8}  {r.get('display_name', '')}")
    chosen = res[0]
    if len(res) > 1:  # name autocomplete is ambiguous — surface alternatives so the user can correct
        alts = ", ".join(f"{r['id']}={r.get('display_name', '').split(',')[0]}" for r in res[1:5])
        print(f"::warning::picked place_id {chosen['id']} ({chosen.get('display_name', '')}). "
              f"If that's the wrong place, re-run with place set to one of: {alts}")
    return chosen["id"], chosen.get("display_name", place)


def is_taiwan(display):
    return display.endswith(", TW") or "Taiwan" in display or "臺灣" in display or "台灣" in display


def slug(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode()
    return re.sub(r"[^a-zA-Z0-9]+", "-", s).strip("-").lower()


def probe(user, place_id, d1, d2):
    """Best-effort: report obs count, walk count, and geographic outlier candidates."""
    try:
        obs = W.fetch(user, place_id, d1, d2)
    except Exception as e:
        print(f"::warning::probe skipped ({e})")
        return
    geo_rows = [(o.get("id"), c[1], c[0]) for o in obs
                for c in [(o.get("geojson") or {}).get("coordinates")] if c]
    walks = W.segment(obs, 120)
    print(f"probe: {len(obs)} obs · {len(geo_rows)} geo-located · {len(walks)} walk(s) @gap120")
    if len(geo_rows) >= 4:
        clat = statistics.median(r[1] for r in geo_rows)
        clng = statistics.median(r[2] for r in geo_rows)
        outl = [(i, round(geo.hav(la, ln, clat, clng) / 1000, 1))
                for i, la, ln in geo_rows if geo.hav(la, ln, clat, clng) > 50000]
        if outl:
            ids = ",".join(str(i) for i, _ in outl)
            print(f"::warning::{len(outl)} obs >50 km off the main cluster (possible off-trail): "
                  + "; ".join(f"{i} ({d} km)" for i, d in outl)
                  + f". To drop them, re-run with exclude_ids={ids}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--user", required=True)
    ap.add_argument("--place", required=True, help="place name (resolved via iNat) or numeric place_id")
    ap.add_argument("--d1", required=True)
    ap.add_argument("--d2", required=True)
    ap.add_argument("--mode", choices=["trek", "survey"], default="trek")
    ap.add_argument("--taxonomy", choices=["auto", "inat", "taicol"], default="auto")
    ap.add_argument("--exclude", default="", help="comma-separated obs ids to drop")
    ap.add_argument("--label", default="")
    ap.add_argument("--id", default="", help="URL slug; derived if omitted")
    ap.add_argument("--gap", default="120", help="survey walk_gap_min")
    a = ap.parse_args()

    place_id, display = resolve_place(a.place)
    short = display.split(",")[0].strip()
    taxonomy = a.taxonomy if a.taxonomy != "auto" else ("taicol" if is_taiwan(display) else "inat")
    label = a.label.strip() or short
    base = slug(a.label) or slug(short) or f"place{place_id}"
    jid = a.id.strip() or f"{base}-{a.d1[:4]}-{a.mode}"
    exclude = [x.strip() for x in a.exclude.split(",") if x.strip()]

    cfg = {"id": jid, "label": label, "user_login": a.user, "place_id": place_id,
           "d1": a.d1, "d2": a.d2}
    if a.mode == "trek":
        cfg["mode"] = "trek"
    else:
        cfg["walk_gap_min"] = int(a.gap or 120)
    cfg["taxonomy"] = taxonomy
    if exclude:
        cfg["scope"] = {"exclude_obs_ids": exclude}

    jdir = os.path.join(HERE, "journeys", jid)
    os.makedirs(jdir, exist_ok=True)
    json.dump(cfg, open(os.path.join(jdir, "config.json"), "w"), ensure_ascii=False, indent=2)
    print(f"resolved place: {display} → place_id {place_id} · taxonomy={taxonomy} · mode={a.mode}")
    print(f"wrote journeys/{jid}/config.json")
    probe(a.user, place_id, a.d1, a.d2)

    gh = os.environ.get("GITHUB_OUTPUT")
    if gh:
        with open(gh, "a") as f:
            f.write(f"journey_id={jid}\n")


if __name__ == "__main__":
    main()
