# analyze_sites.py

Command-line utility to analyze a **Dwarf Fortress** *legends.xml* file
with a focus on **sites/locations**. Operates in two modes:

- **List mode** — ranks all sites by activity and prints a summary table
- **Detail mode** — prints full metadata, statistics, and a chronological
  event timeline for a specific site

## Requirements

- Python 3.x
- [`defusedxml`](https://pypi.org/project/defusedxml/) (optional but recommended — falls back to `xml.etree.ElementTree` if not installed)

```
pip install defusedxml
```

## Usage

```
python3 analyze_sites.py <file> [target] [options]
```

| Argument | Description |
|---|---|
| `file` | Path to the legends XML file |
| `target` | Site ID (integer) or name substring — triggers detail mode |
| `--type TYPE` | Filter list mode by site type (e.g. `fortress`, `cave`, `hamlet`) |
| `-n`, `--top N` | Number of top sites to show in list mode (default: `40`) |
| `--format text\|json` | Output format (default: `text`) |

Progress messages (loading, parsing, extraction counts) are written to
**stderr**. Analysis output goes to **stdout**, so they can be separated:

```bash
# Clean output only
python3 analyze_sites.py legends.xml 2>/dev/null

# JSON to a file, progress visible in terminal
python3 analyze_sites.py legends.xml --format json > out.json
```

### Examples

```bash
# Top 40 sites ranked by activity
python3 analyze_sites.py legends.xml

# Top 10 sites
python3 analyze_sites.py legends.xml -n 10

# Full timeline for site ID 31
python3 analyze_sites.py legends.xml 31

# Search by name substring (case-insensitive)
python3 analyze_sites.py legends.xml "flagwebs"

# Filter list mode to fortresses only
python3 analyze_sites.py legends.xml --type fortress

# JSON list output
python3 analyze_sites.py legends.xml --format json 2>/dev/null | python3 -m json.tool

# JSON detail output for site 31
python3 analyze_sites.py legends.xml 31 --format json 2>/dev/null | python3 -m json.tool
```

### Name search

If `target` is not a number, the script does a case-insensitive
substring match against all site names:

- **One match** — proceeds directly to detail mode for that site
- **Multiple matches** — prints a candidate list (ID, name, type, event
  count) and exits; re-run with a specific ID
- **No matches** — prints a message and exits

## Output

### Text — list mode

Prints up to `N` sites ranked by activity score. For each site:

- Name and ID
- Type and coordinates
- Counts: events, deaths (*hf died* events), event collections, structures
- Top event types (up to 5)

If no `--type` filter is active, a **site type summary** follows:

- Count of sites per type
- Total events per type

### Text — detail mode

For the selected site:

- Metadata: name, type, coordinates
- Structure list
- Event collections referencing the site (with aggressor/defender entities where available)
- Statistics: total events, deaths
- Event type breakdown (all types, sorted by count)
- Deadliest figures at the site (by *hf died* with *slayer_hfid*, top 10)
- Most referenced figures (by *hfid* field appearances across site events, top 15)
- Full chronological event timeline with resolved names:
  - `site_id` → site name
  - entity/civ fields → entity name
  - `*hfid*` fields → figure name and race
  - `artifact_id` → artifact name

### JSON — list mode

```json
{
  "filter_type": null,
  "top_sites": [
    {
      "rank": 1,
      "id": "...",
      "name": "...",
      "type": "...",
      "coords": "...",
      "score": 0,
      "events": 0,
      "deaths": 0,
      "collections": 0,
      "structures": 0,
      "top_event_types": [{"type": "...", "count": 0}]
    }
  ],
  "type_summary": [{"type": "...", "site_count": 0, "total_events": 0}]
}
```

`type_summary` always covers all sites regardless of `--type` filtering.

### JSON — detail mode

```json
{
  "id": "...",
  "name": "...",
  "type": "...",
  "coords": "...",
  "structures": [{"id": "...", "type": "...", "name": "..."}],
  "total_events": 0,
  "deaths": 0,
  "event_type_breakdown": [{"type": "...", "count": 0}],
  "top_killers": [{"hfid": "...", "name": "...", "kills": 0}],
  "notable_figures": [{"hfid": "...", "name": "...", "event_count": 0}],
  "collections": [{"type": "...", "name": "...", "start_year": "...", "end_year": "..."}],
  "events": [
    {
      "id": "...",
      "type": "...",
      "year": 0,
      "timestamp": "Year 100, 1 Granite",
      "details": {}
    }
  ]
}
```

`events[].details` keeps raw IDs (no name resolution) for machine consumption.

## Activity scoring (list mode)

Sites are ranked by:

```
score = events + (deaths × 2) + (collections × 5) + (structures × 3)
```

The score is used only for ordering and is included in JSON output.

## Time formatting

Events carry `year` and `seconds72`. When `seconds72 >= 0` the script
converts it to a DF calendar date (12 months × 28 days, named *Granite*
through *Obsidian*). If conversion fails it falls back to `Year <year>`.

## Limitations

- Loads the full XML into memory (clean → parse). Very large legends
  files may use significant RAM.
- Site timelines include only events that carry a `site_id` field.
  Events with no site reference are tracked globally but do not appear
  in any site's timeline.
- Sub-collection references in event collections (`eventcol` children)
  are not expanded.

## Troubleshooting

**File not found** — verify the path passed as the first argument.

**XML parse errors** — the script strips control characters before
parsing, but truncated or otherwise malformed files may still fail.
Ensure the legends export completed successfully.

**"Multiple matches"** — your name substring matched more than one site.
Use the printed ID list to re-run with an exact site ID.
