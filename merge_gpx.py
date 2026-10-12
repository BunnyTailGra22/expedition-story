#!/usr/bin/env python3
"""Merge per-day GPX files into one: a single <trk> with one <trkseg> per input
segment, ordered by first timestamp. Segments are copied verbatim (full precision,
device extensions kept), so the result round-trips into Garmin/Strava/etc.

  python3 merge_gpx.py D1.gpx D2.gpx ... -o merged.gpx --name "#YariHotakaCircuit"

--strip drops per-point <extensions> (heart rate, cadence, temperature): use it
for the copy committed under journeys/<id>/ — the engine needs only lat/lon/ele/time,
and the repo is public.
"""
import argparse, re, sys

SEG = re.compile(r"<trkseg>.*?</trkseg>", re.S)
TIME = re.compile(r"<time>([^<]+)</time>")
EXT = re.compile(r"\s*<extensions>.*?</extensions>", re.S)
ROOT = re.compile(r"<gpx\b[^>]*>", re.S)
XMLNS = re.compile(r'xmlns(?::[\w.-]+)?="[^"]*"')


def read(path):
    """-> (namespace declarations on <gpx>, [(first time, segment text), ...])"""
    txt = open(path, encoding="utf-8").read()
    segs = SEG.findall(txt)
    if not segs:
        sys.exit(f"{path}: no <trkseg> found")
    root = ROOT.search(txt)
    return (XMLNS.findall(root.group(0)) if root else [],
            [(TIME.search(s).group(1) if TIME.search(s) else "", s) for s in segs])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("gpx", nargs="+")
    ap.add_argument("-o", "--out", required=True)
    ap.add_argument("--name", default="merged track")
    ap.add_argument("--strip", action="store_true", help="drop per-point <extensions>")
    a = ap.parse_args()

    parsed = [read(p) for p in a.gpx]
    # carry every input's namespace declarations, so verbatim extensions stay valid
    ns = list(dict.fromkeys(['xmlns="http://www.topografix.com/GPX/1/1"',
                             'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"']
                            + [d for decl, _ in parsed for d in decl
                               if d.startswith("xmlns:") and not d.startswith("xmlns:xsi=")]))
    segs = sorted((s for _, ss in parsed for s in ss), key=lambda s: s[0])
    body = "\n    ".join(EXT.sub("", s) if a.strip else s for _, s in segs)
    name = a.name.replace("&", "&amp;").replace("<", "&lt;")
    gpx = f"""<?xml version="1.0" encoding="UTF-8"?>
<gpx creator="expedition-story merge_gpx.py" version="1.1"
  xsi:schemaLocation="http://www.topografix.com/GPX/1/1 http://www.topografix.com/GPX/11.xsd"
  {" ".join(ns)}>
  <metadata>
    <time>{segs[0][0]}</time>
  </metadata>
  <trk>
    <name>{name}</name>
    {body}
  </trk>
</gpx>
"""
    open(a.out, "w", encoding="utf-8").write(gpx)
    print(f"{a.out}: {len(segs)} segment(s) from {len(a.gpx)} file(s), "
          f"{gpx.count('<trkpt')} points{' (extensions stripped)' if a.strip else ''}")


if __name__ == "__main__":
    main()
