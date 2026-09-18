# Evo Scheduler

Manage your Evohome **weekly heating schedules** from inside Home Assistant:
see the live schedule per zone, keep a library of named alternate schedules
(Winter, Away, WFH, Half-term…), edit them on a visual grid, and push any one
of them back to Evohome **a zone at a time**.

It talks to Honeywell/Resideo **Total Connect Comfort (TCC)** directly via the
`evohome-async` library — the same cloud API the core Evohome integration uses.
Your HA Evohome integration can't read or write full schedules; this fills that
gap. It does **not** replace the integration — keep using that for live temps
and overrides.

## Installation (local add-on)

1. Copy this whole folder to `/addons/evo_scheduler/` on your HA host
   (via the Samba or File editor add-on, into the `addons` share).
2. **Settings → Add-ons → Add-on Store → ⋮ → Check for updates.**
3. Open **Evo Scheduler** → **Install**.

## Configuration

| Option | What it is |
|---|---|
| `username` | Your Total Connect Comfort email (same as the Evohome app) |
| `password` | Your TCC password |
| `location_idx` | Which location (0 for a single-home account) |

Start the add-on, then open its **Web UI** (or the sidebar panel). The badge
top-right reads **Live · TCC** once it's connected. If it can't connect, the
screen tells you why — check the add-on **Log**.

## Using it

- **Zones** (left) — pick a heating zone or Hot Water. The week shows as
  temperature-coloured timelines: cool blue = setback, warm amber/red = comfort.
- Click a **day** to edit its switchpoints (time + temperature, or On/Off for
  hot water). Add/remove points; copy a day to Mon–Fri / weekend / all.
- **Save to library** stores the current zone's schedule into a named set.
  Sets live server-side in `/data` and are included in add-on backups.
- **Push this zone to Live** writes the schedule you're editing back to Evohome,
  behind a confirmation. Only that zone changes.
- **Pull live ↓** grabs the current live schedule into the editor to tweak.

## Notes & safety

- Pushing overwrites the **whole Mon–Sun programme** for that zone. Manual
  overrides set on the wall unit are unaffected — only the schedule changes.
- TCC rate-limits aggressively. The add-on caches its access token in `/data`
  to avoid re-authenticating; if you see a rate-limit message, wait a minute.
- Evohome allows up to ~6 switchpoints per day per zone; the editor warns past 6.
- Credentials are stored in the add-on options (HA's standard mechanism).

## Backups
Your schedule library (`/data/library.json`) and token cache travel with the
add-on's backup, so your Google Drive Backup add-on already covers them.
