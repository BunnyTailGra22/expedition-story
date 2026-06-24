"""GPS quality control: flag fixes worse than ACC_THRESH and snap them to the
time-interpolated position between their nearest reliable neighbours (so a bad
fix doesn't inject a fake detour or a wrong DEM elevation)."""
ACC_THRESH = 100.0


def correct(rows):
    """rows: list of dicts with _t (datetime), lat, lng, acc — sorted by _t.
    Mutates in place: adds 'fl' (1 if acc>thresh) and corrected lat/lng."""
    for r in rows:
        r["olat"], r["olng"] = r["lat"], r["lng"]

    def good(i):
        return rows[i]["acc"] <= ACC_THRESH

    for i, r in enumerate(rows):
        if r["acc"] <= ACC_THRESH:
            r["fl"] = 0
            continue
        r["fl"] = 1
        L = i - 1
        while L >= 0 and not good(L):
            L -= 1
        R = i + 1
        while R < len(rows) and not good(R):
            R += 1
        a = rows[L] if L >= 0 else None
        b = rows[R] if R < len(rows) else None
        if a and b:
            span = (b["_t"] - a["_t"]).total_seconds() or 1
            f = (r["_t"] - a["_t"]).total_seconds() / span
            r["lat"] = a["olat"] + f * (b["olat"] - a["olat"])
            r["lng"] = a["olng"] + f * (b["olng"] - a["olng"])
        elif a:
            r["lat"], r["lng"] = a["olat"], a["olng"]
        elif b:
            r["lat"], r["lng"] = b["olat"], b["olng"]
    return rows
