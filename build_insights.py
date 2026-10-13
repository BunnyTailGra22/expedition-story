#!/usr/bin/env python3
"""Build journeys/<id>/insights.html (the page's 「AI彙整，待查證」 section) from a
compact, hand-curated spec module journeys/<id>/insights_spec.py.

  python3 build_insights.py --journey south3-2025-trek
  python3 build_insights.py --journey south3-2025-trek --check   # diff only, write nothing

The spec is plain Python data, written from the insights_data.py report:
  ID, SOURCES          journey id; data-source line for the HTML comment
  KEY                  three key findings (HTML strings), shown first
  HAB_NOTE, HAB        habitat × genus table: (habitat, "n 筆・m–m m<br>km …", genera, traits)
  FAM_NOTE, FAM        family table: (科, 屬, 種（筆・海拔）, 生態特色, 花／果期, 狀態);
                       consecutive rows of one 科 / 屬 are merged with rowspan
  HIDDEN_TITLE, HIDDEN, HIDDEN_NOTE   optional list of obscured, off-map observations
generate.py inlines the resulting fragment as-is; rerun generate.py afterwards."""
import argparse, difflib, importlib.util, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))


def load(path):
    spec = importlib.util.spec_from_file_location("insights_spec", path)
    s = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(s)
    return s


def rowspan(n):
    return f' rowspan="{n}"' if n > 1 else ""


def build(s):
    o = [f"<!-- Insights for {s.ID}. Hand-curated HTML fragment, inlined by generate.py\n"
         f"     into the page's third section (AI彙整，待查證). {s.SOURCES} -->"]
    o.append('<ol class="ins-key">')
    o += [f"  <li>{k}</li>" for k in s.KEY]
    o.append("</ol>\n")

    o.append("<h3>依棲地 × 屬</h3>")
    o.append(f'<p class="ins-note">{s.HAB_NOTE}</p>')
    o.append('<div class="tbl"><table class="t-hab">\n<colgroup><col style="width:22%"><col style="width:46%">'
             '<col style="width:32%"></colgroup>')
    o.append("<thead><tr><th>棲地（筆數・海拔）</th><th>屬：物種</th><th>特性</th></tr></thead>\n<tbody>")
    for name, sub, gens, trait in s.HAB:
        o.append(f"<tr><td><b>{name}</b><br>{sub}</td><td>{gens}</td><td>{trait}</td></tr>")
    o.append("</tbody></table></div>\n")

    o.append("<h3>依科別：屬、種、生態、花果期、保育等級</h3>")
    o.append(f'<p class="ins-note">{s.FAM_NOTE}</p>')
    o.append('<div class="tbl"><table class="t-fam">\n<colgroup><col style="width:9%"><col style="width:10%">'
             '<col style="width:20%"><col style="width:32%"><col style="width:16%"><col style="width:13%"></colgroup>')
    o.append("<thead><tr><th>科</th><th>屬</th><th>種（筆・海拔）</th><th>生態特色</th><th>花／果期</th>"
             "<th>狀態</th></tr></thead>\n<tbody>")
    F = s.FAM
    for i, (fam, gen, sp, eco, phen, st) in enumerate(F):
        cells = []
        if i == 0 or F[i - 1][0] != fam:
            n = 1
            while i + n < len(F) and F[i + n][0] == fam:
                n += 1
            cells.append(f"<td{rowspan(n)}><b>{fam}</b></td>")
        if i == 0 or F[i - 1][0] != fam or F[i - 1][1] != gen:
            n = 1
            while i + n < len(F) and F[i + n][0] == fam and F[i + n][1] == gen:
                n += 1
            cells.append(f"<td{rowspan(n)}>{gen}</td>")
        cells += [f"<td>{sp}</td>", f"<td>{eco}</td>", f"<td>{phen}</td>", f"<td>{st}</td>"]
        o.append("<tr>" + "".join(cells) + "</tr>")
    o.append("</tbody></table></div>")

    if getattr(s, "HIDDEN", None):
        o.append(f'\n<h3>{s.HIDDEN_TITLE}</h3>\n<ul class="ins-list">')
        o += [f"  <li>{h}</li>" for h in s.HIDDEN]
        o.append("</ul>")
        if getattr(s, "HIDDEN_NOTE", ""):
            o.append(f'<p class="ins-note">{s.HIDDEN_NOTE}</p>')
    return "\n".join(o) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--journey", required=True)
    ap.add_argument("--spec", help="spec module (default journeys/<id>/insights_spec.py)")
    ap.add_argument("--out", help="output (default journeys/<id>/insights.html)")
    ap.add_argument("--check", action="store_true", help="show the diff against the current file; write nothing")
    a = ap.parse_args()
    jdir = os.path.join(HERE, "journeys", a.journey)
    s = load(a.spec or os.path.join(jdir, "insights_spec.py"))
    html = build(s)
    out = a.out or os.path.join(jdir, "insights.html")
    if a.check:
        old = open(out, encoding="utf-8").read() if os.path.exists(out) else ""
        diff = list(difflib.unified_diff(old.splitlines(), html.splitlines(), out, "(spec)", lineterm=""))
        print("\n".join(diff) if diff else f"{out} is up to date")
        sys.exit(1 if diff else 0)
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"wrote {out} · {len(s.HAB)} habitat rows · {len(s.FAM)} family rows")


if __name__ == "__main__":
    main()
