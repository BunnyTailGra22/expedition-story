#!/usr/bin/env python3
"""Expedition Story — turn an iNaturalist query (user × place × date-range) into a
vegetation elevation-transect site. Each contiguous walk → one transect HTML;
a journey index links them.

Usage:  python3 generate.py --journey <id>   # reads journeys/<id>/config.json
"""
import argparse, json, os, sys, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from lib import walks as W, profile as P, taicol as T, render as R

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
h1{{color:{BR['green']};font-weight:700;font-size:24px;margin:0 0 4px}}
.sub{{color:{BR['gray']};font-size:14px;margin:0 0 22px}}
ul{{list-style:none;padding:0;margin:0}}
li{{border:0.5px solid {BR['gray2']};border-radius:10px;margin-bottom:10px}}
li a{{display:block;padding:14px 16px;color:#3a3a36;text-decoration:none}}
li a:hover{{background:#f5f4ef;color:{BR['green']}}}
.foot{{margin-top:24px;font-size:11.5px;color:{BR['gray2']}}}</style></head><body><div class="wrap">
<h1>{cfg['label']}</h1>
<p class="sub">{q['user_login']} · place_id {q['place_id']} · {q['d1']}–{q['d2']} · {len(walks)} 趟 walks（依時間自動分段）</p>
<ul>{rows}</ul>
<p class="foot">Expedition Story · 資料來源 iNaturalist · 海拔 SRTM 30 m · 學名 TaiCoL · 色彩 荒野保護協會。</p>
</div></body></html>"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--journey", required=True)
    jid = ap.parse_args().journey
    cfg = json.load(open(os.path.join(HERE, "journeys", jid, "config.json")))

    obs = W.fetch(cfg["user_login"], cfg["place_id"], cfg["d1"], cfg["d2"])
    walks = W.segment(obs, cfg.get("walk_gap_min", 120))
    out = os.path.join(HERE, "site", cfg["id"])
    os.makedirs(out, exist_ok=True)

    seen, index = {}, []
    for w in walks:
        pts = P.build(w["obs"], cfg.get("scope"), CACHE)
        if not pts:
            continue
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
