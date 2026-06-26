"""Render one walk's points into a self-contained HTML page:
1) elevation transect (Chart.js): 科/屬 filter (中拉), GPS-flag diamonds, photo
   tooltip, pinch-zoom/pan; click a point → its iNaturalist observation.
2) observation map below it (Leaflet + OpenTopoMap, MVP): obs-point track polyline
   + circular photo markers + popups; the 科/屬 filter syncs both views. Mobile-
   responsive. (Track = obs points in time order; a real GPX route is a later tier.)"""
import json, math

TPL = """<!DOCTYPE html><html lang="zh-Hant"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1">
<title>__TITLE__</title>
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@400;500;700&display=swap" rel="stylesheet">
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/hammer.js/2.0.8/hammer.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/chartjs-plugin-zoom/2.0.1/chartjs-plugin-zoom.min.js"></script>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>
:root{--green:#587A30;--green2:#90B821;--gray:#666;--gray2:#B2B2B2;--yellow:#FFD900;--red:#E8380D;--ink:#3a3a36}
*{box-sizing:border-box}body{margin:0;background:#fff;color:var(--ink);font-family:"Noto Sans TC",system-ui,sans-serif}
.wrap{max-width:1000px;margin:0 auto;padding:40px 26px 34px}
.nav{font-size:13px;margin:0 0 14px}.nav a{color:var(--green);text-decoration:none}
h1{font-weight:700;font-size:24px;color:var(--green);margin:0 0 4px}
.sub{font-size:14px;color:var(--gray);margin:0 0 20px}
.cards{display:grid;grid-template-columns:repeat(6,1fr);gap:10px;margin:0 0 20px}
.card{background:#f5f4ef;border-radius:10px;padding:11px 12px}
.card .lbl{font-size:12px;color:var(--gray)}.card .val{font-size:22px;font-weight:500}
.card .sub2{font-size:11px;color:var(--gray2);margin-top:2px}
.card select{width:100%;font-family:inherit;font-size:13px;color:var(--ink);background:#fff;border:0.5px solid var(--gray2);border-radius:6px;padding:7px 6px;margin-top:3px;cursor:pointer}
@media(max-width:760px){.wrap{padding:24px 16px}.cards{grid-template-columns:repeat(3,1fr)}}
@media(max-width:480px){h1{font-size:20px}.cards{grid-template-columns:repeat(2,1fr)}.card .val{font-size:19px}}
.legend{display:flex;flex-wrap:wrap;gap:15px;font-size:13px;color:var(--gray);margin:0 0 8px}
.legend i{display:inline-block;vertical-align:middle;margin-right:6px}
.dot{width:11px;height:11px;border-radius:50%}.diam{width:10px;height:10px;background:var(--green);border:1.5px solid var(--red);transform:rotate(45deg)}
.ctrl{display:flex;justify-content:space-between;gap:10px;align-items:center;margin:0 0 8px;font-size:12px;color:var(--gray2)}
.ctrl button{font-family:inherit;font-size:12px;color:var(--gray);background:#fff;border:0.5px solid var(--gray2);border-radius:6px;padding:5px 10px;cursor:pointer}
.chartbox{position:relative;width:100%;height:450px;touch-action:none}
.ctt{position:fixed;opacity:0;transition:opacity .12s;background:#fff;z-index:30;font-size:12px;line-height:1.45;border:0.5px solid var(--gray2);border-radius:8px;padding:8px}
.ctt.float{width:178px;pointer-events:none}
.ctt.float img{width:100%;height:118px;object-fit:cover;border-radius:6px;margin-bottom:6px;display:block;background:#f1efe8}
.ctt.sheet{left:0;right:0;bottom:0;width:100%;border:none;border-top:0.5px solid var(--gray2);border-radius:12px 12px 0 0;box-shadow:0 -2px 14px rgba(0,0,0,.10);padding:12px 16px;display:flex;gap:12px;align-items:center;pointer-events:auto}
.ctt.sheet img{width:88px;height:88px;flex:0 0 auto;object-fit:cover;border-radius:8px;background:#f1efe8}
.ctt .nm{font-weight:700;color:var(--green);font-size:14px}.ctt .sci{font-style:italic;color:var(--gray)}.ctt .fam{color:var(--gray)}.ctt .lnk{display:inline-block;margin-top:6px;color:var(--green);font-weight:500;text-decoration:none}
.foot{margin-top:20px;font-size:11.5px;color:var(--gray2);line-height:1.6}
.seclbl{font-size:15px;font-weight:500;color:var(--green);margin:30px 0 6px}
.seclbl span{font-size:12px;font-weight:400;color:var(--gray2);margin-left:8px}
.mapbox{position:relative;width:100%;height:480px;border-radius:12px;overflow:hidden;border:0.5px solid var(--gray2)}
#map{width:100%;height:100%;background:#eee}
.mk{width:38px;height:38px;border-radius:50%;overflow:hidden;border:2px solid #fff;box-shadow:0 1px 4px rgba(0,0,0,.35);background:#f1efe8}
.mk img{width:100%;height:100%;object-fit:cover;display:block}
.mk.fl{border-color:var(--red)}
.dotmk{width:14px;height:14px;border-radius:50%;border:2px solid #fff;box-shadow:0 1px 3px rgba(0,0,0,.3)}
.dotmk.fl{border-color:var(--red)}
.leaflet-popup-content{font-family:"Noto Sans TC",system-ui,sans-serif;margin:10px 12px;width:180px!important}
.pp img{width:100%;height:120px;object-fit:cover;border-radius:6px;margin-bottom:6px;display:block;background:#f1efe8}
.pp .nm{font-weight:700;color:var(--green);font-size:14px}.pp .sci{font-style:italic;color:var(--gray);font-size:12px}
.pp .fam{color:var(--gray);font-size:12px}.pp .lnk{display:inline-block;margin-top:6px;color:var(--green);font-weight:500;text-decoration:none;font-size:12px}
@media(max-width:760px){.mapbox{height:360px}}
</style></head><body><div class="wrap">
__NAV__
<h1>__TITLE__</h1>
<p class="sub">__SUBT__</p>
<div class="cards">
  <div class="card"><div class="lbl">觀察數 observations</div><div class="val">__N__</div></div>
  <div class="card"><div class="lbl">物種數 species</div><div class="val">__SP__</div></div>
  <div class="card"><div class="lbl">科別 family</div><select id="famSel" autocomplete="off"></select></div>
  <div class="card"><div class="lbl">屬別 genus</div><select id="genSel" autocomplete="off"></select></div>
  <div class="card"><div class="lbl">步道長 trail</div><div class="val">__DIST__ __DUNIT__</div></div>
  <div class="card"><div class="lbl">__C6LBL__</div><div class="val">__C6VAL__</div><div class="sub2">__C6SUB__</div></div>
</div>
<div class="legend">
  <span><i class="dot" style="background:var(--green)"></i>研究等級 research</span>
  <span><i class="dot" style="background:var(--green2)"></i>需鑑定 needs-ID</span>
  <span><i class="diam"></i>GPS &gt;100 m · 位置/高程內插 interpolated</span>
</div>
<div class="ctrl"><span>縮放：雙指 / 滾輪　平移：拖曳　點選點位 → iNaturalist</span><button id="rz" type="button">重置 reset</button></div>
<div class="chartbox"><canvas id="t" role="img" aria-label="__TITLE__ 海拔剖面圖"></canvas></div>
<div class="seclbl">觀測點地圖 observation map<span>拖曳/縮放　點選圖示看物種　科/屬篩選同步</span></div>
<div class="mapbox"><div id="map"></div></div>
<p class="foot">__FOOT__</p>
</div>
<script>
var DATA=__DATA__;
var FAM='*', GEN='*', chart, lmap, markers=[], trackLine;
function isMobile(){return window.matchMedia('(max-width:760px)').matches;}
function gen(d){return d.genSci;}
function active(d){return (FAM==='*'||d.famSci===FAM)&&(GEN==='*'||gen(d)===GEN);}
function pcol(c){var d=c.raw;return d.g==='research'?'#587A30':'#90B821';}
function pbord(c){return c.raw.fl?'#E8380D':'#ffffff';}
function pbw(c){return c.raw.fl?2.5:1;}
function prad(c){var d=c.raw;if(!active(d))return 0;return d.fl?5.5:4;}
function pstyle(c){return c.raw.fl?'rectRot':'circle';}
function extTip(ctx){
  var tip=ctx.tooltip, mob=isMobile();
  var el=document.getElementById('ctt');
  if(!el){el=document.createElement('div');el.id='ctt';document.body.appendChild(el);}
  if(tip.opacity===0){el.style.opacity=0;return;}
  var d=tip.dataPoints[0].raw;
  if(!active(d)){el.style.opacity=0;return;}
  var img=d.ph?('<img src="'+d.ph+'" alt="">'):'';
  var link=mob?('<a class="lnk" href="'+d.u+'" target="_blank" rel="noopener">iNaturalist ↗</a>'):'';
  var bd=(d.end?'<span style="color:#3B6D11">⬥臺灣特有</span> ':'')+(d.threat?'<span style="color:#A32D2D">'+(['CR','EN','VU','NT'].indexOf(d.threat)>=0?'IUCN ':'紅皮書 ')+d.threat+'</span>':'');
  el.innerHTML=img+'<div><div class="nm">'+(d.c||'—')+'</div><div class="sci">'+d.s+
    '</div><div class="fam">'+(d.famZh||'')+' '+(d.famSci||'')+'</div><div class="fam">'+(d.genZh||'')+' '+(d.genSci||'')+'</div>'+
    (bd?'<div class="fam">'+bd+'</div>':'')+(d.fl?'<div class="fam" style="color:#E8380D">GPS ±'+Math.round(d.a)+'m</div>':'')+link+'</div>';
  if(mob){el.className='ctt sheet';el.style.left='0';el.style.right='0';el.style.bottom='0';el.style.top='auto';el.style.width='';}
  else{el.className='ctt float';var r=ctx.chart.canvas.getBoundingClientRect();var left=r.left+tip.caretX+16;if(left+186>window.innerWidth)left=r.left+tip.caretX-186;if(left<4)left=4;var top=r.top+tip.caretY-30;if(top<4)top=4;el.style.left=left+'px';el.style.top=top+'px';el.style.right='auto';el.style.bottom='auto';}
  el.style.opacity=1;
}
function fillFamilies(){var fc={},fz={};DATA.forEach(function(d){fc[d.famSci]=(fc[d.famSci]||0)+1;fz[d.famSci]=d.famZh;});
  var keys=Object.keys(fc).sort(function(a,b){return fc[b]-fc[a];});
  var h='<option value="*">全部 all ('+keys.length+' 科)</option>';
  keys.forEach(function(k){h+='<option value="'+k+'">'+(fz[k]?fz[k]+' ':'')+k+' · '+fc[k]+'</option>';});
  document.getElementById('famSel').innerHTML=h;}
function fillGenera(fam){var gc={},gz={};DATA.forEach(function(d){if(fam==='*'||d.famSci===fam){gc[d.genSci]=(gc[d.genSci]||0)+1;gz[d.genSci]=d.genZh;}});
  var keys=Object.keys(gc).sort();var h='<option value="*">全部 all ('+keys.length+' 屬)</option>';
  keys.forEach(function(k){h+='<option value="'+k+'">'+(gz[k]?gz[k]+' ':'')+k+' · '+gc[k]+'</option>';});
  document.getElementById('genSel').innerHTML=h;}
function markerIcon(d){
  if(d.ph){var u=d.ph.replace('medium','square');
    return L.divIcon({className:'',iconSize:[38,38],iconAnchor:[19,19],html:'<div class="mk'+(d.fl?' fl':'')+'"><img src="'+u+'" alt=""></div>'});}
  var col=d.g==='research'?'#587A30':'#90B821';
  return L.divIcon({className:'',iconSize:[14,14],iconAnchor:[7,7],html:'<div class="dotmk'+(d.fl?' fl':'')+'" style="background:'+col+'"></div>'});
}
function popupHtml(d){
  var img=d.ph?('<img src="'+d.ph+'" alt="">'):'';
  var bd=(d.end?'<span style="color:#3B6D11">⬥臺灣特有</span> ':'')+(d.threat?'<span style="color:#A32D2D">'+(['CR','EN','VU','NT'].indexOf(d.threat)>=0?'IUCN ':'紅皮書 ')+d.threat+'</span>':'');
  return '<div class="pp">'+img+'<div class="nm">'+(d.c||'—')+'</div><div class="sci">'+d.s+'</div><div class="fam">'+(d.famZh||'')+' '+(d.famSci||'')+'</div>'+(bd?'<div class="fam">'+bd+'</div>':'')+(d.fl?'<div class="fam" style="color:#E8380D">GPS ±'+Math.round(d.a)+'m · 位置內插</div>':'')+'<a class="lnk" href="'+d.u+'" target="_blank" rel="noopener">iNaturalist ↗</a></div>';
}
function initMap(){
  if(!window.L){setTimeout(initMap,80);return;}
  var geo=DATA.filter(function(d){return d.lat!=null&&d.lng!=null;});
  if(!geo.length)return;
  lmap=L.map('map',{scrollWheelZoom:true});
  L.tileLayer('https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png',{maxZoom:17,attribution:'© OpenStreetMap、SRTM ｜ © OpenTopoMap (CC-BY-SA)'}).addTo(lmap);
  trackLine=L.polyline(geo.map(function(d){return [d.lat,d.lng];}),{color:'#FC5200',weight:3,opacity:0.9}).addTo(lmap);
  geo.forEach(function(d){var m=L.marker([d.lat,d.lng],{icon:markerIcon(d)});m.bindPopup(popupHtml(d),{maxWidth:200});markers.push({m:m,d:d});});
  refreshMarkers();
  lmap.fitBounds(trackLine.getBounds(),{padding:[30,30]});
}
function refreshMarkers(){
  if(!lmap)return;
  markers.forEach(function(o){
    if(active(o.d)){if(!lmap.hasLayer(o.m))o.m.addTo(lmap);}
    else if(lmap.hasLayer(o.m))lmap.removeLayer(o.m);
  });
}
function go(){
  fillFamilies();fillGenera('*');
  document.getElementById('famSel').onchange=function(){FAM=this.value;GEN='*';fillGenera(FAM);chart.update();refreshMarkers();};
  document.getElementById('genSel').onchange=function(){GEN=this.value;chart.update();refreshMarkers();};
  document.getElementById('rz').onclick=function(){if(chart.resetZoom)chart.resetZoom();};
  chart=new Chart(document.getElementById('t'),{type:'line',
    data:{datasets:[{data:DATA,borderColor:'#666666',borderWidth:1.5,fill:'start',backgroundColor:'rgba(178,178,178,0.20)',tension:0.3,
      pointBackgroundColor:pcol,pointBorderColor:pbord,pointBorderWidth:pbw,pointRadius:prad,pointStyle:pstyle,
      pointHitRadius:function(c){return active(c.raw)?10:0;},pointHoverRadius:function(c){return active(c.raw)?prad(c)+2:0;}}]},
    options:{responsive:true,maintainAspectRatio:false,interaction:{mode:'nearest',intersect:true},
      onClick:function(e,els){if(els.length){var p=DATA[els[0].index];if(!active(p))return;window.open(p.u,'_blank');}},
      plugins:{legend:{display:false},tooltip:{enabled:false,external:extTip},
        zoom:{pan:{enabled:true,mode:'x'},zoom:{wheel:{enabled:true},pinch:{enabled:true},mode:'x'},limits:{x:{min:0,max:__XMAX__,minRange:40}}}},
      scales:{x:{type:'linear',min:0,max:__XMAX__,title:{display:true,text:'沿步道水平距離 horizontal distance (__XUNIT__)',color:'#666'},grid:{color:'rgba(178,178,178,0.30)'},ticks:{color:'#666',callback:function(v){return v/__USCALE__+' __XUNIT__';}}},
        y:{min:__YMIN__,max:__YMAX__,title:{display:true,text:'海拔 elevation (m)',color:'#666'},grid:{color:'rgba(178,178,178,0.30)'},ticks:{color:'#666',callback:function(v){return v+' m';}}}}}});
  initMap();
}
if(window.Chart){go();}else{var w=setInterval(function(){if(window.Chart){clearInterval(w);go();}},60);}
</script></body></html>"""


def transect_html(meta, pts):
    ys = [p["y"] for p in pts]
    nsp = len({p["s"] for p in pts})
    maxx = pts[-1]["x"] if pts else 0
    xmax = int(math.ceil(maxx / 25) * 25) or 25
    # adaptive distance unit: metres for a short ridge walk, km for a long trek
    if maxx >= 2000:
        uscale, unit, dist = 1000, "km", f"{maxx / 1000:.1f}"
    else:
        uscale, unit, dist = 1, "m", str(int(round(maxx)))
    e0, e1 = int(round(ys[0])), int(round(ys[-1]))
    climb = e1 - e0
    if meta.get("trek"):  # out-and-back trek: peak + total ascent, not net start→end
        ascent = round(sum(max(0.0, ys[i] - ys[i - 1]) for i in range(1, len(ys))))
        c6lbl, c6val, c6sub = "最高海拔 peak", f"{int(round(max(ys)))} m", f"總爬升 +{ascent} m"
    else:
        c6lbl = "爬升 climb"
        c6val = f"{'+' if climb >= 0 else '−'}{abs(climb)} m"
        c6sub = f"{e0} → {e1} m"
    nav = "" if meta.get("nav") is False else \
        '<div class="nav"><a href="../index.html">← 旅程索引 journeys</a></div>'
    tax = ("科/屬中拉名：iNaturalist 分類（地區俗名 zh-TW）" if meta.get("taxonomy") == "inat"
           else "科/屬中拉名與特有/保育：TaiCoL 臺灣物種名錄")
    foot = (f"資料來源 iNaturalist API（觀察者 {meta.get('user','')}，地點 place_id {meta.get('place_id','')}）· "
            f"海拔 SRTM 30 m（雙線性內插）· GPS &gt;100 m 之點位置與高程以鄰近可靠點時間內插 · "
            f"{tax}"
            + (f" · 快照 {meta['snapshot']}" if meta.get("snapshot") else "") + "。")
    rep = {"__TITLE__": meta["title"], "__SUBT__": meta["subtitle"], "__NAV__": nav,
           "__N__": str(len(pts)), "__SP__": str(nsp), "__DIST__": dist, "__DUNIT__": unit,
           "__XMAX__": str(xmax), "__USCALE__": str(uscale), "__XUNIT__": unit,
           "__C6LBL__": c6lbl, "__C6VAL__": c6val, "__C6SUB__": c6sub,
           "__YMIN__": str(int(min(ys)) - 8), "__YMAX__": str(int(max(ys)) + 8),
           "__FOOT__": foot, "__DATA__": json.dumps(pts, ensure_ascii=False)}
    html = TPL
    for k, v in rep.items():
        html = html.replace(k, v)
    return html
