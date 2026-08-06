#!/usr/bin/env python3
"""Build site/index.html — the global landing page listing every journey, read
from each site/<id>/journey.json. SOW brand; matches the per-journey index style.

The page has two views of the same set: an overview map (OpenTopoMap) drawing
every journey's track, each clickable through to its page, and a list that can be
sorted by date / distance / days / observations / species. Hovering either one
highlights the other. Run after generate.py. Usage: python3 build_site_index.py"""
import json, glob, os

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "site")
BR = {"green": "#587A30", "gray": "#666", "gray2": "#B2B2B2"}
# one colour per journey so the overview map's tracks stay tellable apart
PAL = ["#587A30", "#FC5200", "#2E6F8F", "#90B821", "#8A5A2B", "#7A3E6E"]

SORTS = [("date", "日期 date"), ("km", "距離 distance"), ("days", "天數 days"),
         ("obs", "觀察數 observations"), ("spp", "物種數 species")]


def summarize(j):
    """One journey's comparable numbers, whichever mode wrote the manifest."""
    walks = j.get("walks", [])
    trek = j.get("mode") == "trek"
    d1 = j.get("d1") or (walks[0]["date"] if walks else "")
    d2 = j.get("d2") or (walks[-1]["date"] if walks else "")
    return {
        "id": j["id"], "label": j["label"], "trek": trek,
        "tag": "健行 trek" if trek else "踏查 survey",
        "d1": d1, "d2": d2,
        "days": j.get("days") or len({w["date"] for w in walks}),
        "walks": len(walks),
        "obs": j.get("points") or sum(w["n"] for w in walks),
        "spp": j.get("species") or sum(w["species"] for w in walks),
        "km": j.get("trail_km"), "peak": j.get("peak_m"),
        "track": j.get("track") or [],
    }


def stat_line(s):
    bits = [f'{s["d1"]}–{s["d2"]}']
    bits.append(f'{s["days"]} 天' if s["trek"] else f'{s["walks"]} 趟 walks')
    bits += [f'{s["obs"]} 樣點', f'{s["spp"]} 種']
    if s["km"] is not None:
        bits.append(f'{s["km"]} km')
    if s["peak"] is not None:
        bits.append(f'最高 {s["peak"]} m')
    return " · ".join(bits)


def entry(s, i):
    return (f'<li data-id="{s["id"]}" data-i="{i}" data-date="{s["d1"]}" '
            f'data-km="{s["km"] if s["km"] is not None else -1}" data-days="{s["days"]}" '
            f'data-obs="{s["obs"]}" data-spp="{s["spp"]}">'
            f'<a href="{s["id"]}/index.html"><span class="tag" style="color:{PAL[i % len(PAL)]};'
            f'border-color:{PAL[i % len(PAL)]}">{s["tag"]}</span>'
            f'<span class="nm">{s["label"]}</span>'
            f'<span class="st">{stat_line(s)}</span></a></li>')


def main():
    journeys = [json.load(open(p)) for p in sorted(glob.glob(os.path.join(SITE, "*", "journey.json")))]
    journeys.sort(key=lambda j: (j.get("mode") != "trek", j["id"]))
    S = [summarize(j) for j in journeys]
    rows = "".join(entry(s, i) for i, s in enumerate(S))
    btns = "".join(f'<button type="button" data-k="{k}"{" class=on" if k == "date" else ""}>{lbl}</button>'
                   for k, lbl in SORTS)
    mapdata = json.dumps([{"id": s["id"], "label": s["label"], "stat": stat_line(s),
                           "c": PAL[i % len(PAL)], "track": s["track"]}
                          for i, s in enumerate(S)], ensure_ascii=False)
    html = f"""<!DOCTYPE html><html lang="zh-Hant"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Expedition Story · 旅程總覽</title>
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@400;500;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>body{{margin:0;background:#fff;color:#3a3a36;font-family:"Noto Sans TC",system-ui,sans-serif}}
.wrap{{max-width:880px;margin:0 auto;padding:48px 26px}}
h1{{color:{BR['green']};font-weight:700;font-size:26px;margin:0 0 4px}}
.sub{{color:{BR['gray']};font-size:14px;margin:0 0 22px;line-height:1.6}}
.mapbox{{position:relative;height:430px;border:0.5px solid {BR['gray2']};border-radius:12px;overflow:hidden;margin:0 0 22px}}
#map{{width:100%;height:100%;background:#eee}}
.sortbar{{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:0 0 12px;font-size:12px;color:{BR['gray2']}}}
.sortbar span{{margin-right:2px}}
.sortbar button{{font-family:inherit;font-size:12px;color:{BR['gray']};background:#fff;border:0.5px solid {BR['gray2']};border-radius:20px;padding:5px 12px;cursor:pointer}}
.sortbar button:hover{{background:#f5f4ef}}
.sortbar button.on{{color:#fff;background:{BR['green']};border-color:{BR['green']}}}
ul{{list-style:none;padding:0;margin:0}}
li{{border:0.5px solid {BR['gray2']};border-radius:10px;margin-bottom:12px}}
li a{{display:block;padding:16px 18px;color:#3a3a36;text-decoration:none}}
li a:hover,li.hi a{{background:#f5f4ef}}
.tag{{display:inline-block;font-size:11px;color:{BR['green']};border:0.5px solid {BR['green']};border-radius:20px;padding:2px 9px;margin-right:8px;vertical-align:middle}}
.nm{{font-size:17px;font-weight:500;color:{BR['green']}}}
.st{{display:block;font-size:13px;color:{BR['gray']};margin-top:5px}}
.leaflet-popup-content{{font-family:"Noto Sans TC",system-ui,sans-serif;margin:10px 12px}}
.pp .nm{{font-size:15px}}.pp .st{{font-size:12px}}
.pp a{{display:inline-block;margin-top:6px;color:{BR['green']};font-weight:500;text-decoration:none;font-size:12px}}
.foot{{margin-top:28px;font-size:11.5px;color:{BR['gray2']};line-height:1.7}}
@media(max-width:760px){{.wrap{{padding:28px 16px}}.mapbox{{height:320px}}}}</style></head><body><div class="wrap">
<h1>Expedition Story</h1>
<p class="sub">把任一段 iNaturalist 踏查（使用者 × 地點 × 日期區間）自動產成植被／生物多樣性海拔剖面圖。<br>
共 {len(S)} 趟旅程。地圖：點選路線或標記開啟該趟旅程。</p>
<div class="mapbox"><div id="map"></div></div>
<div class="sortbar"><span>排序 sort by</span>{btns}</div>
<ul id="list">{rows}</ul>
<p class="foot">資料來源 iNaturalist · 海拔 SRTM 30 m · 學名 TaiCoL（臺灣）／ iNaturalist（海外）。</p>
</div>
<script>
var J={mapdata};
var lmap, lines=[], SORT='date', DIR=-1;      // date starts newest-first
function num(li,k){{return parseFloat(li.getAttribute('data-'+k));}}
function sortList(k){{
  var ul=document.getElementById('list'),items=[].slice.call(ul.children);
  items.sort(function(a,b){{
    var va=k==='date'?a.getAttribute('data-date'):num(a,k),
        vb=k==='date'?b.getAttribute('data-date'):num(b,k);
    return (va<vb?-1:va>vb?1:0)*DIR;
  }});
  items.forEach(function(li){{ul.appendChild(li);}});
}}
function paintSort(){{                              // arrow only on the active key
  [].forEach.call(document.querySelectorAll('.sortbar button'),function(o){{
    var on=o.getAttribute('data-k')===SORT;
    o.className=on?'on':'';
    o.textContent=o.getAttribute('data-lbl')+(on?(DIR<0?' ↓':' ↑'):'');
  }});
}}
function initSort(){{
  [].forEach.call(document.querySelectorAll('.sortbar button'),function(b){{
    b.setAttribute('data-lbl',b.textContent);
    b.onclick=function(){{
      var k=b.getAttribute('data-k');
      DIR=(k===SORT)?-DIR:-1;                     // a new key starts biggest / newest first
      SORT=k;paintSort();sortList(k);
    }};
  }});
  paintSort();sortList('date');
}}
function popupHtml(j){{
  return '<div class="pp"><div class="nm" style="color:'+j.c+'">'+j.label+'</div>'+
         '<div class="st">'+j.stat+'</div>'+
         '<a href="'+j.id+'/index.html">開啟旅程 open →</a></div>';
}}
function highlight(i,on){{
  var g=lines[i]; if(!g)return;
  g.forEach(function(p){{p.setStyle({{weight:on?7:4,opacity:on?1:0.85}});}});
  var li=document.querySelector('li[data-i="'+i+'"]');
  if(li)li.className=on?'hi':'';
}}
function initMap(){{
  if(!window.L){{setTimeout(initMap,80);return;}}
  lmap=L.map('map',{{scrollWheelZoom:true}});
  var bTopo=L.tileLayer('https://{{s}}.tile.opentopomap.org/{{z}}/{{x}}/{{y}}.png',
        {{maxZoom:17,attribution:'© OpenStreetMap、SRTM ｜ © OpenTopoMap (CC-BY-SA)'}}),
      bOsm=L.tileLayer('https://tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png',
        {{maxZoom:19,attribution:'© OpenStreetMap contributors'}}),
      bLight=L.tileLayer('https://{{s}}.basemaps.cartocdn.com/light_all/{{z}}/{{x}}/{{y}}{{r}}.png',
        {{maxZoom:19,subdomains:'abcd',attribution:'© OpenStreetMap contributors ｜ © CARTO'}});
  bTopo.addTo(lmap);
  L.control.layers({{'地形 topo':bTopo,'街道 OSM':bOsm,'淺色 light':bLight}},null,{{position:'bottomright'}}).addTo(lmap);
  var all=[];
  J.forEach(function(j,i){{
    var segs=[];
    (j.track||[]).forEach(function(t){{
      if(!t.length)return;
      all=all.concat(t);
      var pl=L.polyline(t,{{color:j.c,weight:4,opacity:0.85}}).addTo(lmap);
      pl.bindPopup(popupHtml(j));
      pl.on('mouseover',function(){{highlight(i,true);}});
      pl.on('mouseout',function(){{highlight(i,false);}});
      segs.push(pl);
    }});
    lines[i]=segs;
    var first=(j.track||[]).find(function(t){{return t.length;}});
    if(first){{
      var m=L.circleMarker(first[0],{{radius:7,color:'#fff',weight:2,fillColor:j.c,fillOpacity:1}}).addTo(lmap);
      m.bindPopup(popupHtml(j));
      m.bindTooltip(j.label,{{direction:'top'}});
      m.on('mouseover',function(){{highlight(i,true);}});
      m.on('mouseout',function(){{highlight(i,false);}});
    }}
  }});
  if(all.length)lmap.fitBounds(L.latLngBounds(all).pad(0.08));
  else lmap.setView([23.7,121],7);
  [].forEach.call(document.querySelectorAll('#list li'),function(li){{
    var i=parseInt(li.getAttribute('data-i'),10);
    li.onmouseenter=function(){{highlight(i,true);}};
    li.onmouseleave=function(){{highlight(i,false);}};
  }});
}}
initSort();initMap();
</script></body></html>"""
    open(os.path.join(SITE, "index.html"), "w").write(html)
    print(f"site/index.html ← {len(S)} journeys: " + ", ".join(s["id"] for s in S))


if __name__ == "__main__":
    main()
