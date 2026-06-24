"""Geodesy helpers."""
import math


def hav(a1, o1, a2, o2):
    R = 6371000
    p1, p2 = math.radians(a1), math.radians(a2)
    dp, dl = math.radians(a2 - a1), math.radians(o2 - o1)
    x = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(x))


def cumdist(coords):
    """coords: [(lat,lng), ...] in walk order -> cumulative metres [0, ...]."""
    d, out = 0.0, [0.0]
    for i in range(1, len(coords)):
        d += hav(coords[i - 1][0], coords[i - 1][1], coords[i][0], coords[i][1])
        out.append(round(d, 1))
    return out
