#!/usr/bin/env python3
"""Measure what the Internet Archive's mementos of this endpoint can and cannot answer.

    python3 backfill_stats.py <memento-dir> [--out stats.json]

Runs the REPO'S OWN parser (parsers/floodwarning_v1.py) over every archived capture of
/flood-monitoring/id/floods, so the numbers here describe the pipeline that ships rather
than a parallel one written to flatter it.

The question is not "is flood data interesting". It is narrower and it is falsifiable:
**can the existing archive already answer the questions this repo proposes to capture
for?** If it can, the capture is redundant and should not be run.
"""
from __future__ import annotations
import argparse, gzip, json, pathlib, sys
from collections import Counter, defaultdict
from datetime import datetime

HERE = pathlib.Path(__file__).resolve()
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "parsers"))
sys.path.insert(0, str(REPO.parent / "wss-engine"))
import floodwarning_v1 as P              # noqa: E402
from wss import derive                   # noqa: E402

CTX = derive.ParseContext.__new__(derive.ParseContext)
SEV = {1: "Severe Flood Warning", 2: "Flood Warning", 3: "Flood Alert", 4: "No longer in force"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("memento_dir")
    ap.add_argument("--out", default="")
    a = ap.parse_args()

    files = sorted(pathlib.Path(a.memento_dir).glob("*.json.gz"))
    caps = []
    for f in files:
        ts = datetime.strptime(f.name[:14], "%Y%m%d%H%M%S")
        obs = list(P.parse(gzip.decompress(f.read_bytes()), CTX))
        by_area: dict[str, dict] = defaultdict(dict)
        for o in obs:
            by_area[o.entity_id][o.metric] = o.value
        caps.append({"ts": ts, "areas": by_area, "n": len(by_area)})

    # ---- gaps between consecutive captures, against the documented ~24h window
    gaps_h = [ (caps[i + 1]["ts"] - caps[i]["ts"]).total_seconds() / 3600
               for i in range(len(caps) - 1) ]
    within = sum(1 for g in gaps_h if g <= 24)

    # ---- warning continuity. A warning is identified by (floodAreaID, warning_id):
    # a changed warning_id at the same area is a NEW event, not a continuing one.
    seen: dict[tuple, list] = defaultdict(list)
    for c in caps:
        for area, m in c["areas"].items():
            seen[(area, m.get("warning_id"))].append((c["ts"], m.get("severity_level")))
    once = sum(1 for v in seen.values() if len(v) == 1)

    # ---- THE CENTRAL QUESTION. A warning at severityLevel 4 has been stood down and is
    # awaiting deletion. Measuring that window needs the SAME warning observed at level 4
    # in at least two captures. How often does the archive manage it?
    at4 = {k: [(t, l) for t, l in v if l == 4] for k, v in seen.items()}
    at4 = {k: v for k, v in at4.items() if v}
    at4_multi = {k: v for k, v in at4.items() if len(v) > 1}

    # ---- repeat flooding: distinct events per area
    ev_per_area = Counter(area for (area, _wid) in seen)

    sev_by_cap = [Counter(int(m["severity_level"]) for m in c["areas"].values()
                          if m.get("severity_level") is not None) for c in caps]

    stats = {
        "n_mementos": len(caps),
        "span": [caps[0]["ts"].isoformat(), caps[-1]["ts"].isoformat()] if caps else [],
        "total_days": (caps[-1]["ts"] - caps[0]["ts"]).days if len(caps) > 1 else 0,
        "gaps_h": gaps_h,
        "gaps_within_24h": within,
        "gaps_n": len(gaps_h),
        "captures": [
            {"ts": c["ts"].isoformat(), "n": c["n"],
             "sev": {str(k): v for k, v in sorted(s.items())}}
            for c, s in zip(caps, sev_by_cap)
        ],
        "distinct_warnings": len(seen),
        "warnings_seen_once": once,
        "warnings_at_level4": len(at4),
        "warnings_at_level4_twice": len(at4_multi),
        "distinct_areas": len(ev_per_area),
        "areas_with_multiple_events": sum(1 for n in ev_per_area.values() if n > 1),
        "events_per_area": dict(Counter(ev_per_area.values())),
    }
    txt = json.dumps(stats, indent=1, sort_keys=True)
    if a.out:
        pathlib.Path(a.out).write_text(txt)

    print(f"  mementos            {stats['n_mementos']}  spanning {stats['total_days']:,} days")
    print(f"  gaps <= 24h         {within} of {len(gaps_h)}"
          f"  ({100*within/len(gaps_h):.1f}%)" if gaps_h else "")
    print(f"  distinct warnings   {stats['distinct_warnings']:,}")
    print(f"  seen ONCE only      {once:,}  ({100*once/max(1,len(seen)):.1f}%)")
    print(f"  ever at level 4     {stats['warnings_at_level4']:,}")
    print(f"  at level 4 TWICE    {stats['warnings_at_level4_twice']:,}"
          f"   <- the deletion window is measurable only for these")
    print(f"  distinct areas      {stats['distinct_areas']:,}"
          f"   repeat: {stats['areas_with_multiple_events']:,}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
