"""TaiCoL (Catalogue of Life in Taiwan) enrichment: Taiwan-accepted name, family &
genus (Chinese + Latin), endemism, IUCN / national Red List. Cached on disk;
seeded from the sibling update-erge-phenology skill cache so only new species hit
the API."""
import json, os, subprocess, urllib.parse, time

SKILL_CACHE = os.path.expanduser("~/.claude/skills/update-erge-phenology/taicol_cache.json")


def _curl(u):
    return subprocess.run(["curl", "-s", "--max-time", "25", "-H",
                           "User-Agent: expedition-story/1.0", u], capture_output=True, text=True).stdout


def _taicol(common=None, sci=None):
    q = ("common_name=" + urllib.parse.quote(common)) if common else ("scientific_name=" + urllib.parse.quote(sci))
    try:
        d = json.loads(_curl("https://api.taicol.tw/v2/taxon?" + q))
    except Exception:
        return None
    recs = d.get("data", [])
    acc = [r for r in recs if r.get("taxon_status") == "accepted"] or recs
    tw = [r for r in acc if r.get("is_in_taiwan")] or acc
    for want in ("Species", "Variety", "Subspecies", "Genus"):
        for r in tw:
            if r.get("rank") == want:
                return r
    return tw[0] if tw else None


def _lineage(tid):
    try:
        d = json.loads(_curl("https://api.taicol.tw/v2/higherTaxa?taxon_id=" + tid))
    except Exception:
        return {}
    out = {}
    for t in d.get("data", []):
        if t.get("rank") == "Family":
            out["fam_zh"], out["fam_sci"] = t.get("common_name_c"), t.get("simple_name")
        elif t.get("rank") == "Genus":
            out["gen_zh"], out["gen_sci"] = t.get("common_name_c"), t.get("simple_name")
    return out


def _threat(iucn, rl):
    if iucn in {"CR", "EN", "VU", "NT"}:
        return iucn
    if rl and rl not in ("NLC", "NA", "NE", "DD", None):
        return rl
    return None


def enrich(species, cache_path):
    """species: {scientific: common}. Returns {scientific: {accepted_sci, fam_zh,
    fam_sci, gen_zh, gen_sci, is_endemic, iucn, redlist, threat, src}}."""
    cache = json.load(open(cache_path)) if os.path.exists(cache_path) else {}
    by_sci, by_zh = {}, {}
    if os.path.exists(SKILL_CACHE):
        for zh, v in json.load(open(SKILL_CACHE)).get("taicol", {}).items():
            if v.get("accepted_sci"):
                by_sci[v["accepted_sci"].lower()] = v
            by_zh[zh] = v
    for sci, common in species.items():
        if sci in cache:
            continue
        v = by_sci.get(sci.lower()) or (by_zh.get(common) if common else None)
        if v:
            e = {k: v.get(k) for k in ("accepted_sci", "accepted_zh", "fam_zh", "fam_sci",
                                       "gen_zh", "gen_sci", "iucn", "redlist", "protected")}
            e["is_endemic"] = bool(v.get("is_endemic"))
            e["src"] = "cache"
        else:
            rec = _taicol(sci=sci) or (_taicol(common=common) if common else None)
            if rec:
                e = {"accepted_sci": rec.get("simple_name"), "accepted_zh": rec.get("common_name_c"),
                     "is_endemic": bool(rec.get("is_endemic")), "iucn": rec.get("iucn"),
                     "redlist": rec.get("redlist"), "protected": rec.get("protected"), "src": "taicol"}
                e.update(_lineage(rec["taxon_id"]))
                time.sleep(0.4)
            else:
                e = {"accepted_sci": sci, "accepted_zh": common, "fam_zh": None, "fam_sci": None,
                     "gen_zh": None, "gen_sci": (sci or "").split(" ")[0], "is_endemic": False,
                     "iucn": None, "redlist": None, "protected": None, "src": "unresolved"}
        e["threat"] = _threat(e.get("iucn"), e.get("redlist"))
        cache[sci] = e
    os.makedirs(os.path.dirname(cache_path), exist_ok=True)
    json.dump(cache, open(cache_path, "w"), ensure_ascii=False, indent=2)
    return {sci: cache[sci] for sci in species}
