"""Recorded GPS track (GPX) — the real walked route, replacing the straight
observation-to-observation polyline. Distance along it becomes the transect's x
axis, its recorded elevation the profile, and each observation is placed on it by
time (the track knows where you were when the photo was taken).

Loading is namespace-agnostic (GPX 1.0/1.1) and stdlib-only."""
import bisect, datetime, statistics, xml.etree.ElementTree as ET
from . import geo

TIME_TOL_M = 250            # a time-matched position must lie this close to the obs fix
NEAR_WINDOW_S = 3 * 3600    # fallback search window: a loop passes the same trail twice


def _tag(el):
    return el.tag.rsplit("}", 1)[-1]


def _child(el, name):
    return next((c for c in el if _tag(c) == name), None)


def smooth(t, ele, win_s):
    """Centred moving median of elevation over win_s seconds. For a watch that logs
    GPS-derived (not barometric) altitude: its jitter, summed by the ascent dead-band,
    inflates the climb (南湖 2020: +6703 m raw vs +4160 m at 120 s, SRTM +3855 m),
    while a median keeps the summits."""
    ts, out, a, b = [x.timestamp() for x in t], [], 0, 0
    for i, ti in enumerate(ts):
        while ts[a] < ti - win_s / 2:
            a += 1
        while b < len(ts) and ts[b] <= ti + win_s / 2:
            b += 1
        out.append(statistics.median(ele[a:b]))
    return out


def load(paths, smooth_s=0):
    """GPX files (any order; days may be split across files) -> one time-sorted
    track {"t": [datetime], "lat", "lng", "ele", "x": [cumulative m]}. smooth_s > 0
    median-filters a noisy elevation record (config "gpx_smooth_s")."""
    rows = []
    for p in paths:
        for tp in ET.parse(p).getroot().iter():
            if _tag(tp) != "trkpt":
                continue
            t, e = _child(tp, "time"), _child(tp, "ele")
            if t is None or not (t.text or "").strip():
                continue
            rows.append((datetime.datetime.fromisoformat(t.text.strip().replace("Z", "+00:00")),
                         float(tp.get("lat")), float(tp.get("lon")),
                         float(e.text) if e is not None and e.text else None))
    if not rows:
        raise ValueError(f"no timestamped track points in {paths}")
    rows.sort(key=lambda r: r[0])
    ele = [r[3] for r in rows]
    known = [i for i, v in enumerate(ele) if v is not None]
    if not known:
        raise ValueError(f"GPX has no elevation: {paths}")
    for i, v in enumerate(ele):             # the odd missing <ele>: carry the nearest known
        if v is None:
            j = bisect.bisect_left(known, i)
            ele[i] = ele[known[min(j, len(known) - 1)]]
    t = [r[0] for r in rows]
    if smooth_s:
        ele = smooth(t, ele, smooth_s)
    lat, lng = [r[1] for r in rows], [r[2] for r in rows]
    return {"t": t, "lat": lat, "lng": lng, "ele": ele,
            "x": geo.cumdist(list(zip(lat, lng)))}


def _at(trk, i):
    return {"x": trk["x"][i], "ele": trk["ele"][i], "lat": trk["lat"][i], "lng": trk["lng"][i]}


def locate(trk, t, lat, lng):
    """Where on the track was the observer at time t? Interpolates the track at t;
    if that lands far from the obs fix (clock offset, obs outside the recording), falls
    back to the nearest track point within a few hours of t — not the nearest overall,
    since a circuit retraces its approach trail. Returns x/ele/lat/lng + how + off (m)."""
    T = trk["t"]
    if T[0] <= t <= T[-1]:
        b = max(1, bisect.bisect_left(T, t))
        a = b - 1
        span = (T[b] - T[a]).total_seconds()
        f = (t - T[a]).total_seconds() / span if span else 0.0
        pos = {k: trk[k][a] + f * (trk[k][b] - trk[k][a]) for k in ("x", "ele", "lat", "lng")}
        off = geo.hav(lat, lng, pos["lat"], pos["lng"])
        if off <= TIME_TOL_M:
            return dict(pos, how="time", off=off)
    w = datetime.timedelta(seconds=NEAR_WINDOW_S)
    idx = range(bisect.bisect_left(T, t - w), bisect.bisect_right(T, t + w)) or range(len(T))
    j = min(idx, key=lambda k: geo.hav(lat, lng, trk["lat"][k], trk["lng"][k]))
    return dict(_at(trk, j), how="near", off=geo.hav(lat, lng, trk["lat"][j], trk["lng"][j]))


def ascent(ele, band=3.0):
    """Total climb with a dead-band, so altimeter jitter on flat ground isn't summed."""
    up, ref = 0.0, ele[0]
    for e in ele[1:]:
        if e - ref >= band:
            up += e - ref
            ref = e
        elif ref - e >= band:
            ref = e
    return up


def stats(trk):
    return {"km": trk["x"][-1] / 1000, "peak": max(trk["ele"]), "low": min(trk["ele"]),
            "ascent": ascent(trk["ele"]), "start": trk["ele"][0], "end": trk["ele"][-1]}


def decimate(trk, step=25.0):
    """[[lat, lng, x, ele], ...] every ~step metres along the track (ends and the
    summit kept) — dense enough to draw, small enough to inline in the page."""
    top = max(range(len(trk["ele"])), key=trk["ele"].__getitem__)
    keep, last = [], None
    for i, x in enumerate(trk["x"]):
        if last is None or x - last >= step or i == top or i == len(trk["x"]) - 1:
            keep.append([round(trk["lat"][i], 5), round(trk["lng"][i], 5),
                         round(x, 1), round(trk["ele"][i], 1)])
            last = x
    return keep
