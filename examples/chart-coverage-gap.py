#!/usr/bin/env python3
"""Gap between consecutive archived captures, against the publisher's deletion window."""
import json, math, pathlib, sys
import plate
from plate import INK, INK2, MUTED, RULE, GRID, FAINT

W, H = 880, 520
SERIES = "#2f6f5e"   # the gaps
ALERT  = "#b4472e"   # the 24h window -- the thing being violated
R = 4.3


def xlog(v, x0, x1, lo, hi):
    return x0 + (math.log10(max(v, lo)) - math.log10(lo)) / (math.log10(hi) - math.log10(lo)) * (x1 - x0)


def beeswarm(xs, top, bot):
    """Deterministic: each point takes the free slot nearest the axis.

    Two bugs are fixed here and both are worth naming. The first version placed y
    by `i * 37 % band`, which stacked the 741-759 h cluster into a vertical stripe
    that read as a drawing artefact rather than as density. The second version
    searched outward with an UNBOUNDED counter, so once the band was full no slot
    ever satisfied the bounds test again and it spun forever. The search is now
    bounded by how many slots the band actually holds, and falls back to the
    midline rather than not terminating.
    """
    pitch = 2 * R + 1.4
    kmax = max(1, int((bot - top) / (2 * pitch)))
    mid = (top + bot) / 2
    placed, out = [], []
    for x in xs:
        chosen = mid
        for k in range(kmax + 1):
            cands = (mid,) if k == 0 else (mid + k * pitch, mid - k * pitch)
            hit = next((y for y in cands
                        if top + R <= y <= bot - R
                        and all((x - px) ** 2 + (y - py) ** 2 >= (2 * R + 0.8) ** 2
                                for px, py in placed)), None)
            if hit is not None:
                chosen = hit
                break
        placed.append((x, chosen)); out.append(chosen)
    return out


def main():
    here = pathlib.Path(__file__).resolve()
    stats = json.load(open(sys.argv[1]))
    gaps = sorted(stats["gaps_h"])
    n = len(gaps)
    within = sum(1 for g in gaps if g <= 24)
    med = gaps[n // 2]

    lo, hi = 0.5, 40000.0
    x0, x1 = 78, W - 46
    s = plate.open_svg(W, H,
        "The archive samples this register every 31 days. It deletes every 24 hours.",
        subtitle=f"Hours between consecutive Internet Archive captures of "
                 f"/flood-monitoring/id/floods. One mark per gap, n={n}.")
    f, y = plate.frame(W, 88,
        who="Anyone deciding whether to fund an hourly capture of a public register",
        decide="Capture this register hourly, or rely on the Internet Archive already holding it",
        wrong="Most gaps fall inside the 24-hour window, which would mean the archive already tracks it")
    s += f

    top, bot = y + 34, H - 128
    for e in range(0, 5):
        gx = xlog(10 ** e, x0, x1, lo, hi)
        s.append(f'<line x1="{gx:.1f}" y1="{top}" x2="{gx:.1f}" y2="{bot}" stroke="{GRID}"/>')
        # dy, not baseline-shift: cairosvg ignores baseline-shift and renders "10 3"
        s.append(f'<text x="{gx:.1f}" y="{bot+18}" font-size="10.5" fill="{MUTED}" text-anchor="middle" '
                 f'style="font-variant-numeric: tabular-nums">10<tspan dy="-5" '
                 f'font-size="7.5">{e}</tspan></text>')
    s.append(plate.txt((x0 + x1) / 2, bot + 40, "hours between captures", size=10.5, fill=MUTED, anchor="middle"))

    wx = xlog(24, x0, x1, lo, hi)
    s.append(f'<rect x="{x0}" y="{top}" width="{wx-x0:.1f}" height="{bot-top}" fill="{ALERT}" opacity="0.07"/>')
    s.append(f'<line x1="{wx:.1f}" y1="{top-10}" x2="{wx:.1f}" y2="{bot}" stroke="{ALERT}" stroke-width="2"/>')
    s += plate.halo(wx + 7, top - 1, "24 h — the publisher's deletion window", size=11, fill=ALERT)

    xs = [xlog(g, x0, x1, lo, hi) for g in gaps]
    ys = beeswarm(xs, top + 14, bot - 26)
    for g, cx, cy in zip(gaps, xs, ys):
        inside = g <= 24
        s.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{R}" fill="{ALERT if inside else SERIES}" '
                 f'fill-opacity="{0.95 if inside else 0.6}" stroke="{plate.SURFACE}" stroke-width="1.1"/>')

    mx = xlog(med, x0, x1, lo, hi)
    s.append(f'<line x1="{mx:.1f}" y1="{top-10}" x2="{mx:.1f}" y2="{bot}" stroke="{INK}" stroke-width="1.4" '
             f'stroke-dasharray="4 3"/>')
    s += plate.halo(mx + 8, bot - 8, f"median {med:,.0f} h  ({med/24:.0f} days)", size=11.5, fill=INK)
    s += plate.halo(x0 + 6, bot - 8, f"{within} of {n} gaps land inside the window", size=11.5, fill=ALERT)

    s.append(f'<line x1="28" y1="{H-62:.1f}" x2="{W-28}" y2="{H-62:.1f}" stroke="{RULE}"/>')
    s += plate.wrap(28, H - 46,
        f"Environment Agency flood-monitoring API, Internet Archive CDX, read 2026-09-23. "
        f"55 of 57 mementos parsed; 2 could not be refetched and are untested, not absent. "
        f"Median gap {med:,.0f} h against a documented 24 h deletion window — a factor of {med/24:.0f}.",
        size=10, fill=MUTED, chars=132, leading=13)
    s.append("</svg>")

    out = here.parent / "charts" / "coverage-gap.svg"
    out.write_text("\n".join(s), encoding="utf-8")
    print(f"  wrote {out.name}  ({n} gaps, {within} inside, median {med:,.0f}h)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
