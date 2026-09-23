#!/usr/bin/env python3
"""Of every warning seen standing down, how many were seen there twice."""
import json, pathlib, sys
import plate
from plate import INK, INK2, MUTED, GRID, FAINT, RULE

W = 880
SERIES = "#2f6f5e"
COLS, R, PITCH = 43, 3.4, 13.2


def main():
    here = pathlib.Path(__file__).resolve()
    st = json.load(open(sys.argv[1]))
    total, twice = st["warnings_at_level4"], st["warnings_at_level4_twice"]
    rows = -(-total // COLS)
    H = 300 + rows * PITCH

    s = plate.open_svg(W, H,
        f"Of {total:,} warnings seen standing down, {twice} were seen there twice",
        subtitle="One mark per warning observed at severityLevel 4, \"Warning no longer in force\", "
                 "in 55 archived captures spanning 2017-2026.")
    f, y = plate.frame(W, 88,
        who="Anyone deciding whether the stand-down-to-deletion window is worth measuring",
        decide="Measure the window by capturing hourly, or treat it as permanently unknowable",
        wrong="A large share of stood-down warnings appear in two or more captures")
    s += f

    x0, top = 78, y + 34
    for i in range(total):
        cx = x0 + (i % COLS) * PITCH
        cy = top + (i // COLS) * PITCH
        seen_twice = i < twice
        s.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{R}" '
                 f'fill="{SERIES if seen_twice else FAINT}" '
                 f'fill-opacity="{1.0 if seen_twice else 0.5}"/>')

    lx = x0 + COLS * PITCH + 26
    s += plate.halo(lx, top + 6, f"{twice}  seen twice", size=12.5, fill=SERIES)
    s.append(plate.txt(lx + 2, top + 22, "the window is bounded", size=10.5, fill=MUTED))
    s += plate.halo(lx, top + 52, f"{total-twice:,}  seen once", size=12.5, fill=INK2)
    s += plate.wrap(lx + 2, top + 68,
        "stood down at some point between one capture and the next -- the window "
        "is bounded only by the gap, which has a median of 31 days",
        size=10.5, fill=MUTED, chars=24, leading=12.5)

    bot = top + rows * PITCH
    s += plate.halo(x0, bot + 34, f"{100*twice/total:.1f}% of the base", size=13, fill=INK)
    s.append(f'<line x1="28" y1="{bot+48:.1f}" x2="{W-28}" y2="{bot+48:.1f}" stroke="{RULE}"/>')
    s += plate.wrap(28, bot + 64,
        f"Environment Agency flood-monitoring API via Internet Archive, read 2026-09-23. Base is "
        f"{total:,} distinct (flood area, warning number) pairs observed at severityLevel 4 across "
        f"55 mementos; 2 further mementos could not be refetched and are untested, not absent.",
        size=10, fill=MUTED, chars=132, leading=13)
    s.append("</svg>")

    out = here.parents[1] / "charts" / "deletion-window.svg"
    out.write_text("\n".join(s), encoding="utf-8")
    print(f"  wrote {out.name}  ({twice}/{total} = {100*twice/total:.1f}%, {rows} rows)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
