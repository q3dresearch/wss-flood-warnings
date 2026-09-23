#!/usr/bin/env python3
"""How many separate flood events each area shows, even under 31-day sampling."""
import json, pathlib, sys
import plate
from plate import INK, INK2, MUTED, GRID, FAINT, RULE

W, H = 880, 520
SERIES = "#2f6f5e"


def main():
    here = pathlib.Path(__file__).resolve()
    st = json.load(open(sys.argv[1]))
    dist = {int(k): v for k, v in st["events_per_area"].items()}
    areas = sum(dist.values())
    repeat = sum(v for k, v in dist.items() if k > 1)
    ks = sorted(dist)

    s = plate.open_svg(W, H,
        f"Even sampled once a month, {repeat:,} of {areas:,} flood areas flooded more than once",
        subtitle="Distinct flood events per area, counted by a change of warning number at the same "
                 "floodAreaID, across 55 archived captures 2017-2026.")
    f, y = plate.frame(W, 88,
        who="An insurer or loss adjuster pricing repeat flood exposure by location",
        decide="Whether flood-area identity carries signal worth accumulating over years",
        wrong="Almost every area appears exactly once, with no repeat tail")
    s += f

    x0, x1 = 150, W - 150
    top = y + 26
    rowh = (H - 96 - top) / len(ks)
    mx = max(dist.values())
    for i, k in enumerate(ks):
        v = dist[k]
        ry = top + i * rowh
        bw = (x1 - x0) * v / mx
        first = (k == 1)
        s.append(f'<rect x="{x0}" y="{ry:.1f}" width="{max(bw,2.0):.1f}" height="{rowh-4:.1f}" rx="3" '
                 f'fill="{FAINT if first else SERIES}" fill-opacity="{0.55 if first else 0.9}"/>')
        s.append(plate.txt(x0 - 12, ry + rowh / 2 + 1, f"{k}", size=11, fill=INK2, anchor="end"))
        s += plate.halo(x0 + max(bw, 2.0) + 8, ry + rowh / 2 + 1, f"{v:,}", size=11,
                        fill=INK2 if first else INK)
    s.append(plate.txt(x0 - 12, top - 12, "events", size=10, fill=MUTED, anchor="end"))
    s.append(plate.txt(x0, top - 12, "flood areas", size=10, fill=MUTED))

    s += plate.halo(x0, H - 74, f"{100*repeat/areas:.0f}% of areas flooded at least twice; "
                                f"one area appears in {max(ks)} separate events", size=12.5, fill=INK)
    s.append(f'<line x1="28" y1="{H-62:.1f}" x2="{W-28}" y2="{H-62:.1f}" stroke="{RULE}"/>')
    s += plate.wrap(28, H - 46,
        f"Environment Agency flood-monitoring API via Internet Archive, read 2026-09-23. Base is "
        f"{areas:,} distinct floodAreaIDs. This is a FLOOR, not a count: the archive samples every "
        f"31 days against warnings that last about a day, so events between captures are invisible.",
        size=10, fill=MUTED, chars=132, leading=13)
    s.append("</svg>")

    out = here.parents[1] / "charts" / "repeat-flooding.svg"
    out.write_text("\n".join(s), encoding="utf-8")
    print(f"  wrote {out.name}  ({repeat:,}/{areas:,} repeat, max {max(ks)} events)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
