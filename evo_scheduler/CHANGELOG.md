# Changelog
## 0.5.0
- Replaced all sliders with +/- buttons (schedule editor, boosts, room override) for reliable control on phones.
- Settings: added a "Button increment" control (0.5 or 1, default 1) that all +/- buttons use; Theme now lives here too.
- Schedule editor now shows a "used / max" count and stops you adding changes beyond your controller's real limit (6 per day).
- New "Day off" button on the home screen: applies a chosen plan-day's schedule to selected rooms for the rest of today, then automatically reverts to your normal schedule at midnight. Configure it in Settings -> Day off setup.
## 0.4.0
- Create new plans from the app (Settings -> Edit plans -> + New plan), optionally cloning an existing plan to start from.
- Manage plans: rename, duplicate, delete.

## 0.3.0
- Home reworked: current plan now lives in the header; Quick boost moved to the top; "Current status" table with Current / Target / Until column labels.
- Tap a room to set a temporary override — +/- 1° with 18/21/23° quick buttons, until a chosen time, and Back to schedule.
- "Until" shows when the setpoint next changes (override end, or next scheduled switchpoint).
- New Settings page (gear): switch plan (dropdown), edit boosts, edit schedules, and theme.
- Theme now offers Light / Dark / Follow system (default: follow system).

## 0.2.1
- Real app icon and logo (a heating-schedule profile mark) and a heating sidebar icon.

## 0.2.0
- New phone-first home screen: switch plan and quick-boost front and centre.
- Apply a saved plan to chosen rooms in one tap (room picker, all covered rooms preselected).
- Quick boosts: one-tap timed overrides (e.g. "Lounge + Kitchen 21° for 2h") with Undo, plus a boosts editor.
- "Rooms now" showing current vs target temperature and boost/hold state.
- Schedule editor moved a level down and cleaned up (plain language, Save/Discard).
- Engine: timed overrides (boost) + cancel; live snapshot of temps and mode.

## 0.1.0
- First version: per-zone schedule viewer, library of alternate schedules, visual day editor, per-zone push.
