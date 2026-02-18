"""Shared utilities for Dwarf Fortress legends XML analysis tools."""

import re
import sys

try:
    import defusedxml.ElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET  # type: ignore[no-redef]

# Fields in events that reference historical figure IDs
HF_FIELDS = {
    'hfid', 'slayer_hfid', 'hfid1', 'hfid2', 'group_hfid', 'snatcher_hfid',
    'changee_hfid', 'changer_hfid', 'woundee_hfid', 'wounder_hfid',
    'doer_hfid', 'target_hfid', 'attacker_hfid', 'defender_hfid',
    'hist_fig_id', 'body_hfid', 'hfid_target', 'hfid_attacker',
    'hfid_defender', 'trickster_hfid', 'cover_hfid', 'student_hfid',
    'teacher_hfid', 'trainer_hfid', 'seeker_hfid',
}

_CONTROL_CHAR_RE = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f]')
_SKIP_KEYS = frozenset(("id", "type", "year", "sec"))
_SKIP_VALS = frozenset(("-1", "", "-1,-1"))

DF_MONTHS = [
    "Granite", "Slate", "Felsite", "Hematite", "Malachite", "Galena",
    "Limestone", "Sandstone", "Timber", "Moonstone", "Opal", "Obsidian",
]


def clean_xml(filepath):
    """Read an XML file and strip invalid control characters."""
    print("Cleaning XML of invalid characters...", file=sys.stderr)
    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()
    return _CONTROL_CHAR_RE.sub('', content)


def parse_xml(xml_string):
    """Parse the full XML tree from a cleaned string."""
    print("Parsing XML tree...", file=sys.stderr)
    root = ET.fromstring(xml_string)
    print("XML parsed.", file=sys.stderr)
    return root


def format_time(year, sec):
    """Convert a DF year + seconds72 value to a human-readable calendar date."""
    ts = "Year " + str(year)
    if sec >= 0:
        try:
            doy = sec // 1200 + 1
            mo = min((doy - 1) // 28 + 1, 12)
            day = (doy - 1) % 28 + 1
            ts = f"Year {year}, {day} {DF_MONTHS[mo - 1]}"
        except (ValueError, IndexError):
            pass
    return ts


def resolve_hf(hfid, hf_info):
    """Return a display name for a historical figure ID, or None if invalid."""
    if hfid == "-1" or not hfid:
        return None
    info = hf_info.get(hfid, {})
    name = info.get("name", "fig#" + hfid)
    race = info.get("race", "")
    return name.title() + " (" + race + ")" if race else name.title()


def resolve_site(sid, sites):
    """Return the name of a site by ID, or None if invalid.

    Expects sites values to be dicts with at least a "name" key.
    """
    if sid == "-1" or not sid:
        return None
    s = sites.get(sid)
    return s["name"] if s else "site#" + sid


def resolve_entity(eid, entities):
    """Return the name of an entity by ID, or None if invalid."""
    if eid == "-1" or not eid:
        return None
    return entities.get(eid, "entity#" + eid)


def format_event_details(ev, sites, entities, hf_info, artifacts):
    """Return human-readable 'Key: Value' strings for displayable event fields."""
    details = []
    for k, v in sorted(ev.items()):
        if k in _SKIP_KEYS or v in _SKIP_VALS:
            continue
        display = v
        if k == "site_id":
            r = resolve_site(v, sites)
            if r:
                display = r
        elif "entity" in k or "civ" in k:
            r = resolve_entity(v, entities)
            if r:
                display = r.title()
        elif "hfid" in k.lower():
            r = resolve_hf(v, hf_info)
            if r:
                display = r
        elif k == "artifact_id":
            a = artifacts.get(v, "")
            if a:
                display = a
        details.append(k.replace("_", " ").title() + ": " + display)
    return details


def sort_events(event_ids, all_events):
    """Return (year, sec, event_id, event_dict) tuples sorted chronologically."""
    result = []
    for eid in event_ids:
        ev = all_events.get(eid, {})
        try:
            yr = int(ev.get("year", 0))
        except ValueError:
            yr = 0
        try:
            sc = int(ev.get("sec", -1))
        except ValueError:
            sc = -1
        result.append((yr, sc, eid, ev))
    result.sort()
    return result
