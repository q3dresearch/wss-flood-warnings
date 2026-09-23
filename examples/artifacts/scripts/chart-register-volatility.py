#!/usr/bin/env python3
"""How many warnings were in force at each archived capture."""
import json, math, pathlib, sys
from datetime import datetime
import plate
from plate import INK, INK2, MUTED, GRID, RULE, FAINT

W, H = 880, 536
SERIES = "#2f6f5e"
ZERO   = "#b4472e"


def main():
    here = pathlib.Path(__file__).resolve()
    st = json.load(open(sys.argv[1]))
    caps = [(datetime.fromisoformat(c["ts"]), c["n"]) for c in st["captures"]]
    caps.sort()
    zeros = sum(1 for _, n in caps if n == 0)
    mx = max(n for _, n in caps)
    med = sorted(n for _, n in caps)[len(caps) // 2]

    s = plate.open_svg(W, H,
        f"The same register reads zero at {zeros} captures and {mx} at another",
        subtitle=f"Flood warnings in force at each of {len(caps)} archived captures, 2017-2026. "
                 f"One mark per capture. Vertical scale is log(1+n) so a true zero is drawn.")
    f, y = plate.frame(W, 88,
        who="Anyone about to quote a number for how much of England is flooding",
        decide="Whether a single reading of this register can stand for a week or a month",
        wrong="Captures cluster around a typical value instead of spanning zero to hundreds")
    s += f

    x0, x1 = 78, W - 46
    top, bot = y + 48, H - 132
    t0, t1 = caps[0][0].timestamp(), caps[-1][0].timestamp()
    ymax = math.log1p(1000)

    def px(t): return x0 + (t.timestamp() - t0) / (t1 - t0) * (x1 - x0)
    def py(n): return bot - math.log1p(n) / ymax * (bot - top)

    for tick in (0, 1, 10, 100, 1000):
        gy = py(tick)
        s.append(f'<line x1="{x0}" y1="{gy:.1f}" x2="{x1}" y2="{gy:.1f}" stroke="{GRID}"/>')
        s.append(plate.txt(x0 - 10, gy + 3.5, f"{tick:,}", size=10.5, fill=MUTED, anchor="end"))
    s.append(plate.txt(x0 - 10, top - 30, "warnings", size=10, fill=MUTED, anchor="end"))
    s.append(plate.txt(x0 - 10, top - 19, "in force", size=10, fill=MUTED, anchor="end"))

    for yr in range(2017, 2027):
        t = datetime(yr, 1, 1)
        if not (t0 <= t.timestamp() <= t1):
            continue
        gx = px(t)
        s.append(f'<line x1="{gx:.1f}" y1="{top}" x2="{gx:.1f}" y2="{bot}" stroke="{GRID}"/>')
        s.append(plate.txt(gx, bot + 18, str(yr), size=10.5, fill=MUTED, anchor="middle"))

    # NO connecting line. A line between captures 31 days apart would assert a
    # trajectory through a register that empties and refills in a day.
    for t, n in caps:
        cx, cy = px(t), py(n)
        s.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="5" fill="{ZERO if n==0 else SERIES}" '
                 f'fill-opacity="{0.95 if n==0 else 0.62}" stroke="{plate.SURFACE}" stroke-width="1.2"/>')

    t, n = max(caps, key=lambda c: c[1])
    s += plate.halo(px(t) + 11, py(n) + 4, f"{n} — Storm Dennis, {t:%d %b %Y}", size=11.5, fill=INK)
    # Placed in the empty 2022-23 span at the zero row: the label sits ON the row it
    # describes without covering a single mark. Earlier positions put it across the
    # "1" gridline and over live dots.
    s += plate.halo(px(datetime(2022, 3, 1)), py(0) + 4,
                    f"{zeros} captures found the register empty — a real national all-clear",
                    size=11.5, fill=ZERO)
    s += plate.halo(x1, top + 6, f"median {med}", size=12, fill=INK2, anchor="end")

    s.append(f'<line x1="28" y1="{H-74:.1f}" x2="{W-28}" y2="{H-74:.1f}" stroke="{RULE}"/>')
    s += plate.wrap(28, H - 58,
        f"Environment Agency flood-monitoring API via Internet Archive, read 2026-09-23. "
        f"{len(caps)} of 57 mementos parsed; 2 could not be refetched and are untested, not absent. "
        f"Marks are deliberately not joined: consecutive captures are a median of 31 days apart, and "
        f"a line between them would assert a path the data cannot support.",
        size=10, fill=MUTED, chars=132, leading=13)
    s.append("</svg>")

    out = here.parents[1] / "charts" / "register-volatility.svg"
    out.write_text("\n".join(s), encoding="utf-8")
    print(f"  wrote {out.name}  ({len(caps)} captures, {zeros} zeros, max {mx}, median {med})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
