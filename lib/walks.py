#!/usr/bin/env python3
"""Phase 1 of the generalized transect generator.

Fetch iNaturalist observations for a query (user × place × date-range) and
segment them into "walks" — contiguous single-path surveys — so each walk can
later become one elevation-transect HTML. A new walk starts on a new calendar
day, or when the within-day time gap exceeds `gap_min` minutes (generalizing the
14:56 break logic from the 二格山 baseline).

Importable:  segment(observations, gap_min) -> [walk, ...]
CLI (demo):  python3 lib/walks.py <user> <place_id> <d1> <d2> [gap_min]
"""
import sys, json, datetime, urllib.request, urllib.parse, time
from datetime import timezone, timedelta

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


def fetch(user, place_id, d1, d2):
    base = {"user_login": user, "place_id": str(place_id), "d1": d1, "d2": d2,
            "per_page": "200", "order_by": "observed_on", "order": "asc", "locale": "zh-TW"}
    out, page = [], 1
    while True:
        url = "https://api.inaturalist.org/v1/observations?" + urllib.parse.urlencode(dict(base, page=str(page)))
        d = json.load(urllib.request.urlopen(url))
        out.extend(d["results"])
        if len(out) >= d["total_results"] or not d["results"]:
            break
        page += 1
        time.sleep(1)
    return out


def segment(obs, gap_min=120):
    """Return list of walks; each = {date, start, end, span_min, n, obs:[...]}."""
    rows = [(o, _t(o)) for o in obs]
    rows = [(o, t) for o, t in rows if t]
    rows.sort(key=lambda r: r[1])
    walks, cur = [], []
    for o, t in rows:
        if cur:
            prev = cur[-1][1]
            same_day = t.date() == prev.date()
            small_gap = (t - prev).total_seconds() / 60 <= gap_min
            if not (same_day and small_gap):
                walks.append(cur)
                cur = []
        cur.append((o, t))
    if cur:
        walks.append(cur)
    result = []
    for w in walks:
        ts = [t for _, t in w]
        result.append({
            "date": ts[0].strftime("%Y-%m-%d"),
            "start": ts[0].strftime("%H:%M"), "end": ts[-1].strftime("%H:%M"),
            "span_min": round((ts[-1] - ts[0]).total_seconds() / 60),
            "n": len(w), "obs": [o for o, _ in w],
        })
    return result


def main():
    if len(sys.argv) < 5:
        print(__doc__)
        return
    user, place_id, d1, d2 = sys.argv[1:5]
    gap = int(sys.argv[5]) if len(sys.argv) > 5 else 120
    obs = fetch(user, place_id, d1, d2)
    walks = segment(obs, gap)
    print(f"query: user={user} place={place_id} {d1}..{d2}  →  {len(obs)} obs, "
          f"{len(walks)} walk(s) (gap_min={gap})\n")
    print(f"{'#':>2} {'date':10} {'time':>13} {'span':>6} {'obs':>4}  species")
    for i, w in enumerate(walks, 1):
        sp = len({(o.get('taxon') or {}).get('id') for o in w['obs'] if o.get('taxon')})
        print(f"{i:>2} {w['date']:10} {w['start']}–{w['end']:>5} {w['span_min']:>4}m {w['n']:>4}  {sp} spp")


if __name__ == "__main__":
    main()
