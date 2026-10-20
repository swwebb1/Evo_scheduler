# Fit Plan

A personal training plan that lives in the Home Assistant sidebar.

## Tabs

- **Today** — what's scheduled for the selected day, with this week's prescription. Kettlebell days list
  every exercise; tap one to read its description and coaching cues, and tap the numbered circles to tick
  off sets. *Mark done* records the session. A quick weigh-in (weight and optional waist) sits underneath.
- **Sessions** — your kettlebell sessions. *Edit* lets you rename a session, change the warm-up, and add,
  remove, reorder or edit exercises (sets, reps or time, rest, load, notes, description and cues).
  *+ New session* creates another (C, D, …) that you can then schedule. The exercise library at the bottom
  holds templates with descriptions that pre-fill new exercises; you can add or edit those too.
- **Plan** — targets, the weekly schedule (which session or run falls on each day), and the week-by-week
  progression table. Everything is editable. *Reset plan to defaults* restores the original 6-week plan
  without touching your logged data.
- **Progress** — 7-day average, change since start, distance to goal, waist change, a chart against the
  planned path, a weekly summary and the list of weigh-ins.

## Data

Stored as JSON in the add-on's `/data` folder (`plan.json`, `log.json`), so it is included in Home
Assistant backups. Set ticks are remembered per device.

No configuration or tokens are needed.
