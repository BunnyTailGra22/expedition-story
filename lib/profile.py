"""Turn one walk's observations into transect points:
apply config scope (time_before / exclude ids) → GPS-correct → SRTM elevation →
along-track distance. Returns a list of point dicts ready for taxonomy + render."""
import os, datetime
from datetime import timezone, timedelta
from . import geo, gps, elevation

TW = timezone(timedelta(hours=8))


def _t(o):
    s = o.get("time_observed_at") or o.get("observed_on")
    if not s:
        return None
    try:
        if "T" in s:
            return datetime.datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(TW)
        return datetime.datetime.fromisoformat(s + "T12:00:00+08:00")
    except Exception:
        return None


def build(walk_obs, scope, cache_dir):
    rows = []
    for o in walk_obs:
        t = _t(o)
        coords = (o.get("geojson") or {}).get("coordinates")
        if not t or not coords:
            continue
        rows.append({"_t": t, "lat": coords[1], "lng": coords[0],
                     "acc": float(o.get("positional_accuracy") or 0), "o": o})
    rows.sort(key=lambda r: r["_t"])

    scope = scope or {}
    ex = set(scope.get("exclude_obs_ids", []))
    tbh = None
    if scope.get("time_before"):
        hh, mm = map(int, scope["time_before"].split(":"))
        tbh = (hh, mm)

    def keep(r):
        if str(r["o"].get("id")) in ex:
            return False
        if tbh and (r["_t"].hour, r["_t"].minute) >= tbh:
            return False
        return True

    rows = [r for r in rows if keep(r)]
    if not rows:
        return []

    gps.correct(rows)
    coords = [(r["lat"], r["lng"]) for r in rows]
    els = elevation.sample(coords, os.path.join(cache_dir, "elevation.json"))
    dist = geo.cumdist(coords)

    pts = []
    for i, r in enumerate(rows):
        o = r["o"]; tx = o.get("taxon") or {}; ph = o.get("photos") or []
        pts.append({"n": i + 1, "t": r["_t"].strftime("%H:%M"), "s": tx.get("name"),
                    "c": tx.get("preferred_common_name") or "", "g": o.get("quality_grade"),
                    "a": round(r["acc"], 1), "x": dist[i], "y": els[i], "fl": r["fl"],
                    "tid": tx.get("id"),
                    "u": o.get("uri") or f"https://www.inaturalist.org/observations/{o.get('id')}",
                    "ph": (ph[0].get("url", "").replace("square", "medium") if ph else "")})

    for i, p in enumerate(pts):                       # fill any missing elevation by distance
        if p["y"] is None:
            L, R = i - 1, i + 1
            while L >= 0 and pts[L]["y"] is None:
                L -= 1
            while R < len(pts) and pts[R]["y"] is None:
                R += 1
            if L >= 0 and R < len(pts):
                f = (p["x"] - pts[L]["x"]) / ((pts[R]["x"] - pts[L]["x"]) or 1)
                p["y"] = pts[L]["y"] + f * (pts[R]["y"] - pts[L]["y"])
            elif L >= 0:
                p["y"] = pts[L]["y"]
            elif R < len(pts):
                p["y"] = pts[R]["y"]
            else:
                p["y"] = 0
        p["y"] = round(p["y"], 1)
    return pts
