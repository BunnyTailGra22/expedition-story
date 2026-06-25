#!/usr/bin/env python3
"""Expedition Story — turn an iNaturalist query (user × place × date-range) into a
vegetation elevation-transect site. Each contiguous walk → one transect HTML;
a journey index links them.

Usage:  python3 generate.py --journey <id>   # reads journeys/<id>/config.json
"""
import argparse, json, os, sys, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from lib import walks as W, profile as P, taicol as T, render as R, inat_taxa as IT

CACHE = os.path.join(HERE, "caches")
BR = {"green": "#587A30", "gray": "#666", "gray2": "#B2B2B2"}


def journey_index_html(cfg, walks):
    q = cfg
    rows = "".join(
        f'<li><a href="{w["walk_id"]}/index.html">{w["date"]} · {w["start"]}–{w["end"]}'
        f' · {w["n"]} 觀察 · {w["species"]} 種</a></li>' for w in walks)
    return f"""<!DOCTYPE html><html lang="zh-Hant"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{cfg['label']} · 旅程索引</title>
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@400;500;700&display=swap" rel="stylesheet">
<style>body{{margin:0;background:#fff;color:#3a3a36;font-family:"Noto Sans TC",system-ui,sans-serif}}
.wrap{{max-width:760px;margin:0 auto;padding:44px 26px}}
.nav{{font-size:13px;margin:0 0 14px}}.nav a{{color:{BR['green']};text-decoration:none}}
h1{{color:{BR['green']};font-weight:700;font-size:24px;margin:0 0 4px}}
.sub{{color:{BR['gray']};font-size:14px;margin:0 0 22px}}
ul{{list-style:none;padding:0;margin:0}}
li{{border:0.5px solid {BR['gray2']};border-radius:10px;margin-bottom:10px}}
li a{{display:block;padding:14px 16px;color:#3a3a36;text-decoration:none}}
li a:hover{{background:#f5f4ef;color:{BR['green']}}}
.foot{{margin-top:24px;font-size:11.5px;color:{BR['gray2']}}}</style></head><body><div class="wrap">
<div class="nav"><a href="../index.html">← 所有旅程 all journeys</a></div>
<h1>{cfg['label']}</h1>
<p class="sub">{q['user_login']} · place_id {q['place_id']} · {q['d1']}–{q['d2']} · {len(walks)} 趟 walks（依時間自動分段）</p>
<ul>{rows}</ul>
<p class="foot">Expedition Story · 資料來源 iNaturalist · 海拔 SRTM 30 m · 學名 TaiCoL。</p>
</div></body></html>"""


def enrich_points(pts, cfg):
    """Attach famSci/famZh/genSci/genZh/end/threat to each point. Taxonomy source
    follows cfg['taxonomy']: 'inat' (global, family from iNat ancestors) or the
    default 'taicol' (Taiwan-scope: adds 中文名 + 特有/保育)."""
    if cfg.get("taxonomy") == "inat":
        tx = IT.enrich([p.get("tid") for p in pts], os.path.join(CACHE, "inat_taxa.json"))
        for p in pts:
            e = tx.get(str(p.get("tid")), {})
            p["famSci"] = e.get("fam_sci") or "?"
            p["famZh"] = e.get("fam_zh") or ""
            p["genSci"] = e.get("gen_sci") or ((p["s"] or "?").split(" ")[0])
            p["genZh"] = e.get("gen_zh") or ""
            p["end"] = False
            p["threat"] = None
    else:
        species = {p["s"]: p["c"] for p in pts if p["s"]}
        tx = T.enrich(species, os.path.join(CACHE, "taicol.json"))
        for p in pts:
            e = tx.get(p["s"], {})
            p["famSci"] = e.get("fam_sci") or "?"
            p["famZh"] = e.get("fam_zh") or ""
            p["genSci"] = e.get("gen_sci") or ((p["s"] or "?").split(" ")[0])
            p["genZh"] = e.get("gen_zh") or ""
            p["end"] = bool(e.get("is_endemic"))
            p["threat"] = e.get("threat")


def run_trek(cfg, obs, out):
    """Trek mode: the whole multi-day journey is ONE continuous path → a single
    elevation transect (x = cumulative along-track distance over the whole trek).
    Deliberately overrides the per-walk 'no cross-day merge' rule for point-to-point
    treks (see CLAUDE.md)."""
    pts = P.build(obs, cfg.get("scope"), CACHE)
    if not pts:
        print(f"{cfg['label']}: no usable points after scope.")
        return
    enrich_points(pts, cfg)
    ex = set((cfg.get("scope") or {}).get("exclude_obs_ids", []))
    dts = sorted(t for t in (W._t(o) for o in obs if str(o.get("id")) not in ex) if t)
    d0, d1 = dts[0].strftime("%Y-%m-%d"), dts[-1].strftime("%Y-%m-%d")
    ndays = len({t.date() for t in dts})
    nsp = len({p["s"] for p in pts})
    ys, km = [p["y"] for p in pts], pts[-1]["x"] / 1000
    meta = {"title": cfg["label"],
            "subtitle": f"{d0} – {d1} · {ndays} 天 · {len(pts)} 樣點 · {nsp} 種 · "
                        f"連續路徑剖面 single continuous transect",
            "user": cfg["user_login"], "place_id": cfg["place_id"],
            "snapshot": cfg.get("snapshot"), "trek": True,
            "taxonomy": cfg.get("taxonomy")}
    open(os.path.join(out, "index.html"), "w").write(R.transect_html(meta, pts))
    json.dump({"id": cfg["id"], "label": cfg["label"], "mode": "trek",
               "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
               "d1": d0, "d2": d1, "days": ndays, "points": len(pts), "species": nsp,
               "trail_km": round(km, 1), "peak_m": round(max(ys)), "low_m": round(min(ys)),
               "climb_m": round(pts[-1]["y"] - pts[0]["y"])},
              open(os.path.join(out, "journey.json"), "w"), ensure_ascii=False, indent=2)
    print(f"{cfg['label']}: {len(obs)} obs → 1 continuous transect → site/{cfg['id']}/")
    print(f"  {d0}–{d1} · {ndays} 天 · {len(pts)} pts · {nsp} spp · "
          f"{km:.1f} km · {round(pts[0]['y'])}→{round(pts[-1]['y'])} m")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--journey", required=True)
    jid = ap.parse_args().journey
    cfg = json.load(open(os.path.join(HERE, "journeys", jid, "config.json")))

    obs = W.fetch(cfg["user_login"], cfg["place_id"], cfg["d1"], cfg["d2"])
    out = os.path.join(HERE, "site", cfg["id"])
    os.makedirs(out, exist_ok=True)

    if cfg.get("mode") == "trek":
        run_trek(cfg, obs, out)
        return

    walks = W.segment(obs, cfg.get("walk_gap_min", 120))
    seen, index = {}, []
    for w in walks:
        pts = P.build(w["obs"], cfg.get("scope"), CACHE)
        if not pts:
            continue
        enrich_points(pts, cfg)
        wid = w["date"]
        seen[wid] = seen.get(wid, 0) + 1
        if seen[wid] > 1:
            wid = f"{wid}-{seen[wid]}"
        nsp = len({p["s"] for p in pts})
        meta = {"title": f"{cfg['label']} · {wid}",
                "subtitle": f"{w['date']} 踏查 · {w['start']}–{w['end']} · {len(pts)} 樣點 · {nsp} 種",
                "user": cfg["user_login"], "place_id": cfg["place_id"], "snapshot": cfg.get("snapshot")}
        wdir = os.path.join(out, wid)
        os.makedirs(wdir, exist_ok=True)
        open(os.path.join(wdir, "index.html"), "w").write(R.transect_html(meta, pts))
        index.append({"walk_id": wid, "date": w["date"], "start": w["start"],
                      "end": w["end"], "n": len(pts), "species": nsp})

    open(os.path.join(out, "index.html"), "w").write(journey_index_html(cfg, index))
    json.dump({"id": cfg["id"], "label": cfg["label"], "generated_at":
               datetime.datetime.now().isoformat(timespec="seconds"), "walks": index},
              open(os.path.join(out, "journey.json"), "w"), ensure_ascii=False, indent=2)

    print(f"{cfg['label']}: {len(obs)} obs → {len(index)} transect(s) → site/{cfg['id']}/")
    for w in index:
        print(f"  {w['walk_id']}  {w['start']}–{w['end']}  ·  {w['n']:>3} pts  ·  {w['species']} spp")


if __name__ == "__main__":
    main()
