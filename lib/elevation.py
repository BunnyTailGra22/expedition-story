"""SRTM 30 m elevation via Open Topo Data (bilinear), with a shared on-disk cache
keyed by rounded coordinate so repeated/overlapping points are never re-queried."""
import json, os, time, urllib.request, urllib.parse


def _key(la, ln):
    return f"{round(la, 6)},{round(ln, 6)}"


def sample(coords, cache_path):
    """coords: [(lat,lng), ...] -> [elevation_m or None, ...]."""
    cache = json.load(open(cache_path)) if os.path.exists(cache_path) else {}
    todo = list({_key(la, ln): (la, ln) for la, ln in coords if _key(la, ln) not in cache}.values())
    for i in range(0, len(todo), 100):
        batch = todo[i:i + 100]
        locs = "|".join(f"{la:.6f},{ln:.6f}" for la, ln in batch)
        try:
            url = "https://api.opentopodata.org/v1/srtm30m?" + urllib.parse.urlencode(
                {"locations": locs, "interpolation": "bilinear"})
            d = json.load(urllib.request.urlopen(url, timeout=40))
            if d.get("status") == "OK":
                for (la, ln), res in zip(batch, d["results"]):
                    cache[_key(la, ln)] = res["elevation"]
        except Exception as e:
            print("elevation fetch failed:", e)
        time.sleep(1)
    os.makedirs(os.path.dirname(cache_path), exist_ok=True)
    json.dump(cache, open(cache_path, "w"))
    return [cache.get(_key(la, ln)) for la, ln in coords]
