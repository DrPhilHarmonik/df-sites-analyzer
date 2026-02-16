# analyze_sites.py

Command-line utility to analyze a **Dwarf Fortress** *legends.xml* file
with a focus on **sites/locations**. It can either (1) rank all sites by
activity or (2) print a full, chronological timeline for a specific
site.

## Features

- Parses a *legends.xml* file and extracts:

  - Sites (including structures)
  - Entities
  - Historical figures
  - Artifacts
  - Historical events
  - Historical event collections (e.g., wars/battles/attacks)

- Default mode: ranks sites by an activity score and prints the top
  results

- Detail mode: prints site metadata, summary statistics, and a full
  event timeline for a given site

- Name search: find sites by a case-insensitive substring of the site
  name

- Optional filter: restrict ranking output by site type

## Requirements

- Python 3.x
- Standard library only (no external dependencies)

## Installation

No installation required. Save the script as *analyze_sites.py* and run
it with Python.

## Usage

### Rank all sites by activity (default)

*python3 analyze_sites.py \<legends_xml_file\>*

### Show details and full timeline for a specific site ID

*python3 analyze_sites.py \<legends_xml_file\> \<site_id\>*

### Search for a site by name substring

*python3 analyze_sites.py \<legends_xml_file\> "\<name_substring\>"*

If multiple sites match, the script prints a list of candidates (ID,
name, type, event count) and exits. Re-run with a specific ID.

### Filter ranking output by site type

*python3 analyze_sites.py \<legends_xml_file\> --type \<site_type\>*

Example:

*python3 analyze_sites.py legends.xml --type fortress*

## Output

### Ranking mode

Prints up to the top 40 sites (after optional filtering). For each site:

- Name and ID

- Type and coordinates

- Counts for:

  - Events
  - Deaths at the site (*hf died* events)
  - Event collections referencing the site
  - Structures listed on the site

- Top event types (up to 5) for that site

If no type filter is provided, an additional **site type summary** is
printed:

- Count of sites per type
- Total events per type

### Detail mode (site timeline)

For the selected site, prints:

- Site metadata (name/type/coords)

- List of structures

- Event collections referencing the site (including aggressor/defender
  entities where available)

- Statistics:

  - Total events
  - Deaths at the site

- Event type breakdown

- “Deadliest figures” at this site (based on *hf died* events with a
  *slayer_hfid*)

- Most referenced historical figures (based on *\*hfid\** fields found
  in site events)

- Full chronological event timeline with resolved names for:

  - Site IDs
  - Entity IDs
  - Historical figure IDs
  - Artifact IDs

## Activity Scoring (Ranking Mode)

Sites are ranked by a computed score:

*score = events + (deaths \* 2) + (collections \* 5) + (structures \*
3)*

This score is used only for ordering the “most active” sites list.

## Time Formatting

Events include *year* and *seconds72*. When *seconds72* is available
(\>= 0), the script converts it into a calendar date using:

- 12 months, 28 days per month
- Dwarf Fortress month names (*Granite* through *Obsidian*)

If conversion fails, the script prints *Year \<year\>*.

## Limitations

- Loads the XML into memory (reads the full file content, cleans it,
  then parses). Very large legends files may require significant RAM.
- Site timelines include only events that explicitly contain a
  *site_id*.
- Sub-collection references in event collections (*eventcol*) are not
  expanded.

## Troubleshooting

- **File not found**

  - Verify the path passed as the first argument points to an existing
    file.

- **Parse errors**

  - The script removes control characters before parsing, but malformed
    or truncated XML files may still fail. Ensure the legends file is
    complete and valid.

## License

No license is included. Add a license file if you plan to redistribute.
