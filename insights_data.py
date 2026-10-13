#!/usr/bin/env python3
"""Gather the facts behind a journey's 「AI彙整，待查證」 section and print them as a
report to write it from.

  python3 insights_data.py --journey south1-2025-trek
  python3 insights_data.py --journey south1-2025-trek --zones 3240,3100,2500 --month 3

For every kept observation (same scope, GPX placement and taxonomy as generate.py):
elevation, along-route km, date, research grade, family / genus, and status —
TaiCoL 特有 / IUCN / 紅皮書 / 原生·外來 inside Taiwan, iNaturalist IUCN + national list +
establishment means elsewhere. For every plant taxon: flowering and fruiting months
from iNaturalist "Flowers and Fruits" annotations (the journey's country, or global
when the country has fewer than 8 annotations).

The report lists the observations by elevation zone × genus, one line per taxon with
its status and 花果期 peak months, the endemic / threatened / introduced taxa, what was
in flower or fruit in the journey's month, and excluded or obscured observations.
Everything is also written to caches/insights/<id>.json; phenology histograms are
cached in caches/phenology.json. Network: api.inaturalist.org (+ api.taicol.tw)."""
import argparse, collections, json, os, sys, time, urllib.parse, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import generate as G
from lib import walks as W, profile as P, track as TR, taicol as T

API = "https://api.inaturalist.org/v1"
TAIWAN = {7887, 7888}


def get(path):
    for i in range(4):
        try:
            return json.load(urllib.request.urlopen(API + path, timeout=60))
        except Exception:
            time.sleep(2 * (i + 1))
    raise RuntimeError(path)


def points(cfg):
    """The page's points, built exactly as generate.py builds them."""
    obs = W.fetch(cfg["user_login"], cfg["place_id"], cfg["d1"], cfg["d2"])
    if cfg.get("mode") == "trek":
        trk = None
        if cfg.get("gpx"):
            g = cfg["gpx"]
            trk = TR.load([os.path.join(HERE, "journeys", cfg["id"], f) for f in ([g] if isinstance(g, str) else g)])
        pts = P.build(obs, cfg.get("scope"), G.CACHE, track=trk)
    else:
        pts = [p for w in W.segment(obs, cfg.get("walk_gap_min", 120))
               for p in P.build(w["obs"], cfg.get("scope"), G.CACHE)]
    G.enrich_points(pts, cfg)
    return obs, pts


def status_inat(tids, country):
    """iNaturalist IUCN (global), national lists and establishment means in the country."""
    out = {}
    tids = sorted(t for t in tids if t)
    for i in range(0, len(tids), 25):
        for t in get(f"/taxa/{','.join(map(str, tids[i:i + 25]))}?locale=zh-TW")["results"]:
            cs = [(c.get("authority") or "", c.get("status"), (c.get("place") or {}).get("id"))
                  for c in t.get("conservation_statuses", [])]
            est = [l.get("establishment_means") for l in t.get("listed_taxa", [])
                   if (l.get("place") or {}).get("id") == country]
            out[t["id"]] = {"iucn": next((s for a, s, pl in cs if pl is None and "IUCN" in a), None),
                            "national": [f"{a}={s}" for a, s, pl in cs if pl == country],
                            "establishment": est[0] if est else None}
        time.sleep(1)
    return out


def phenology(tids, country, cache_path):
    cache = json.load(open(cache_path)) if os.path.exists(cache_path) else {}
    for tid in tids:
        key = f"{tid}@{country}"
        if key in cache:
            continue
        rec = {}
        for scope in ("country", "global"):
            for lab, v in (("fl", 13), ("fr", 14)):
                q = {"taxon_id": tid, "term_id": 12, "term_value_id": v, "date_field": "observed",
                     "interval": "month_of_year", "verifiable": "true"}
                if scope == "country":
                    q["place_id"] = country
                h = get("/observations/histogram?" + urllib.parse.urlencode(q))["results"]["month_of_year"]
                rec[f"{scope}_{lab}"] = [h.get(str(m), 0) for m in range(1, 13)]
                time.sleep(0.5)
            if sum(rec["country_fl"]) + sum(rec["country_fr"]) >= 8:
                break
        cache[key] = rec
        os.makedirs(os.path.dirname(cache_path), exist_ok=True)
        json.dump(cache, open(cache_path, "w"))
    return {tid: cache[f"{tid}@{country}"] for tid in tids}


def months(a, share=0.4):
    """Peak months (≥ share of the busiest month) as compact ranges, e.g. '12–4'."""
    if sum(a) < 4:
        return None
    top = max(a)
    ms = [i + 1 for i, c in enumerate(a) if c >= share * top]
    runs = []
    for m in ms:
        if runs and m == runs[-1][1] + 1:
            runs[-1][1] = m
        else:
            runs.append([m, m])
    if len(runs) > 1 and runs[0][0] == 1 and runs[-1][1] == 12:
        runs[-1][1] = runs[0][1]
        runs = runs[1:]
    return "、".join(f"{a}–{b}" if a != b else str(a) for a, b in runs)


def phen_text(ph):
    if not ph:
        return ""
    sc = "country" if sum(ph.get("country_fl", [])) + sum(ph.get("country_fr", [])) >= 8 else "global"
    fl, fr = months(ph.get(f"{sc}_fl", [0] * 12)), months(ph.get(f"{sc}_fr", [0] * 12))
    n = sum(ph.get(f"{sc}_fl", [])) + sum(ph.get(f"{sc}_fr", []))
    tag = "" if sc == "country" else "全"
    return " ".join(x for x in (f"花 {fl}" if fl else "", f"果 {fr}" if fr else "") if x) + (f"（{tag}n={n}）" if fl or fr else "")


def in_month(a, m, share=0.25):
    return sum(a) >= 4 and a[m - 1] >= share * max(a)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--journey", required=True)
    ap.add_argument("--zones", default="3300,3100,2500",
                    help="descending elevation cut-offs, metres (Taiwan default after 蘇鴻傑 1984)")
    ap.add_argument("--month", type=int, default=0, help="journey month for the in-season list (default: d1's)")
    a = ap.parse_args()
    cfg = json.load(open(os.path.join(HERE, "journeys", a.journey, "config.json"), encoding="utf-8"))
    taiwan = cfg["place_id"] in TAIWAN
    country = 7887 if taiwan else cfg["place_id"]
    month = a.month or int(cfg["d1"][5:7])
    cuts = [int(c) for c in a.zones.split(",")]

    obs, pts = points(cfg)
    byid = {str(o["id"]): o for o in obs}
    tc = json.load(open(os.path.join(G.CACHE, "taicol.json"))) if taiwan and os.path.exists(os.path.join(G.CACHE, "taicol.json")) else {}
    rows = []
    for p in pts:
        oid = p["u"].rstrip("/").split("/")[-1]
        o = byid.get(oid, {})
        tx = o.get("taxon") or {}
        t = W._t(o)
        rows.append({"id": oid, "sci": p["s"], "name": p["c"] or p["s"], "tid": p["tid"], "rank": tx.get("rank"),
                     "iconic": tx.get("iconic_taxon_name"), "fam": p["famSci"], "fam_zh": p["famZh"],
                     "gen": p["genSci"], "gen_zh": p["genZh"], "ele": round(p["y"]), "km": round(p["x"] / 1000, 1),
                     "date": t.strftime("%m-%d") if t else "", "grade": p["g"]})
    taxa = {r["tid"]: r for r in rows if r["tid"]}
    if taiwan:
        for r in rows:
            e = tc.get(r["sci"], {})
            r.update(endemic=bool(e.get("is_endemic")), iucn=e.get("iucn"), redlist=e.get("redlist"),
                     taicol_zh=e.get("accepted_zh"))
        alien = {}
        for r in taxa.values():
            if r["rank"] in ("species", "subspecies", "variety"):
                rec = T._match(r["sci"])
                alien[r["sci"]] = rec.get("alien_type") if rec else None
                time.sleep(0.3)
        for r in rows:
            r["origin"] = alien.get(r["sci"])
    else:
        st = status_inat(taxa, country)
        for r in rows:
            s = st.get(r["tid"], {})
            r.update(iucn=s.get("iucn"), national=s.get("national"), origin=s.get("establishment"),
                     endemic=s.get("establishment") == "endemic")
    plants = [t for t, r in taxa.items() if r["iconic"] == "Plantae"]
    ph = phenology(plants, country, os.path.join(G.CACHE, "phenology.json"))

    # ---------- report ----------
    def zone(e):
        for i, c in enumerate(cuts):
            if e >= c:
                return i
        return len(cuts)
    species_level = {r["sci"]: r for r in rows if r["rank"] in ("species", "subspecies", "variety")}
    print(f"# {cfg['label']} — {len(rows)} 筆 · {len({r['sci'] for r in rows})} 類群 · "
          f"{len(species_level)} 種級 · 研究等級 {sum(r['grade'] == 'research' for r in rows)}/{len(rows)} · "
          f"{min(r['ele'] for r in rows):,}–{max(r['ele'] for r in rows):,} m")
    print("\n## 依棲地（海拔帶）× 屬")
    Z = collections.defaultdict(list)
    for r in rows:
        Z[zone(r["ele"])].append(r)
    for k in sorted(Z):
        rs = Z[k]
        sp = {r["sci"] for r in rs if r["sci"] in species_level}
        en = {r["sci"] for r in rs if r["sci"] in species_level and r.get("endemic")}
        lo = f"≥{cuts[k]:,}" if k < len(cuts) else f"<{cuts[-1]:,}"
        print(f"\n### {lo} m · {len(rs)} 筆 · {min(r['ele'] for r in rs):,}–{max(r['ele'] for r in rs):,} m · "
              f"km {min(r['km'] for r in rs)}–{max(r['km'] for r in rs)} · {sorted({r['date'] for r in rs})} · 特有 {len(en)}/{len(sp)}")
        G2 = collections.defaultdict(list)
        for r in rs:
            G2[(r["gen_zh"] or r["gen"], r["fam_zh"] or r["fam"])].append(r)
        for (g, f), v in sorted(G2.items(), key=lambda kv: -len(kv[1])):
            names = collections.Counter(x["name"] for x in v)
            print(f"- {g}（{f}）: " + "、".join(f"{n}{'＊' if any(x['name'] == n and x.get('endemic') for x in v) else ''}"
                                               f"{f'（{c}）' if c > 1 else ''}" for n, c in names.items())
                  + f" · {min(x['ele'] for x in v):,}–{max(x['ele'] for x in v):,} m")
    print("\n## 依科別（科 | 屬 | 種（筆・海拔）| 狀態 | 花果期）")
    per = collections.OrderedDict()
    for r in sorted(rows, key=lambda r: (r["fam"], r["gen"], r["sci"])):
        per.setdefault(r["sci"], []).append(r)
    for sci, v in per.items():
        r = v[0]
        e = [x["ele"] for x in v]
        rng = f"{min(e):,} m" if min(e) == max(e) else f"{min(e):,}–{max(e):,} m"
        st = [s for s in ("特" if r.get("endemic") else "", r.get("iucn") or "",
                          f"紅 {r['redlist']}" if r.get("redlist") else "",
                          "；".join(r.get("national") or []),
                          r.get("origin") if r.get("origin") not in (None, "native", "endemic") else "") if s]
        print(f"- {r['fam_zh'] or r['fam']} | {r['gen_zh'] or r['gen']} | {r['name']} {sci}（{len(v)}・{rng}）| "
              f"{'・'.join(st) or '—'} | {phen_text(ph.get(r['tid']))}")
    print("\n## 摘要")
    src = "TaiCoL" if taiwan else f"iNaturalist place {country} establishment means — verify, often too narrow"
    print(f"- 特有（{src}）:", "、".join(r["name"] for r in species_level.values() if r.get("endemic")) or "—")
    print("- 受脅:", "、".join(f"{r['name']}（{'・'.join(x for x in (r.get('iucn'), r.get('redlist')) if x)}）"
                             for r in species_level.values()
                             if (r.get("iucn") in ("NT", "VU", "EN", "CR")) or (r.get("redlist") or "NLC") not in ("NLC", "NA", "DD"))
          or "—")
    print("- 外來:", "、".join(f"{r['name']}（{r['origin']}）" for r in species_level.values()
                             if r.get("origin") not in (None, "native", "endemic")) or "—")
    def peak(tid, lab):
        p = ph.get(tid) or {}
        sc = "country" if sum(p.get("country_fl", [])) + sum(p.get("country_fr", [])) >= 8 else "global"
        return p.get(f"{sc}_{lab}", [0] * 12)
    print(f"- {month} 月花期中:", "、".join(r["name"] for t, r in taxa.items() if t in ph and in_month(peak(t, "fl"), month)) or "—")
    print(f"- {month} 月果期中:", "、".join(r["name"] for t, r in taxa.items() if t in ph and in_month(peak(t, "fr"), month)) or "—")
    print("- 每日筆數:", " ".join(f"{d}:{n}" for d, n in sorted(collections.Counter(r["date"] for r in rows).items())))
    excl = (cfg.get("scope") or {}).get("exclude_obs_ids", [])
    print("- 排除:", "、".join(f"{i} {(byid[i].get('taxon') or {}).get('name')}{'（模糊座標）' if byid[i].get('obscured') else ''}"
                             for i in excl if i in byid) or "—")
    kept_obscured = [r for r in rows if byid.get(r["id"], {}).get("obscured")]
    print("- 仍在圖上的模糊座標紀錄:", "、".join(f"{r['id']} {r['name']}" for r in kept_obscured) or "—")

    out = os.path.join(G.CACHE, "insights", f"{a.journey}.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    json.dump({"journey": a.journey, "zones": cuts, "month": month, "rows": rows,
               "phenology": {str(k): v for k, v in ph.items()}}, open(out, "w"), ensure_ascii=False, indent=1)
    print(f"\n(wrote {os.path.relpath(out, HERE)})")


if __name__ == "__main__":
    main()
