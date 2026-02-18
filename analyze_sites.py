#!/usr/bin/env python3
"""Analyze a Dwarf Fortress legends XML file focused on sites/locations.

Usage:
    python3 analyze_sites.py <file>                    # All sites ranked by activity
    python3 analyze_sites.py <file> 31                 # Full timeline for site ID 31
    python3 analyze_sites.py <file> "flagwebs"         # Search by name substring
    python3 analyze_sites.py <file> --type fortress    # Filter by site type
    python3 analyze_sites.py <file> --format json      # JSON output to stdout
"""

import argparse
import json
import os
import sys
from collections import defaultdict, Counter

from df_legends_common import (
    HF_FIELDS, clean_xml, parse_xml, format_time,
    resolve_hf, resolve_site, resolve_entity,
    format_event_details, sort_events,
)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Analyze a Dwarf Fortress legends XML file focused on sites/locations."
    )
    parser.add_argument("file", help="Path to the legends XML file")
    parser.add_argument("target", nargs="?", default=None,
                        help="Site ID (integer) or name substring for full timeline")
    parser.add_argument("--type", dest="filter_type", default=None, metavar="TYPE",
                        help="Filter site list by type (e.g. fortress, cave, hamlet)")
    parser.add_argument("-n", "--top", type=int, default=40, metavar="N",
                        help="Number of top sites to show in list mode (default: 40)")
    parser.add_argument("--format", choices=["text", "json"], default="text",
                        dest="output_format", help="Output format (default: text)")
    return parser.parse_args()


def build_site_list_json(ranked, filter_type, site_event_types, site_collections, sites, site_events):
    top_sites = []
    for rank, (score, evt_count, deaths, n_colls, sid, s) in enumerate(ranked, 1):
        top_types = site_event_types[sid].most_common(5)
        top_sites.append({
            "rank": rank,
            "id": sid,
            "name": s["name"].title(),
            "type": s["type"],
            "coords": s["coords"],
            "score": score,
            "events": evt_count,
            "deaths": deaths,
            "collections": n_colls,
            "structures": len(s["structures"]),
            "top_event_types": [{"type": t, "count": c} for t, c in top_types],
        })

    type_counts = Counter()
    type_events = Counter()
    for sid, s in sites.items():
        type_counts[s["type"]] += 1
        type_events[s["type"]] += len(site_events.get(sid, []))
    type_summary = [
        {"type": stype, "site_count": count, "total_events": type_events[stype]}
        for stype, count in type_counts.most_common()
    ]

    return {
        "filter_type": filter_type,
        "top_sites": top_sites,
        "type_summary": type_summary,
    }


def build_site_detail_json(target, sites, site_events, site_event_types, site_kills_by,
                            site_collections, all_events, hf_info, entities, artifacts):
    s = sites[target]
    evts = site_events.get(target, [])
    deaths = site_event_types[target]["hf died"]

    structures = [{"id": st["id"], "type": st["type"], "name": st["name"]}
                  for st in s["structures"]]

    event_type_breakdown = [{"type": etype, "count": count}
                             for etype, count in site_event_types[target].most_common()]

    top_killers = []
    if target in site_kills_by:
        for hfid, kills in site_kills_by[target].most_common(10):
            name = resolve_hf(hfid, hf_info) or "unknown"
            top_killers.append({"hfid": hfid, "name": name, "kills": kills})

    figure_appearances = Counter()
    for eid in evts:
        ev = all_events.get(eid, {})
        for k in HF_FIELDS:
            v = ev.get(k, "")
            if v and v != "-1":
                figure_appearances[v] += 1
    notable_figures = []
    for hfid, count in figure_appearances.most_common(15):
        name = resolve_hf(hfid, hf_info) or "unknown"
        notable_figures.append({"hfid": hfid, "name": name, "event_count": count})

    colls = site_collections.get(target, [])
    collections_list = [
        {
            "type": c.get("type", ""),
            "name": c.get("name", ""),
            "start_year": c.get("start_year", ""),
            "end_year": c.get("end_year", ""),
        }
        for c in colls
    ]

    events_sorted = sort_events(evts, all_events)

    event_list = []
    for yr, sc, eid, ev in events_sorted:
        event_list.append({
            "id": eid,
            "type": ev.get("type", ""),
            "year": yr,
            "timestamp": format_time(yr, sc),
            "details": {k: v for k, v in ev.items()
                        if k not in ("id", "type", "year", "sec") and v not in ("-1", "", "-1,-1")},
        })

    return {
        "id": target,
        "name": s["name"].title(),
        "type": s["type"],
        "coords": s["coords"],
        "structures": structures,
        "total_events": len(evts),
        "deaths": deaths,
        "event_type_breakdown": event_type_breakdown,
        "top_killers": top_killers,
        "notable_figures": notable_figures,
        "collections": collections_list,
        "events": event_list,
    }


def main():
    args = parse_args()

    if not os.path.isfile(args.file):
        print(f"ERROR: File not found: {args.file}", file=sys.stderr)
        sys.exit(1)

    content = clean_xml(args.file)
    root = parse_xml(content)
    del content

    # ── Sites ────────────────────────────────────────────────────────────────
    print("Extracting sites...", file=sys.stderr)
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
    print(f"  {len(sites)} sites", file=sys.stderr)

    # ── Entities ─────────────────────────────────────────────────────────────
    print("Extracting entities...", file=sys.stderr)
    entities = {}
    for ent in root.findall(".//entities/entity"):
        entities[ent.findtext("id", "")] = ent.findtext("name", "unnamed")
    print(f"  {len(entities)} entities", file=sys.stderr)

    # ── Historical figures ───────────────────────────────────────────────────
    print("Extracting historical figures...", file=sys.stderr)
    hf_info = {}
    for hf in root.findall(".//historical_figures/historical_figure"):
        hfid = hf.findtext("id", "")
        hf_info[hfid] = {
            "name": hf.findtext("name", "unnamed"),
            "race": hf.findtext("race", ""),
            "caste": hf.findtext("caste", ""),
        }
    print(f"  {len(hf_info)} figures", file=sys.stderr)

    # ── Artifacts ────────────────────────────────────────────────────────────
    print("Extracting artifacts...", file=sys.stderr)
    artifacts = {}
    for art in root.findall(".//artifacts/artifact"):
        aid = art.findtext("id", "")
        item_el = art.find("item")
        item_name = item_el.findtext("name_string", "") if item_el is not None else ""
        artifacts[aid] = item_name or "artifact#" + aid
    print(f"  {len(artifacts)} artifacts", file=sys.stderr)

    # ── Events ───────────────────────────────────────────────────────────────
    print("Extracting events...", file=sys.stderr)
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

    print(f"  {len(all_events)} events, {len(site_events)} sites referenced", file=sys.stderr)

    # ── Event Collections ────────────────────────────────────────────────────
    print("Extracting event collections...", file=sys.stderr)
    site_collections = defaultdict(list)
    n_collections = 0
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
        n_collections += 1
        csid = c.get("site_id", "-1")
        if csid and csid != "-1":
            site_collections[csid].append(c)
    print(f"  {n_collections} collections", file=sys.stderr)

    root.clear()

    # ── Handle name search ───────────────────────────────────────────────────
    target = args.target
    if target and not target.isdigit():
        search = target.lower()
        matches = [(sid, s) for sid, s in sites.items()
                   if search in s["name"].lower()]
        if not matches:
            print(f"\nNo sites found matching '{target}'", file=sys.stderr)
            return
        if len(matches) == 1:
            target = matches[0][0]
            print(f"\nFound: {matches[0][1]['name'].title()} (ID:{target})", file=sys.stderr)
        else:
            print(f"\nMultiple matches for '{target}':", file=sys.stderr)
            for sid, s in matches:
                evt_count = len(site_events.get(sid, []))
                print(f"  ID:{sid} - {s['name'].title()} ({s['type']}) - {evt_count} events",
                      file=sys.stderr)
            print("\nRe-run with a specific ID.", file=sys.stderr)
            return

    # ── LIST MODE ────────────────────────────────────────────────────────────
    if target is None:
        ranked = []
        for sid, s in sites.items():
            if args.filter_type and s["type"].lower() != args.filter_type:
                continue
            evt_count = len(site_events.get(sid, []))
            deaths = site_event_types[sid]["hf died"]
            n_colls = len(site_collections.get(sid, []))
            n_structs = len(s["structures"])
            score = evt_count + deaths * 2 + n_colls * 5 + n_structs * 3
            ranked.append((score, evt_count, deaths, n_colls, sid, s))
        ranked.sort(reverse=True)

        if args.output_format == "json":
            result = build_site_list_json(
                ranked[:args.top], args.filter_type, site_event_types,
                site_collections, sites, site_events
            )
            print(json.dumps(result, indent=2))
            return

        type_label = f" (type: {args.filter_type})" if args.filter_type else ""
        print("\n" + "=" * 80)
        print(f"ALL SITES RANKED BY ACTIVITY{type_label}")
        print("=" * 80)

        for rank, (score, evt_count, deaths, n_colls, sid, s) in enumerate(ranked[:args.top], 1):
            n_structs = len(s["structures"])
            print(f"\n  #{rank}: {s['name'].title()} (ID:{sid})")
            print(f"    Type: {s['type']}, Coords: {s['coords']}")
            print(f"    Events: {evt_count}, Deaths: {deaths}, "
                  f"Collections: {n_colls}, Structures: {n_structs}")
            if sid in site_event_types:
                top_types = site_event_types[sid].most_common(5)
                print("    Top event types: " + ", ".join(
                    t + "(" + str(c) + ")" for t, c in top_types))

        if args.filter_type is None:
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

        print(f"\n\nUse '{sys.argv[0]} <file> <ID>' for a full site timeline.", file=sys.stderr)
        print(f"Use '{sys.argv[0]} <file> --type fortress' to filter by type.", file=sys.stderr)
        return

    # ── DETAIL MODE ──────────────────────────────────────────────────────────
    if target not in sites:
        print(f"\nERROR: Site ID '{target}' not found!", file=sys.stderr)
        sys.exit(1)

    if args.output_format == "json":
        result = build_site_detail_json(
            target, sites, site_events, site_event_types, site_kills_by,
            site_collections, all_events, hf_info, entities, artifacts
        )
        print(json.dumps(result, indent=2))
        return

    s = sites[target]
    print("\n" + "=" * 80)
    print(f"SITE: {s['name'].title()}")
    print(f"  Type: {s['type']}")
    print(f"  Coords: {s['coords']}")
    print("=" * 80)

    if s["structures"]:
        print(f"\n  STRUCTURES ({len(s['structures'])}):")
        for st in s["structures"]:
            label = st["type"]
            if st["name"]:
                label += ": " + st["name"]
            print(f"    - {label}")

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
                    en = resolve_entity(eid, entities) or eid
                    nice = (ekey.replace("_ent_id", "").replace("_enid", "")
                            .replace("_", " ").strip().title())
                    label += f" [{nice}: {en.title()}]"
            print(f"    - {label}")

    evts = site_events.get(target, [])
    deaths = site_event_types[target]["hf died"]
    print(f"\n  STATISTICS:")
    print(f"    Total events: {len(evts)}")
    print(f"    Deaths at this site: {deaths}")

    if target in site_event_types:
        print(f"\n  EVENT TYPE BREAKDOWN:")
        for etype, count in site_event_types[target].most_common():
            print(f"    {etype}: {count}")

    if target in site_kills_by:
        print(f"\n  DEADLIEST FIGURES AT THIS SITE:")
        for hfid, kills in site_kills_by[target].most_common(10):
            name = resolve_hf(hfid, hf_info) or "unknown"
            print(f"    {name}: {kills} kills")

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
            name = resolve_hf(hfid, hf_info) or "unknown"
            print(f"    {name}: {count} events here")

    print(f"\n  FULL TIMELINE ({len(evts)} events):")
    print("-" * 80)

    events_sorted = sort_events(evts, all_events)

    for yr, sc, eid, ev in events_sorted:
        etype = ev.get("type", "?")
        ts = format_time(yr, sc)
        details = format_event_details(ev, sites, entities, hf_info, artifacts)
        print(f"\n  [{ts}] {etype.upper()}")
        for d in details:
            print(f"      {d}")

    print("\n\nANALYSIS COMPLETE")


if __name__ == "__main__":
    main()
