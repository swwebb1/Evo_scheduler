"""Local backend — drives the ramses_cc integration over Home Assistant's API.

Same public surface as EvoEngine (engine.py), so server.py can use either:
    start/close, connected, zones, snapshot, get_live, push, boost, cancel,
    today_dow, next_midnight_iso, now_ge, plus pull() (ramses-only).

Talks to HA core via the Supervisor proxy (http://supervisor/core/api) using
the add-on's SUPERVISOR_TOKEN; requires `homeassistant_api: true` in config.yaml.

The RF dongle stays owned by ramses_cc — this engine is only a client of it:
  - status/targets/modes  <- GET /api/states/<entity>  (ramses zone attributes)
  - boost / override      -> ramses_cc.set_zone_mode (temporary_override)
  - back to schedule      -> ramses_cc.reset_zone_mode
  - read schedule         -> ramses_cc.get_zone_schedule then read attr.schedule
  - write schedule        -> ramses_cc.set_zone_schedule

Zones are exposed under the SAME ids the cloud/library use (TCC zone ids),
mapped from the controller's own zone name (attributes.params.name), which TCC,
EvoControl and ramses all agree on regardless of HA entity renames.
"""
from __future__ import annotations

import asyncio
import logging
import os
import time
from datetime import datetime, timedelta, timezone

import aiohttp

_LOGGER = logging.getLogger("evo.ramses")
UTC = timezone.utc
DAY_ORDER = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]  # Monday index 0

SUPERVISOR = "http://supervisor/core/api"

# Controller zone name -> the id the library/cloud use for that zone.
# (Steve's system 01:220768; names are the controller's own, stable across TCC/ramses.)
NAME_TO_ID = {
    "Office": "6237752",
    "Kitchen": "6237753",
    "Bedroom": "6237754",
    "Playroom": "6238085",
    "Guest Room": "6238401",
    "Living Room": "6238402",
    "Hall": "6238403",
    "Rays Bedroom": "8248133",
    "Ray's Bedroom": "8248133",
    "Ray’s Bedroom": "8248133",
}


def _num(v):
    try:
        return round(float(v), 1)
    except (TypeError, ValueError):
        return None


class RamsesEngine:
    backend = "local"

    def __init__(self, loc_idx: int = 0) -> None:
        self._token = os.getenv("SUPERVISOR_TOKEN", "")
        self._session: aiohttp.ClientSession | None = None
        self._zones: list[dict] = []          # [{id,name,entity_id,idx,min,max}]
        self._by_id: dict[str, dict] = {}      # id -> zone dict
        self._sched: dict[str, dict] = {}      # id -> normalised weekly schedule
        self._connected = False

    # ---- lifecycle -------------------------------------------------------
    async def start(self) -> None:
        if not self._token:
            raise RuntimeError("No SUPERVISOR_TOKEN — enable homeassistant_api for the add-on")
        self._session = aiohttp.ClientSession(
            headers={"Authorization": f"Bearer {self._token}"})
        await self._discover()

    async def close(self) -> None:
        if self._session:
            await self._session.close()

    @property
    def connected(self) -> bool:
        return self._connected and bool(self._zones)

    # ---- HA REST helpers -------------------------------------------------
    async def _get_states(self) -> list[dict]:
        async with self._session.get(f"{SUPERVISOR}/states") as r:
            r.raise_for_status()
            return await r.json()

    async def _get_state(self, entity_id: str) -> dict:
        async with self._session.get(f"{SUPERVISOR}/states/{entity_id}") as r:
            r.raise_for_status()
            return await r.json()

    async def _call(self, domain: str, service: str, data: dict) -> None:
        url = f"{SUPERVISOR}/services/{domain}/{service}"
        async with self._session.post(url, json=data) as r:
            if r.status >= 400:
                txt = await r.text()
                raise RuntimeError(f"{domain}.{service} failed ({r.status}): {txt[:200]}")

    # ---- discovery -------------------------------------------------------
    async def _discover(self) -> None:
        states = await self._get_states()
        zones = []
        for s in states:
            eid = s.get("entity_id", "")
            if not eid.startswith("climate."):
                continue
            a = s.get("attributes", {}) or {}
            if a.get("zone_index") is None:
                continue  # the controller itself has no zone_index
            cname = (a.get("params", {}) or {}).get("name") or a.get("friendly_name")
            zid = NAME_TO_ID.get((cname or "").strip())
            if not zid:
                _LOGGER.warning("ramses zone '%s' (%s) not in name map — skipped", cname, eid)
                continue
            zones.append({
                "id": zid, "name": (cname or "").strip(), "entity_id": eid,
                "idx": a.get("zone_index"),
                "min": _num(a.get("min_temp")) or 5.0,
                "max": _num(a.get("max_temp")) or 35.0,
            })
        zones.sort(key=lambda z: str(z["idx"]))
        self._zones = zones
        self._by_id = {z["id"]: z for z in zones}
        self._connected = bool(zones)
        _LOGGER.info("ramses_cc: discovered %d zone(s): %s",
                     len(zones), ", ".join(f"{z['name']}={z['entity_id']}" for z in zones))

    def _find(self, zone_id: str) -> dict:
        z = self._by_id.get(str(zone_id))
        if not z:
            raise KeyError(zone_id)
        return z

    # ---- entities --------------------------------------------------------
    async def zones(self) -> list[dict]:
        if not self.connected:
            raise RuntimeError("not connected")
        return [{"id": z["id"], "name": z["name"], "type": "heating",
                 "min": z["min"], "max": z["max"], "maxSwitchpoints": 6}
                for z in self._zones]

    # ---- time helpers (local) --------------------------------------------
    def _local_now(self) -> datetime:
        return datetime.now().astimezone()

    def today_dow(self) -> str:
        return DAY_ORDER[self._local_now().weekday()]

    def next_midnight_iso(self) -> str:
        n = self._local_now()
        m = (n + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        return m.isoformat()

    def now_ge(self, iso: str) -> bool:
        try:
            t = datetime.fromisoformat(str(iso))
            if t.tzinfo is None:
                t = t.replace(tzinfo=self._local_now().tzinfo)
            return self._local_now() >= t
        except Exception:
            return False

    def _next_switch(self, sched: dict, now: datetime):
        for add in range(0, 8):
            d = now + timedelta(days=add)
            for sp in sorted(sched.get(DAY_ORDER[d.weekday()], []), key=lambda s: s["time"]):
                hh, mm = (int(x) for x in sp["time"].split(":"))
                cand = d.replace(hour=hh, minute=mm, second=0, microsecond=0)
                if cand > now:
                    return cand, sp.get("temp")
        return None, None

    # ---- live status -----------------------------------------------------
    async def snapshot(self) -> list[dict]:
        now = self._local_now()
        results = await asyncio.gather(
            *[self._get_state(z["entity_id"]) for z in self._zones],
            return_exceptions=True)
        out = []
        for z, st in zip(self._zones, results):
            e = {"id": z["id"], "name": z["name"], "type": "heating",
                 "mode": None, "overridden": False}
            if isinstance(st, Exception):
                out.append(e)
                continue
            a = st.get("attributes", {}) or {}
            e["current"] = _num(a.get("current_temperature"))
            e["target"] = _num(a.get("temperature"))
            md = a.get("mode") or {}
            mode = md.get("mode") if isinstance(md, dict) else None
            e["mode"] = mode
            overridden = bool(mode and mode != "follow_schedule")
            e["overridden"] = overridden
            until = md.get("until") if isinstance(md, dict) else None
            # opportunistically cache any schedule already on the entity
            sch = a.get("schedule")
            if isinstance(sch, list) and sch:
                self._sched[z["id"]] = self._to_norm(sch)
            if overridden and until:
                e["changesAt"] = until
            else:
                cached = self._sched.get(z["id"])
                if cached:
                    cand, temp = self._next_switch(cached, now)
                    if cand:
                        e["changesAt"] = cand.isoformat()
                        e["changesTo"] = temp
            out.append(e)
        return out

    # ---- schedules -------------------------------------------------------
    async def _read_schedule_attr(self, entity_id: str):
        st = await self._get_state(entity_id)
        sch = (st.get("attributes", {}) or {}).get("schedule")
        return sch if isinstance(sch, list) and sch else None

    async def get_live(self, zone_id: str) -> dict:
        z = self._find(zone_id)
        sch = await self._read_schedule_attr(z["entity_id"])
        if sch is None:
            # ask ramses to fetch it from the controller over RF, then poll
            await self._call("ramses_cc", "get_zone_schedule", {"entity_id": z["entity_id"]})
            for _ in range(10):
                await asyncio.sleep(1.0)
                sch = await self._read_schedule_attr(z["entity_id"])
                if sch:
                    break
        if sch is None:
            raise RuntimeError("Schedule not available yet — try 'Load from controller' again")
        norm = self._to_norm(sch)
        self._sched[z["id"]] = norm
        return norm

    async def push(self, zone_id: str, norm: dict) -> dict:
        z = self._find(zone_id)
        sched = self._to_ramses(norm)
        await self._call("ramses_cc", "set_zone_schedule",
                         {"entity_id": z["entity_id"], "schedule": sched})
        self._sched[z["id"]] = norm
        return {"ok": True}

    async def pull(self, zone_ids=None) -> dict:
        """Force ramses to fetch schedules from the controller into the entities."""
        targets = [self._find(z) for z in (zone_ids or [z["id"] for z in self._zones])]
        results = []
        for z in targets:
            try:
                await self._call("ramses_cc", "get_zone_schedule", {"entity_id": z["entity_id"]})
                sch = None
                for _ in range(10):
                    await asyncio.sleep(1.0)
                    sch = await self._read_schedule_attr(z["entity_id"])
                    if sch:
                        break
                if sch:
                    self._sched[z["id"]] = self._to_norm(sch)
                    results.append({"zone": z["id"], "status": "ok"})
                else:
                    results.append({"zone": z["id"], "status": "timeout"})
            except Exception as err:
                results.append({"zone": z["id"], "status": f"error: {err}"})
        ok = sum(1 for r in results if r["status"] == "ok")
        return {"ok": ok > 0, "loaded": ok, "total": len(targets), "results": results}

    # ---- boost (timed override) & cancel ---------------------------------
    async def boost(self, zone_ids, temp, minutes=None, until_iso=None) -> dict:
        if until_iso:
            until = datetime.fromisoformat(str(until_iso).replace("Z", "+00:00"))
            if until.tzinfo is None:
                until = until.replace(tzinfo=self._local_now().tzinfo)
            until = until.astimezone()
        else:
            until = self._local_now() + timedelta(minutes=int(minutes))
        until_str = until.strftime("%Y-%m-%d %H:%M:%S")
        done = []
        for zid in zone_ids:
            z = self._find(zid)
            await self._call("ramses_cc", "set_zone_mode", {
                "entity_id": z["entity_id"], "mode": "temporary_override",
                "setpoint": float(temp), "until": until_str})
            done.append(str(zid))
        return {"ok": True, "zones": done, "until": until.isoformat(), "temp": float(temp)}

    async def cancel(self, zone_ids) -> dict:
        for zid in zone_ids:
            z = self._find(zid)
            await self._call("ramses_cc", "reset_zone_mode", {"entity_id": z["entity_id"]})
        return {"ok": True, "zones": [str(z) for z in zone_ids]}

    # ---- conversion (ramses <-> normalised) ------------------------------
    def _to_norm(self, sched: list) -> dict:
        out = {d: [] for d in DAY_ORDER}
        for day in sched or []:
            dow = day.get("day_of_week")
            try:
                short = DAY_ORDER[int(dow)]
            except (TypeError, ValueError, IndexError):
                continue
            sps = []
            for sp in day.get("switchpoints", []):
                t = str(sp.get("time_of_day"))[:5]
                sps.append({"time": t, "temp": float(sp["heat_setpoint"])})
            out[short] = sorted(sps, key=lambda s: s["time"])
        return out

    def _to_ramses(self, norm: dict) -> list:
        sched = []
        for i, short in enumerate(DAY_ORDER):
            sps = []
            for sp in sorted(norm.get(short, []), key=lambda s: s["time"]):
                sps.append({"time_of_day": sp["time"][:5],
                            "heat_setpoint": round(float(sp["temp"]), 1)})
            sched.append({"day_of_week": i, "switchpoints": sps})
        return sched
