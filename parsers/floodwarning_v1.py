"""Parser for schema_id `floodwarning.v1` -- Environment Agency flood warnings.

WHAT MOVES HERE IS A WARNING BEING RETIRED, IN TWO STAGES

Most registers in this fleet have no terminal status, so a disappearance is the
only way an ending can be expressed. This one has both, and they are about a
day apart. The publisher's own reference says a warning's severity is set to 4,
"Warning no Longer in Force", roughly 24 hours after it was raised, and the row
"is removed altogether" some time after that.

So there are two distinct endings to tell apart, and they mean different things:

  severityLevel 4 present   -> the EA has stood the warning down. The flood is
                               over. This is a STATEMENT, and it is in the data.
  floodAreaID absent        -> the record has been deleted. This is not a
                               statement about the flood, it is the register
                               forgetting. Nothing outside a capture holds it.

`listed` is emitted once per area per capture so the second one is visible as
an absence. `severity_level` is emitted as a number so the first one is visible
as a value. Counting the consecutive captures in which an area sits at
severity_level 4 measures the deletion window the publisher does not document.

THE ENTITY IS THE floodAreaID, NOT THE WARNING NUMBER

`@id` ends in a numeric warning id (.../floods/111676). It is unique per
warning, but it means nothing outside this API and it does not survive the
warning. `floodAreaID` (e.g. 053WAF113LWA) resolves to a published flood-area
polygon with a county and a river, so it is the identifier that joins to
geography, to a second flood at the same place years later, and to anything a
user of this dataset already has.

That choice has a cost, and it is paid here rather than discovered later: two
separate floods at the same area would look like one long-lived entity. So the
warning number is emitted as `warning_id` and `time_raised` alongside it. A
changed warning_id at an unchanged floodAreaID is a NEW EVENT, not a continuing
one. Any series built from this must break on warning_id, not on presence.

Key uniqueness was checked before this was written, on the largest payload the
archive holds (2020-02-17, Storm Dennis, 760 items): floodAreaID, @id and
(floodAreaID, timeRaised) are each 760 distinct over 760 rows.

AN EMPTY RESPONSE IS NOT A PARSE FAILURE

Most hours of most years, no part of England is flooding and `items` is `[]`.
This parser yields nothing and raises nothing in that case, on purpose: a zero
here is a measurement, not a broken fetch. The gates in the registry are what
distinguish the two, by requiring the publisher's own metadata to be present.
"""
import json

from wss import derive

PARSER_VERSION = "1"
SCHEMA_ID = "floodwarning.v1"

# Straight passthrough -> metric name. Strings, kept as strings.
TEXT = {
    "severity": "severity",
    "description": "description",
    "eaAreaName": "ea_area_name",
    "eaRegionName": "ea_region_name",
    "timeRaised": "time_raised",
    "timeMessageChanged": "time_message_changed",
    "timeSeverityChanged": "time_severity_changed",
    "message": "message",
}

# Fields lifted out of the nested floodArea object.
AREA = {
    "county": "county",
    "riverOrSea": "river_or_sea",
    "polygon": "polygon_url",
}


def parse(body: bytes, ctx: derive.ParseContext):
    doc = json.loads(body)
    if not isinstance(doc, dict):
        return
    items = doc.get("items")
    # The API serves a bare object rather than a list when exactly one warning
    # is active. Normalising here keeps every downstream count honest -- without
    # it a single-warning hour parses as zero warnings.
    if isinstance(items, dict):
        items = [items]
    if not isinstance(items, list):
        return

    for r in items:
        if not isinstance(r, dict):
            continue
        entity = r.get("floodAreaID")
        if entity in (None, ""):
            continue
        entity = str(entity)

        yield derive.Observation(entity_id=entity, metric="listed", value=1, unit="count")

        # The orderable one: 1 severe, 2 warning, 3 alert, 4 no longer in force.
        level = r.get("severityLevel")
        if isinstance(level, int) and not isinstance(level, bool):
            yield derive.Observation(entity_id=entity, metric="severity_level",
                                     value=level, unit="level")

        for field, metric in TEXT.items():
            v = r.get(field)
            if v not in (None, ""):
                yield derive.Observation(entity_id=entity, metric=metric, value=str(v))

        # The warning number, carried so a second flood at the same area is a
        # changed id rather than a silently continuing entity. See the docstring.
        at = r.get("@id")
        if isinstance(at, str) and "/" in at:
            wid = at.rsplit("/", 1)[-1]
            if wid:
                yield derive.Observation(entity_id=entity, metric="warning_id", value=wid)

        tidal = r.get("isTidal")
        if isinstance(tidal, bool):
            yield derive.Observation(entity_id=entity, metric="is_tidal",
                                     value="true" if tidal else "false")

        area = r.get("floodArea")
        if isinstance(area, dict):
            for field, metric in AREA.items():
                v = area.get(field)
                if v not in (None, ""):
                    yield derive.Observation(entity_id=entity, metric=metric, value=str(v))


derive.register(SCHEMA_ID, parse, PARSER_VERSION)
