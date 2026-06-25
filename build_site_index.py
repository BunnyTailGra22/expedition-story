#!/usr/bin/env python3
"""Build site/index.html — the global landing page listing every journey, read
from each site/<id>/journey.json. SOW brand; matches the per-journey index style.
Run after generate.py. Usage: python3 build_site_index.py"""
import json, glob, os

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "site")
BR = {"green": "#587A30", "gray": "#666", "gray2": "#B2B2B2"}


def entry(j):
    jid = j["id"]
    if j.get("mode") == "trek":
        tag = "健行 trek"
        stat = (f'{j["d1"]}–{j["d2"]} · {j["days"]} 天 · {j["points"]} 樣點 · {j["species"]} 種 · '
                f'{j["trail_km"]} km · 最高 {j.get("peak_m", "?")} m')
    else:
        walks = j.get("walks", [])
        npts = sum(w["n"] for w in walks)
        nsp = sum(w["species"] for w in walks)
        tag = "踏查 survey"
        d = f'{walks[0]["date"]}–{walks[-1]["date"]}' if walks else ""
        stat = f'{d} · {len(walks)} 趟 walks · {npts} 樣點 · {nsp} 物種觀察'
    return (f'<li><a href="{jid}/index.html"><span class="tag">{tag}</span>'
            f'<span class="nm">{j["label"]}</span><span class="st">{stat}</span></a></li>')


def main():
    journeys = [json.load(open(p)) for p in sorted(glob.glob(os.path.join(SITE, "*", "journey.json")))]
    # treks first, then surveys; each by id
    journeys.sort(key=lambda j: (j.get("mode") != "trek", j["id"]))
    rows = "".join(entry(j) for j in journeys)
    html = f"""<!DOCTYPE html><html lang="zh-Hant"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Expedition Story · 旅程總覽</title>
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@400;500;700&display=swap" rel="stylesheet">
<style>body{{margin:0;background:#fff;color:#3a3a36;font-family:"Noto Sans TC",system-ui,sans-serif}}
.wrap{{max-width:760px;margin:0 auto;padding:48px 26px}}
h1{{color:{BR['green']};font-weight:700;font-size:26px;margin:0 0 4px}}
.sub{{color:{BR['gray']};font-size:14px;margin:0 0 26px;line-height:1.6}}
ul{{list-style:none;padding:0;margin:0}}
li{{border:0.5px solid {BR['gray2']};border-radius:10px;margin-bottom:12px}}
li a{{display:block;padding:16px 18px;color:#3a3a36;text-decoration:none}}
li a:hover{{background:#f5f4ef}}
.tag{{display:inline-block;font-size:11px;color:{BR['green']};border:0.5px solid {BR['green']};border-radius:20px;padding:2px 9px;margin-right:8px;vertical-align:middle}}
.nm{{font-size:17px;font-weight:500;color:{BR['green']}}}
.st{{display:block;font-size:13px;color:{BR['gray']};margin-top:5px}}
.foot{{margin-top:28px;font-size:11.5px;color:{BR['gray2']};line-height:1.7}}</style></head><body><div class="wrap">
<h1>Expedition Story</h1>
<p class="sub">把任一段 iNaturalist 踏查（使用者 × 地點 × 日期區間）自動產成植被／生物多樣性海拔剖面圖。<br>
共 {len(journeys)} 趟旅程。</p>
<ul>{rows}</ul>
<p class="foot">資料來源 iNaturalist · 海拔 SRTM 30 m · 學名 TaiCoL（臺灣）／ iNaturalist（海外）。</p>
</div></body></html>"""
    open(os.path.join(SITE, "index.html"), "w").write(html)
    print(f"site/index.html ← {len(journeys)} journeys: " + ", ".join(j["id"] for j in journeys))


if __name__ == "__main__":
    main()
