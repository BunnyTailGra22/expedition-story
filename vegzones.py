#!/usr/bin/env python3
"""Vegetation-zone comparison figure for an overseas journey: Taiwan's altitudinal
zones beside the visited region's, on one shared elevation axis, with one blue dot
per observation of this journey. Writes journeys/<id>/vegzones.png (white
background), which generate.py copies into site/<id>/.

  python3 vegzones.py --journey yari-hotaka-circuit-2026-trek

Zones come from journeys/<id>/vegzones.json; observation elevations are read from
the already-generated site/<id>/index.html, so run generate.py first. Needs
matplotlib (an authoring tool only — the site itself stays dependency-free)."""
import argparse, json, os, re

import logging
import matplotlib
matplotlib.use("Agg")
logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)
import matplotlib.pyplot as plt
from matplotlib import font_manager

HERE = os.path.dirname(os.path.abspath(__file__))
INK, MUTED, FAINT, GRID = "#2E333B", "#7B848F", "#A3ACB9", "#C8D0D9"
BLUE, ORANGE = "#1170AA", "#C85200"
# zone fills: one grey ramp, lighter toward the cold summit zones
RAMP = ["#C8D0D9", "#D3D9E0", "#DDE2E8", "#E6EAEE", "#EEF1F4", "#F5F7F9", "#FAFBFC"]
FONTS = ["Segoe UI", "Noto Sans TC", "Noto Sans CJK TC", "WenQuanYi Zen Hei", "DejaVu Sans"]


def observations(jid):
    html = open(os.path.join(HERE, "site", jid, "index.html"), encoding="utf-8").read()
    data = json.loads(re.search(r"var DATA=(\[.*?\]);\n", html, re.S).group(1))
    return [(p["y"], p["u"].rstrip("/").split("/")[-1]) for p in data if p.get("y") is not None]


def column(ax, x, w, zones, top, treeline, ymax):
    for i, (lo, hi, name, note) in enumerate(zones):
        hi = min(hi, top)
        ax.add_patch(plt.Rectangle((x, lo), w, hi - lo, facecolor=RAMP[i % len(RAMP)],
                                   edgecolor="white", linewidth=2))
        thin = (hi - lo) / ymax < 0.1          # too short for two lines: name and note side by side
        ax.text(x + 0.03, (lo + hi) / 2, f"{name}　{note}" if thin else f"{name}\n{note}", va="center",
                ha="left", fontsize=10.5 if not thin else 9.5, color=INK, linespacing=1.35)
    ax.plot([x, x + w], [treeline, treeline], color=ORANGE, linewidth=2.2, solid_capstyle="butt")
    ax.text(x + w - 0.02, treeline - ymax * 0.008, f"森林線 約 {treeline:,} m", ha="right", va="top",
            fontsize=10, color=ORANGE, fontweight="bold")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--journey", required=True)
    jid = ap.parse_args().journey
    cfg = json.load(open(os.path.join(HERE, "journeys", jid, "vegzones.json"), encoding="utf-8"))
    obs = observations(jid)
    hidden = set(cfg.get("unreliable_obs_ids", []))
    top = cfg["ymax"]

    plt.rcParams["font.family"] = [f for f in FONTS if any(f == e.name for e in font_manager.fontManager.ttflist)] or ["sans-serif"]
    fig = plt.figure(figsize=(10, 6.6), dpi=200, facecolor="white")
    ax = fig.add_axes([0.085, 0.13, 0.89, 0.74])
    ax.set_facecolor("white")
    tw, ov = cfg["taiwan"], cfg["region"]
    column(ax, 0.0, 1.0, tw["zones"], tw["top"], tw["treeline"], top)
    column(ax, 1.15, 1.0, ov["zones"], ov["top"], ov["treeline"], top)
    # observation strip: a deterministic jitter so dots at one elevation don't stack
    x0, x1 = 2.35, 2.95
    pts = sorted(obs)
    for i, (e, oid) in enumerate(pts):
        x = x0 + (x1 - x0) * ((i * 0.618034) % 1.0)
        if oid in hidden:
            ax.scatter([x], [e], s=34, facecolor="white", edgecolor=MUTED, linewidth=1.3, zorder=3)
        else:
            ax.scatter([x], [e], s=34, facecolor=BLUE, edgecolor="white", linewidth=0.8, zorder=3)
    if tw.get("peak"):
        ax.text(0.97, tw["top"] - top * 0.008, tw["peak"], ha="right", va="top", fontsize=9.5, color=MUTED)

    for x, label in ((0.5, tw["label"]), (1.65, ov["label"]), ((x0 + x1) / 2, cfg["obs_label"])):
        ax.text(x, top * 1.015, label, ha="center", va="bottom", fontsize=12, color=INK, fontweight="bold")
    ax.set_xlim(-0.02, 3.0)
    ax.set_ylim(0, top)
    ax.set_xticks([])
    ax.set_yticks(range(0, top + 1, cfg.get("ystep", 500)))
    ax.set_yticklabels([f"{v:,} m" for v in range(0, top + 1, cfg.get("ystep", 500))], fontsize=10, color=MUTED)
    ax.tick_params(axis="y", length=0)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.yaxis.grid(True, color=GRID, linewidth=0.6)
    ax.set_axisbelow(True)

    legend = [plt.Line2D([], [], marker="o", linestyle="", markersize=7, markerfacecolor=BLUE,
                         markeredgecolor="white", label=cfg["dot_legend"])]
    if hidden:
        legend.append(plt.Line2D([], [], marker="o", linestyle="", markersize=7, markerfacecolor="white",
                                 markeredgecolor=MUTED, label="座標被模糊，海拔不可信"))
    legend.append(plt.Line2D([], [], color=ORANGE, linewidth=2.2, label="森林線"))
    fig.legend(handles=legend, loc="lower left", bbox_to_anchor=(0.085, 0.045), ncol=len(legend),
               frameon=False, fontsize=10, labelcolor=INK, handletextpad=0.4, columnspacing=1.6)
    fig.text(0.085, 0.94, cfg["takeaway"], fontsize=13.5, color=INK, fontweight="bold")
    fig.text(0.085, 0.012, cfg["source"], fontsize=8.5, color=MUTED)
    out = os.path.join(HERE, "journeys", jid, "vegzones.png")
    fig.savefig(out, facecolor="white")
    print(f"wrote {out} · {len(pts)} observations")


if __name__ == "__main__":
    main()
