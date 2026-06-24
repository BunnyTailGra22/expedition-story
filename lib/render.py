"""Render one walk's points into a self-contained transect HTML (SOW brand):
elevation profile, 科/屬 filter (中拉, TaiCoL), GPS-flag diamonds, photo tooltip,
pinch-zoom/pan; clicking a point opens its iNaturalist observation."""
import json, math

TPL = """<!DOCTYPE html><html lang="zh-Hant"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1">
<title>__TITLE__</title>
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@400;500;700&display=swap" rel="stylesheet">
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/hammer.js/2.0.8/hammer.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/chartjs-plugin-zoom/2.0.1/chartjs-plugin-zoom.min.js"></script>
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
</style></head><body><div class="wrap">
<div class="nav"><a href="../index.html">← 旅程索引 journeys</a></div>
<h1>__TITLE__</h1>
<p class="sub">__SUBT__</p>
<div class="cards">
  <div class="card"><div class="lbl">觀察數 observations</div><div class="val">__N__</div></div>
  <div class="card"><div class="lbl">物種數 species</div><div class="val">__SP__</div></div>
  <div class="card"><div class="lbl">科別 family</div><select id="famSel" autocomplete="off"></select></div>
  <div class="card"><div class="lbl">屬別 genus</div><select id="genSel" autocomplete="off"></select></div>
  <div class="card"><div class="lbl">步道長 trail</div><div class="val">__DIST__ m</div></div>
  <div class="card"><div class="lbl">爬升 climb</div><div class="val">__CLIMBSIGN____CLIMB__ m</div><div class="sub2">__E0__ → __E1__ m</div></div>
</div>
<div class="legend">
  <span><i class="dot" style="background:var(--green)"></i>研究等級 research</span>
  <span><i class="dot" style="background:var(--green2)"></i>需鑑定 needs-ID</span>
  <span><i class="diam"></i>GPS &gt;100 m · 位置/高程內插 interpolated</span>
</div>
<div class="ctrl"><span>縮放：雙指 / 滾輪　平移：拖曳　點選點位 → iNaturalist</span><button id="rz" type="button">重置 reset</button></div>
<div class="chartbox"><canvas id="t" role="img" aria-label="__TITLE__ 海拔剖面圖"></canvas></div>
<p class="foot">__FOOT__</p>
</div>
<script>
var DATA=__DATA__;
var FAM='*', GEN='*', chart;
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
function go(){
  fillFamilies();fillGenera('*');
  document.getElementById('famSel').onchange=function(){FAM=this.value;GEN='*';fillGenera(FAM);chart.update();};
  document.getElementById('genSel').onchange=function(){GEN=this.value;chart.update();};
  document.getElementById('rz').onclick=function(){if(chart.resetZoom)chart.resetZoom();};
  chart=new Chart(document.getElementById('t'),{type:'line',
    data:{datasets:[{data:DATA,borderColor:'#666666',borderWidth:1.5,fill:'start',backgroundColor:'rgba(178,178,178,0.20)',tension:0.3,
      pointBackgroundColor:pcol,pointBorderColor:pbord,pointBorderWidth:pbw,pointRadius:prad,pointStyle:pstyle,
      pointHitRadius:function(c){return active(c.raw)?10:0;},pointHoverRadius:function(c){return active(c.raw)?prad(c)+2:0;}}]},
    options:{responsive:true,maintainAspectRatio:false,interaction:{mode:'nearest',intersect:true},
      onClick:function(e,els){if(els.length){var p=DATA[els[0].index];if(!active(p))return;window.open(p.u,'_blank');}},
      plugins:{legend:{display:false},tooltip:{enabled:false,external:extTip},
        zoom:{pan:{enabled:true,mode:'x'},zoom:{wheel:{enabled:true},pinch:{enabled:true},mode:'x'},limits:{x:{min:0,max:__XMAX__,minRange:40}}}},
      scales:{x:{type:'linear',min:0,max:__XMAX__,title:{display:true,text:'沿步道水平距離 horizontal distance (m)',color:'#666'},grid:{color:'rgba(178,178,178,0.30)'},ticks:{color:'#666',callback:function(v){return v+' m';}}},
        y:{min:__YMIN__,max:__YMAX__,title:{display:true,text:'海拔 elevation (m)',color:'#666'},grid:{color:'rgba(178,178,178,0.30)'},ticks:{color:'#666',callback:function(v){return v+' m';}}}}}});
}
if(window.Chart){go();}else{var w=setInterval(function(){if(window.Chart){clearInterval(w);go();}},60);}
</script></body></html>"""


def transect_html(meta, pts):
    ys = [p["y"] for p in pts]
    nsp = len({p["s"] for p in pts})
    dist = int(round(pts[-1]["x"])) if pts else 0
    xmax = int(math.ceil((pts[-1]["x"] if pts else 0) / 25) * 25) or 25
    e0, e1 = int(round(ys[0])), int(round(ys[-1]))
    climb = e1 - e0
    foot = (f"資料來源 iNaturalist API（觀察者 {meta.get('user','')}，地點 place_id {meta.get('place_id','')}）· "
            f"海拔 SRTM 30 m（雙線性內插）· GPS &gt;100 m 之點位置與高程以鄰近可靠點時間內插 · "
            f"科/屬中拉名與特有/保育：TaiCoL 臺灣物種名錄 · 色彩：荒野保護協會"
            + (f" · 快照 {meta['snapshot']}" if meta.get("snapshot") else "") + "。")
    rep = {"__TITLE__": meta["title"], "__SUBT__": meta["subtitle"],
           "__N__": str(len(pts)), "__SP__": str(nsp), "__DIST__": str(dist),
           "__XMAX__": str(xmax), "__CLIMB__": str(abs(climb)), "__CLIMBSIGN__": "+" if climb >= 0 else "−",
           "__E0__": str(e0), "__E1__": str(e1),
           "__YMIN__": str(int(min(ys)) - 8), "__YMAX__": str(int(max(ys)) + 8),
           "__FOOT__": foot, "__DATA__": json.dumps(pts, ensure_ascii=False)}
    html = TPL
    for k, v in rep.items():
        html = html.replace(k, v)
    return html
