#!/usr/bin/env python3
"""Analyze a Dwarf Fortress legends XML file focused on sites/locations.

Usage:
    python3 analyze_sites.py <file>                    # All sites ranked by activity
    python3 analyze_sites.py <file> 31                 # Full timeline for site ID 31
    python3 analyze_sites.py <file> "flagwebs"         # Search by name substring
    python3 analyze_sites.py <file> --type fortress    # Filter by site type
"""

import defusedxml.ElementTree as ET
from collections import defaultdict, Counter
import re
import sys
import os

DF_MONTHS = [
    "Granite", "Slate", "Felsite", "Hematite", "Malachite", "Galena",
    "Limestone", "Sandstone", "Timber", "Moonstone", "Opal", "Obsidian"
]

HF_FIELDS = {
    'hfid', 'slayer_hfid', 'hfid1', 'hfid2', 'group_hfid', 'snatcher_hfid',
    'changee_hfid', 'changer_hfid', 'woundee_hfid', 'wounder_hfid',
    'doer_hfid', 'target_hfid', 'attacker_hfid', 'defender_hfid',
    'hist_fig_id', 'body_hfid', 'hfid_target', 'hfid_attacker',
    'hfid_defender', 'trickster_hfid', 'cover_hfid', 'student_hfid',
    'teacher_hfid', 'trainer_hfid', 'seeker_hfid',
}


def clean_and_parse(filepath):
    print("Loading and cleaning XML...")
    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()
    content = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', content)
    print("Parsing XML tree...")
    root = ET.fromstring(content)
    del content
    print("Done!")
    return root


def format_time(year, sec):
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


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 analyze_sites.py <legends_xml_file> [site_id|name|--type <type>]")
        sys.exit(1)

    xml_file = sys.argv[1]
    if not os.path.isfile(xml_file):
        print(f"ERROR: File not found: {xml_file}")
        sys.exit(1)

    # Parse remaining arguments
    target = None
    filter_type = None
    args = sys.argv[2:]
    if len(args) >= 2 and args[0] == "--type":
        filter_type = args[1].lower()
    elif len(args) >= 1:
        target = args[0]

    root = clean_and_parse(xml_file)

    # ── Sites ────────────────────────────────────────────────────────────────
    print("Extracting sites...")
    sites = {}
    for site in root.findall(".//sites/site"):
        sid = site.findtext("id", "")
        structures = []
        for struct in site.findall("structures/structure"):
            structures.append({
                "id": struct.findtext("local_id", ""),
                "type": struct.findtext("type", ""),
                "name": struct.findtext("name", ""),
            })
        sites[sid] = {
            "id": sid,
            "name": site.findtext("name", "unnamed"),
            "type": site.findtext("type", "unknown"),
            "coords": site.findtext("coords", ""),
            "structures": structures,
        }
    print(f"  {len(sites)} sites")

    # ── Entities ─────────────────────────────────────────────────────────────
    print("Extracting entities...")
    entities = {}
    for ent in root.findall(".//entities/entity"):
        entities[ent.findtext("id", "")] = ent.findtext("name", "unnamed")
    print(f"  {len(entities)} entities")

    # ── Historical figures ───────────────────────────────────────────────────
    print("Extracting historical figures...")
    hf_info = {}
    for hf in root.findall(".//historical_figures/historical_figure"):
        hfid = hf.findtext("id", "")
        hf_info[hfid] = {
            "name": hf.findtext("name", "unnamed"),
            "race": hf.findtext("race", ""),
            "caste": hf.findtext("caste", ""),
        }
    print(f"  {len(hf_info)} figures")

    # ── Artifacts ────────────────────────────────────────────────────────────
    print("Extracting artifacts...")
    artifacts = {}
    for art in root.findall(".//artifacts/artifact"):
        aid = art.findtext("id", "")
        item_el = art.find("item")
        item_name = item_el.findtext("name_string", "") if item_el is not None else ""
        artifacts[aid] = item_name or "artifact#" + aid
    print(f"  {len(artifacts)} artifacts")

    # ── Events ───────────────────────────────────────────────────────────────
    print("Extracting events...")
    all_events = {}
    site_events = defaultdict(list)  # site_id -> [event_id, ...]
    site_event_types = defaultdict(Counter)
    site_kills_by = defaultdict(Counter)  # site_id -> {slayer_hfid: count}

    for evt in root.findall(".//historical_events/historical_event"):
        eid = evt.findtext("id", "")
        etype = evt.findtext("type", "")
        ev_data = {
            "id": eid, "type": etype,
            "year": evt.findtext("year", "0"),
            "sec": evt.findtext("seconds72", "-1"),
        }
        for child in evt:
            if child.tag not in ("id", "type", "year", "seconds72"):
                ev_data[child.tag] = child.text or ""

        all_events[eid] = ev_data

        sid = ev_data.get("site_id", "-1")
        if sid and sid != "-1":
            site_events[sid].append(eid)
            site_event_types[sid][etype] += 1
            if etype == "hf died":
                slayer = ev_data.get("slayer_hfid", "")
                if slayer and slayer != "-1":
                    site_kills_by[sid][slayer] += 1

    print(f"  {len(all_events)} events, {len(site_events)} sites referenced")

    # ── Event Collections ────────────────────────────────────────────────────
    print("Extracting event collections...")
    collections = []
    site_collections = defaultdict(list)
    for coll in root.findall(".//historical_event_collections/historical_event_collection"):
        c = {}
        coll_events = []
        for child in coll:
            if child.tag == "event":
                coll_events.append(child.text or "")
            elif child.tag == "eventcol":
                pass  # sub-collection reference
            else:
                c[child.tag] = child.text or ""
        c["_events"] = coll_events
        collections.append(c)
        csid = c.get("site_id", "-1")
        if csid and csid != "-1":
            site_collections[csid].append(c)
    print(f"  {len(collections)} collections")

    root.clear()

    # ── Resolver helpers ─────────────────────────────────────────────────────
    def rhf(hfid):
        if hfid == "-1" or not hfid:
            return None
        info = hf_info.get(hfid, {})
        name = info.get("name", "fig#" + hfid)
        race = info.get("race", "")
        return name.title() + " (" + race + ")" if race else name.title()

    def rent(eid):
        if eid == "-1" or not eid:
            return None
        return entities.get(eid, "entity#" + eid)

    def rsite(sid):
        if sid == "-1" or not sid:
            return None
        s = sites.get(sid)
        return s["name"] if s else "site#" + sid

    # ── Handle name search ───────────────────────────────────────────────────
    if target and not target.isdigit():
        search = target.lower()
        matches = [(sid, s) for sid, s in sites.items()
                   if search in s["name"].lower()]
        if not matches:
            print(f"\nNo sites found matching '{target}'")
            return
        if len(matches) == 1:
            target = matches[0][0]
            print(f"\nFound: {matches[0][1]['name'].title()} (ID:{target})")
        else:
            print(f"\nMultiple matches for '{target}':")
            for sid, s in matches:
                evt_count = len(site_events.get(sid, []))
                print(f"  ID:{sid} - {s['name'].title()} ({s['type']}) - {evt_count} events")
            print("\nRe-run with a specific ID.")
            return

    # ── LIST MODE ────────────────────────────────────────────────────────────
    if target is None:
        # Rank sites by activity
        ranked = []
        for sid, s in sites.items():
            if filter_type and s["type"].lower() != filter_type:
                continue
            evt_count = len(site_events.get(sid, []))
            deaths = site_event_types[sid]["hf died"]
            n_colls = len(site_collections.get(sid, []))
            n_structs = len(s["structures"])
            # Score: events + deaths bonus + collections + structures
            score = evt_count + deaths * 2 + n_colls * 5 + n_structs * 3
            ranked.append((score, evt_count, deaths, n_colls, sid, s))
        ranked.sort(reverse=True)

        type_label = f" (type: {filter_type})" if filter_type else ""
        print("\n" + "=" * 80)
        print(f"ALL SITES RANKED BY ACTIVITY{type_label}")
        print("=" * 80)

        for rank, (score, evt_count, deaths, n_colls, sid, s) in enumerate(ranked[:40], 1):
            n_structs = len(s["structures"])
            print(f"\n  #{rank}: {s['name'].title()} (ID:{sid})")
            print(f"    Type: {s['type']}, Coords: {s['coords']}")
            print(f"    Events: {evt_count}, Deaths: {deaths}, "
                  f"Collections: {n_colls}, Structures: {n_structs}")
            if sid in site_event_types:
                top_types = site_event_types[sid].most_common(5)
                print("    Top event types: " + ", ".join(
                    t + "(" + str(c) + ")" for t, c in top_types))

        if filter_type is None:
            # Also print type summary
            type_counts = Counter()
            type_events = Counter()
            for sid, s in sites.items():
                type_counts[s["type"]] += 1
                type_events[s["type"]] += len(site_events.get(sid, []))
            print("\n\n" + "=" * 80)
            print("SITE TYPE SUMMARY")
            print("=" * 80)
            for stype, count in type_counts.most_common():
                evts = type_events[stype]
                print(f"  {stype}: {count} sites, {evts} total events")

        print(f"\n\nUse 'python3 analyze_sites.py <ID>' for a full site timeline.")
        print(f"Use 'python3 analyze_sites.py --type fortress' to filter by type.")
        return

    # ── DETAIL MODE ──────────────────────────────────────────────────────────
    if target not in sites:
        print(f"\nERROR: Site ID '{target}' not found!")
        return

    s = sites[target]
    print("\n" + "=" * 80)
    print(f"SITE: {s['name'].title()}")
    print(f"  Type: {s['type']}")
    print(f"  Coords: {s['coords']}")
    print("=" * 80)

    # Structures
    if s["structures"]:
        print(f"\n  STRUCTURES ({len(s['structures'])}):")
        for st in s["structures"]:
            label = st["type"]
            if st["name"]:
                label += ": " + st["name"]
            print(f"    - {label}")

    # Event collections (wars, battles, beast attacks, etc.)
    colls = site_collections.get(target, [])
    if colls:
        print(f"\n  EVENT COLLECTIONS ({len(colls)}):")
        for c in colls:
            ctype = c.get("type", "?")
            cname = c.get("name", "")
            sy = c.get("start_year", "?")
            ey = c.get("end_year", "?")
            label = ctype.title()
            if cname:
                label += ": " + cname.title()
            label += f" (years {sy}-{ey})"
            for ekey in ("aggressor_ent_id", "defender_ent_id",
                         "attacking_enid", "defending_enid"):
                eid = c.get(ekey, "")
                if eid and eid != "-1":
                    en = rent(eid) or eid
                    nice = (ekey.replace("_ent_id", "").replace("_enid", "")
                            .replace("_", " ").strip().title())
                    label += f" [{nice}: {en.title()}]"
            print(f"    - {label}")

    # Summary stats
    evts = site_events.get(target, [])
    deaths = site_event_types[target]["hf died"]
    print(f"\n  STATISTICS:")
    print(f"    Total events: {len(evts)}")
    print(f"    Deaths at this site: {deaths}")

    if target in site_event_types:
        print(f"\n  EVENT TYPE BREAKDOWN:")
        for etype, count in site_event_types[target].most_common():
            print(f"    {etype}: {count}")

    # Top killers at this site
    if target in site_kills_by:
        print(f"\n  DEADLIEST FIGURES AT THIS SITE:")
        for hfid, kills in site_kills_by[target].most_common(10):
            name = rhf(hfid) or "unknown"
            print(f"    {name}: {kills} kills")

    # Notable figures linked to this site (via events)
    figure_appearances = Counter()
    for eid in evts:
        ev = all_events.get(eid, {})
        for k in HF_FIELDS:
            v = ev.get(k, "")
            if v and v != "-1":
                figure_appearances[v] += 1
    if figure_appearances:
        print(f"\n  MOST REFERENCED FIGURES ({len(figure_appearances)} total):")
        for hfid, count in figure_appearances.most_common(15):
            name = rhf(hfid) or "unknown"
            print(f"    {name}: {count} events here")

    # Full chronological timeline
    print(f"\n  FULL TIMELINE ({len(evts)} events):")
    print("-" * 80)

    events_sorted = []
    for eid in evts:
        ev = all_events.get(eid, {})
        try:
            yr = int(ev.get("year", 0))
        except ValueError:
            yr = 0
        try:
            sc = int(ev.get("sec", -1))
        except ValueError:
            sc = -1
        events_sorted.append((yr, sc, eid, ev))
    events_sorted.sort()

    for yr, sc, eid, ev in events_sorted:
        etype = ev.get("type", "?")
        ts = format_time(yr, sc)
        details = []
        for k, v in sorted(ev.items()):
            if k in ("id", "type", "year", "sec") or v == "-1" or v == "" or v == "-1,-1":
                continue
            display = v
            if k == "site_id":
                r = rsite(v)
                if r:
                    display = r
            elif "entity" in k or "civ" in k:
                r = rent(v)
                if r:
                    display = r.title()
            elif "hfid" in k.lower():
                r = rhf(v)
                if r:
                    display = r
            elif k == "artifact_id":
                a = artifacts.get(v, "")
                if a:
                    display = a
            details.append(k.replace("_", " ").title() + ": " + display)
        print(f"\n  [{ts}] {etype.upper()}")
        for d in details:
            print(f"      {d}")

    print("\n\nANALYSIS COMPLETE")


if __name__ == "__main__":
    main()
