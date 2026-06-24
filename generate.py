#!/usr/bin/env python3
"""Expedition Story — turn an iNaturalist query (user × place × date-range) into
a vegetation elevation-transect site. Each contiguous *walk* becomes one
transect; a journey index links them.

Usage:  python3 generate.py --journey <id>        # reads journeys/<id>/config.json

Pipeline (phased):
  P1 [done]  fetch + segment into walks                     -> site/<id>/journey.json
  P2 [todo]  per walk: GPS-QA + SRTM elevation + along-track distance + TaiCoL
  P3 [todo]  render per-walk transect HTML + journey index  -> site/<id>/<walk>/index.html
"""
import argparse, json, os, sys, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from lib import walks as W


def load_config(jid):
    p = os.path.join(HERE, "journeys", jid, "config.json")
    if not os.path.exists(p):
        sys.exit(f"no config: journeys/{jid}/config.json")
    return json.load(open(p))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--journey", required=True, help="journey id under journeys/")
    cfg = load_config(ap.parse_args().journey)

    obs = W.fetch(cfg["user_login"], cfg["place_id"], cfg["d1"], cfg["d2"])
    walks = W.segment(obs, cfg.get("walk_gap_min", 120))

    out = os.path.join(HERE, "site", cfg["id"])
    os.makedirs(out, exist_ok=True)
    wsum = []
    for w in walks:
        sp = len({(o.get("taxon") or {}).get("id") for o in w["obs"] if o.get("taxon")})
        wsum.append({"walk_id": w["date"], "date": w["date"], "start": w["start"],
                     "end": w["end"], "span_min": w["span_min"], "n": w["n"], "species": sp})
    manifest = {"id": cfg["id"], "label": cfg.get("label"),
                "query": {k: cfg[k] for k in ("user_login", "place_id", "d1", "d2")},
                "walk_gap_min": cfg.get("walk_gap_min", 120),
                "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
                "walks": wsum}
    json.dump(manifest, open(os.path.join(out, "journey.json"), "w"), ensure_ascii=False, indent=2)

    print(f"{cfg.get('label')}: {len(obs)} obs → {len(walks)} walk(s) → site/{cfg['id']}/journey.json")
    for w in wsum:
        print(f"  {w['date']}  {w['start']}–{w['end']}  ·  {w['n']:>3} obs  ·  {w['species']} spp")
    print("\nnext (P2/P3): per-walk GPS-QA + SRTM elevation + along-track distance + TaiCoL"
          " → transect HTML + journey index.")


if __name__ == "__main__":
    main()
