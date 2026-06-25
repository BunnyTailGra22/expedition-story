"""iNaturalist taxonomy enrichment (global): family & genus — Latin name plus
localized 中文 common name — for any taxon worldwide, read from each taxon's
`ancestors`. Use this instead of `taicol` when a journey falls outside TaiCoL's
Taiwan scope (e.g. an overseas trek). Cached on disk; batches /v1/taxa (≤30 ids).
"""
import json, os, time, urllib.request, urllib.parse

API = "https://api.inaturalist.org/v1/taxa/"


def _anc(ancestors, rank):
    return next((a for a in ancestors if a.get("rank") == rank), None)


def enrich(tids, cache_path, locale="zh-TW"):
    """tids: iterable of iNat taxon ids. Returns {str(tid): {fam_sci, fam_zh,
    gen_sci, gen_zh, iconic}}. Only un-cached ids hit the API."""
    cache = json.load(open(cache_path)) if os.path.exists(cache_path) else {}
    want = [str(t) for t in tids if t is not None]
    miss = [t for t in dict.fromkeys(want) if t not in cache]
    for i in range(0, len(miss), 30):
        batch = miss[i:i + 30]
        url = API + ",".join(batch) + "?" + urllib.parse.urlencode({"locale": locale})
        try:
            d = json.load(urllib.request.urlopen(url, timeout=40))
        except Exception as e:
            print("inat taxa fetch failed:", e)
            continue
        for r in d.get("results", []):
            anc = r.get("ancestors") or []
            fam, gen = _anc(anc, "family"), _anc(anc, "genus")
            cache[str(r["id"])] = {
                "fam_sci": fam.get("name") if fam else None,
                "fam_zh": fam.get("preferred_common_name") if fam else None,
                "gen_sci": gen.get("name") if gen else (r.get("name") or "").split(" ")[0],
                "gen_zh": gen.get("preferred_common_name") if gen else None,
                "iconic": r.get("iconic_taxon_name"),
            }
        time.sleep(1)
    os.makedirs(os.path.dirname(cache_path), exist_ok=True)
    json.dump(cache, open(cache_path, "w"), ensure_ascii=False, indent=2)
    return {t: cache.get(t, {}) for t in want}
