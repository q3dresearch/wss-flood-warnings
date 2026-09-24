#!/usr/bin/env python3
"""Pull every Internet Archive memento of the warnings endpoint into a local cache.

    python3 fetch_mementos.py [--cache DIR]

**Why this exists.** The backfill figures in this repo were built from a memento
directory that lived in /tmp. /tmp was cleared, and with it went the only copy of
the input -- so four PUBLISHED figures could not be rebuilt by anyone, including
us. The fetch step had never been committed, only the analysis that consumed it.

The mementos themselves are not perishable; they are in the Archive. What was lost
was the cache, and a cache that costs 57 network round trips to rebuild is not
temporary. It now lands beside the artifact, in .cache/ (gitignored), and this
script is committed so the path from the Archive to the figure is unbroken.
"""
from __future__ import annotations
import argparse, gzip, json, pathlib, sys, time, urllib.parse, urllib.request

URL = "https://environment.data.gov.uk/flood-monitoring/id/floods"
UA = "wss-flood-warnings/1.0 (+https://github.com/q3dresearch/wss-flood-warnings)"
# NO collapse=digest. Collapsing drops captures whose body is byte-identical to
# the previous one, and the headline measurement in this repo is the GAP BETWEEN
# CAPTURES against a 24 h deletion window. Dropping a capture because its content
# repeated lengthens the gap on either side of it and flatters the archive's
# coverage. A capture is an observation event whether or not the register moved.
# Collapsed, this endpoint reports 52 captures; uncollapsed it is 55.
CDX = ("https://web.archive.org/cdx/search/cdx?url={u}&output=json"
       "&fl=timestamp,statuscode,digest&filter=statuscode:200")


def get(url: str, tries: int = 4) -> bytes:
    for i in range(tries):
        try:
            rq = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(rq, timeout=90) as r:
                body = r.read()
            # The Archive serves Content-Encoding: gzip on its recent captures and
            # urllib does not decompress it. Left unhandled this raised
            # UnicodeDecodeError on exactly the FOUR MOST RECENT captures -- the
            # ones nearest the present and least replaceable -- while every older
            # capture succeeded, so the loss looked like sparse recent coverage
            # rather than a bug in the client.
            if body[:2] == b"\x1f\x8b":
                body = gzip.decompress(body)
            return body
        except Exception as e:                                  # noqa: BLE001
            if i == tries - 1:
                raise
            print(f"    retry {i+1}/{tries-1}: {e}", file=sys.stderr)
            time.sleep(4 * (i + 1))
    raise AssertionError("unreachable")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default=str(pathlib.Path(__file__).resolve().parents[1] / ".cache" / "mementos"))
    a = ap.parse_args()
    out = pathlib.Path(a.cache); out.mkdir(parents=True, exist_ok=True)

    rows = json.loads(get(CDX.format(u=urllib.parse.quote(URL, safe=""))))
    stamps = [r[0] for r in rows[1:]]
    print(f"  CDX lists {len(stamps)} captures with status 200 "
          f"({len(set(r[2] for r in rows[1:]))} distinct digests)")

    got = skip = fail = 0
    for i, ts in enumerate(stamps, 1):
        f = out / f"{ts}.json.gz"
        if f.exists():
            skip += 1
            continue
        try:
            # id_ suffix = the ORIGINAL bytes, without the Archive's banner rewrite.
            body = get(f"https://web.archive.org/web/{ts}id_/{URL}")
            # A rewritten HTML error page is not a memento, and neither is a body
            # that will not decode -- one 2026 capture came back as undecodable
            # bytes and would otherwise have been stored as a real observation.
            json.loads(body.decode("utf-8"))
            f.write_bytes(gzip.compress(body))
            got += 1
        except Exception as e:                                  # noqa: BLE001
            fail += 1
            print(f"    [{i}/{len(stamps)}] {ts} FAILED: {type(e).__name__}", file=sys.stderr)
        time.sleep(1.1)
    print(f"  fetched {got}, already cached {skip}, failed {fail} -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
