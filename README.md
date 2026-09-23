# wss-flood-warnings — live UK flood warnings, captured hourly

Every flood alert and warning the Environment Agency has in force for England:
severity, flood area, county, river or sea, tidal status, and when it was raised
and last changed. Captured **every hour**, because the publisher deletes them
after about a day.

Read [registry/ea.flood.warnings.yml](registry/ea.flood.warnings.yml) first.

## Why this exists

The Environment Agency documents its own deletion, in its
[API reference](https://environment.data.gov.uk/flood-monitoring/doc/reference):

> approximately 24 hours after a warning has been in place for a flood area, the
> severity level will be set to 4, "Warning no Longer in Force", **before the
> warning response is removed altogether**.

So a flood warning has a life of roughly a day and then stops existing. Three
things follow, and each was checked rather than assumed.

**The agency's own archive does not keep them.** `/flood-monitoring/archive/`
holds 22 files, every one of them `readings-{date}.csv` or
`readings-full-{date}.csv`. Those are *measurements* — river levels, rainfall,
tide gauges. There is no warnings archive of any kind.

**The Internet Archive has not covered it either, and here is the number.**
57 distinct captures of the warnings endpoint across 2017–2026:

| year | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| captures | 11 | 18 | 13 | 1 | 3 | 0 | 0 | 2 | 6 | 3 |

One capture per 61 days against a 24-hour turnover. **Three captures in the
whole of 2026.** For contrast, the same measurement run against Apple's App
Store Review Guidelines returns about 1,950. Essentially every flood event
since 2017 is already gone.

**What is being lost is not small.** The largest memento the Archive did catch,
2020-02-17 during Storm Dennis, is 1,096,729 bytes and 760 live records:

| severity | records |
| --- | ---: |
| Flood Alert | 248 |
| Flood Warning | 193 |
| Warning no longer in force | 313 |
| Severe Flood Warning | 6 |

## The question this repo is built to answer

This register is unusual in having **both** a terminal status and a deletion,
about a day apart:

- `severityLevel: 4` — the EA has stood the warning down. A statement, in the data.
- the record disappears — the register has forgotten. Not a statement about anything.

**How long is the gap between them?** The publisher does not say. It cannot be
recovered from the archive, and it cannot be measured by any sampling interval
longer than the window itself. Counting the consecutive hourly captures in which
a flood area sits at severity 4 measures it directly. Query 2 in
[examples/queries.sql](examples/queries.sql) is that count.

## Why hourly, when the fleet floor is weekly

Because this source falsifies the rule rather than straining it. The fleet
samples from **how long a state persists**, not how often a publisher
republishes — and for wss-gho or wss-carbon-registry a state persists for
months, so weekly buys nothing over monthly. Here a state persists for about a
day. A weekly reading would catch roughly **one flood event in seven** and
report success on the other six.

The engine enforced the weekly floor in code until 2026-09-23. `hourly` was
added to `CADENCE_HOURS` for this source, and is offered **only** to sources
that can show the same thing: a documented or measured deletion window shorter
than a week. It is not a licence to poll anything else faster.

Hourly is affordable because the payload is honest: two fetches three seconds
apart are **byte-identical**, so there is no nonce, no served-at stamp and no
rotating id. Dedupe works with no `dedupe_ignore` at all, and an unchanged hour
costs one manifest line.

## An empty register is real data

Most hours of most years, nothing in England is flooding and the response is
703 bytes with `"items": []`. That is a measured national all-clear, **not a
failed fetch.** Nothing in the gates may require a flood field to be present;
what they require is the publisher's own metadata. And `max_shrink_pct` is set
to `100` — never fires — because the drop from a 1.1 MB storm to a 703-byte
quiet hour is a 99.94% shrink that happens after *every* flood event. A shrink
gate tight enough to be meaningful would quarantine exactly the captures that
record a flood **ending**.

## The entity is the flood area, not the warning number

`entity_id` is the `floodAreaID` (e.g. `053WAF113LWA`), because that is what
resolves to a published polygon with a county and a river — the identifier that
joins to geography and to a second flood at the same place years later. The
numeric warning id is carried as the `warning_id` metric instead.

**This has a cost, and it is paid up front:** two separate floods at one area
would otherwise look like a single long-lived entity. A changed `warning_id` at
an unchanged `floodAreaID` is a **new event**. Any series built from this must
break on `warning_id`, not on presence.

All three candidate keys were checked on the 760-record storm payload before the
parser was written: `floodAreaID`, `@id` and `(floodAreaID, timeRaised)` are each
760 distinct over 760 rows.

## Licence

The data is **Open Government Licence v3.0**, asserted by the publisher in
`meta.licence` on every response. Crawl permission was checked separately and
is a different question — see [LICENSE-DATA](LICENSE-DATA) for both, including
the robots evaluation.

> Contains public sector information licensed under the Open Government Licence
> v3.0. Source: Environment Agency flood-monitoring API.

## Layout

| path | what |
| --- | --- |
| `registry/ea.flood.warnings.yml` | the source definition, gates, and the reasoning |
| `parsers/floodwarning_v1.py` | schema `floodwarning.v1` → observations |
| `raw/`, `manifest/` | captured bytes and the append-only capture log |
| `derived/observations/` | long-format CSV, one row per metric per area per capture |
| `examples/queries.sql` | the five questions this data was captured to answer |

Derive runs weekly, so `derived/` lags the raw captures. The raw is hourly and
committed hourly; run `wss derive` locally for anything fresher.
