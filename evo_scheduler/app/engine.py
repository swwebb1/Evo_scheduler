"""Evohome engine — wrapper over evohome-async (evohomeasync2).

Normalised schedule model used by the UI:
    Schedule = { "Mon": [ {"time":"HH:MM","temp":20.5} | {"time":"HH:MM","state":"On"/"Off"} ], ... }

Verified against evohome-async 1.0.6 (import name: evohomeasync2).
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import aiohttp
from evohomeasync2 import AbstractTokenManager, EvohomeClient

_LOGGER = logging.getLogger("evo.engine")
UTC = timezone.utc

DAY_TO_SHORT = {"Monday": "Mon", "Tuesday": "Tue", "Wednesday": "Wed", "Thursday": "Thu",
                "Friday": "Fri", "Saturday": "Sat", "Sunday": "Sun"}
SHORT_TO_DAY = {v: k for k, v in DAY_TO_SHORT.items()}
DAY_ORDER = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]  # Monday index 0

TOKEN_FILE = Path("/data/token.json")


def _num(v):
    try:
        return round(float(v), 1)
    except (TypeError, ValueError):
        return None


class FileTokenManager(AbstractTokenManager):
    async def save_access_token(self) -> None:
        try:
            TOKEN_FILE.write_text(json.dumps(self._export_access_token()))
        except OSError as err:
            _LOGGER.warning("Could not write token cache: %s", err)

    def restore(self) -> None:
        if not TOKEN_FILE.is_file():
            return
        try:
            self._import_access_token(json.loads(TOKEN_FILE.read_text()))
            _LOGGER.info("Restored cached access token")
        except (OSError, KeyError, ValueError) as err:
            _LOGGER.warning("Ignoring unreadable token cache: %s", err)


class EvoEngine:
    def __init__(self, username: str, password: str, loc_idx: int = 0) -> None:
        self._user, self._pass, self._loc_idx = username, password, loc_idx
        self._session = None
        self._tm = None
        self._evo = None
        self._loc = None
        self._tcs = None
        self._lock = asyncio.Lock()
        self._last_update = 0.0
        self._sched: dict[str, dict] = {}   # live schedule cache (normalised)
        self._sched_at = 0.0
        self._warming = False

    # ---- lifecycle -------------------------------------------------------
    async def start(self) -> None:
        if not self._user or not self._pass:
            raise RuntimeError("No TCC username/password configured")
        self._session = aiohttp.ClientSession()
        self._tm = FileTokenManager(self._user, self._pass, self._session)
        self._tm.restore()
        self._evo = EvohomeClient(self._tm, websession=self._session)
        await self.refresh_config()

    async def refresh_config(self) -> None:
        async with self._lock:
            await self._evo.update()
            await self._tm.save_access_token()
            self._last_update = time.monotonic()
        try:
            self._loc = self._evo.locations[self._loc_idx]
        except IndexError as err:
            raise RuntimeError(f"location_idx {self._loc_idx} out of range") from err
        systems = [s for gwy in self._loc.gateways for s in gwy.systems]
        if not systems:
            raise RuntimeError("No temperature control system found")
        self._tcs = systems[0]
        asyncio.create_task(self._warm_schedules())  # background, non-blocking

    async def close(self) -> None:
        if self._session:
            await self._session.close()

    @property
    def connected(self) -> bool:
        return self._tcs is not None

    # ---- entities --------------------------------------------------------
    def _entities(self) -> list:
        ents = list(self._tcs.zones)
        if self._tcs.hotwater:
            ents.append(self._tcs.hotwater)
        return ents

    @staticmethod
    def _is_dhw(ent) -> bool:
        return ent.__class__.__name__ == "HotWater"

    def _find(self, zone_id: str):
        for ent in self._entities():
            if str(ent.id) == str(zone_id):
                return ent
        raise KeyError(zone_id)

    async def zones(self) -> list[dict]:
        if not self.connected:
            raise RuntimeError("not connected")
        out = []
        for z in self._tcs.zones:
            out.append({"id": str(z.id), "name": z.name, "type": "heating",
                        "min": float(z.min_heat_setpoint), "max": float(z.max_heat_setpoint)})
        if self._tcs.hotwater:
            hw = self._tcs.hotwater
            out.append({"id": str(hw.id), "name": hw.name or "Hot Water",
                        "type": "dhw", "min": 0, "max": 1})
        return out

    # ---- schedule cache + next change ------------------------------------
    async def _warm_schedules(self, force: bool = False) -> None:
        if self._warming:
            return
        if not force and self._sched and (time.monotonic() - self._sched_at) < 21600:
            return
        self._warming = True
        try:
            for z in self._tcs.zones:
                try:
                    async with self._lock:
                        daily = await z.get_schedule()
                        await self._tm.save_access_token()
                    self._sched[str(z.id)] = self._to_norm(daily, False)
                except Exception as err:
                    _LOGGER.warning("warm schedule %s failed: %s", z.id, err)
            self._sched_at = time.monotonic()
        finally:
            self._warming = False

    def _local_now(self) -> datetime:
        try:
            n = self._loc.now()
            return n if n.tzinfo else n.replace(tzinfo=UTC)
        except Exception:
            return datetime.now(UTC)

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
    async def _refresh(self, force: bool = False) -> None:
        if force or (time.monotonic() - self._last_update) > 15:
            async with self._lock:
                await self._evo.update()
                await self._tm.save_access_token()
                self._last_update = time.monotonic()

    async def snapshot(self) -> list[dict]:
        await self._refresh()
        if not self._sched and not self._warming:
            asyncio.create_task(self._warm_schedules())
        elif self._sched and (time.monotonic() - self._sched_at) > 21600:
            asyncio.create_task(self._warm_schedules())
        now = self._local_now()
        out = []
        for z in self._entities():
            dhw = self._is_dhw(z)
            try:
                ss = getattr(z, "setpoint_status", None) or {}
            except Exception:
                ss = {}
            mode = ss.get("setpoint_mode") or ss.get("mode")
            if mode is None:
                try:
                    mode = str(z.mode) if getattr(z, "mode", None) else None
                except Exception:
                    mode = None
            overridden = bool(mode and "override" in str(mode).lower())
            until = ss.get("until") or ss.get("time_until")
            e = {"id": str(z.id), "name": (z.name or ("Hot Water" if dhw else str(z.id))),
                 "type": "dhw" if dhw else "heating", "mode": mode, "overridden": overridden}
            if dhw:
                e["state"] = getattr(z, "state", None)
            else:
                try:
                    e["current"] = _num(z.temperature)
                except Exception:
                    e["current"] = None
                try:
                    e["target"] = _num(z.target_heat_temperature)
                except Exception:
                    e["target"] = None
            # when does the setpoint next change?
            if overridden and until:
                e["changesAt"] = until
            else:
                sched = self._sched.get(str(z.id))
                if sched:
                    cand, temp = self._next_switch(sched, now)
                    if cand:
                        e["changesAt"] = cand.isoformat()
                        e["changesTo"] = temp
            out.append(e)
        return out

    # ---- schedules -------------------------------------------------------
    async def get_live(self, zone_id: str) -> dict:
        ent = self._find(zone_id)
        async with self._lock:
            daily = await ent.get_schedule()
            await self._tm.save_access_token()
        norm = self._to_norm(daily, self._is_dhw(ent))
        if not self._is_dhw(ent):
            self._sched[str(zone_id)] = norm
        return norm

    async def push(self, zone_id: str, norm: dict) -> dict:
        ent = self._find(zone_id)
        daily = self._to_tcc(norm, self._is_dhw(ent))
        async with self._lock:
            await ent.set_schedule(daily)
            await self._tm.save_access_token()
        if not self._is_dhw(ent):
            self._sched[str(zone_id)] = norm  # keep cache accurate
        return {"ok": True}

    # ---- boost (timed override, by minutes or explicit until) & cancel ----
    async def boost(self, zone_ids, temp, minutes=None, until_iso=None) -> dict:
        if until_iso:
            until = datetime.fromisoformat(str(until_iso).replace("Z", "+00:00"))
            if until.tzinfo is None:
                until = until.replace(tzinfo=UTC)
        else:
            until = datetime.now(UTC) + timedelta(minutes=int(minutes))
        until = until.astimezone(UTC)
        done = []
        async with self._lock:
            for zid in zone_ids:
                z = self._find(zid)
                if self._is_dhw(z):
                    continue
                await z.set_temperature(float(temp), until=until)
                done.append(str(zid))
            await self._tm.save_access_token()
        self._last_update = 0.0
        return {"ok": True, "zones": done, "until": until.isoformat(), "temp": float(temp)}

    async def cancel(self, zone_ids) -> dict:
        async with self._lock:
            for zid in zone_ids:
                await self._find(zid).reset()
            await self._tm.save_access_token()
        self._last_update = 0.0
        return {"ok": True, "zones": [str(z) for z in zone_ids]}

    # ---- conversion ------------------------------------------------------
    def _to_norm(self, daily: list, is_dhw: bool) -> dict:
        out = {d: [] for d in DAY_ORDER}
        for day in daily or []:
            dow = day.get("day_of_week")
            short = DAY_TO_SHORT.get(dow)
            if short is None:
                try:
                    short = DAY_ORDER[int(dow)]
                except (TypeError, ValueError, IndexError):
                    continue
            sps = []
            for sp in day.get("switchpoints", []):
                t = str(sp["time_of_day"])[:5]
                if is_dhw:
                    sps.append({"time": t, "state": sp["dhw_state"]})
                else:
                    sps.append({"time": t, "temp": float(sp["heat_setpoint"])})
            out[short] = sorted(sps, key=lambda s: s["time"])
        return out

    def _to_tcc(self, norm: dict, is_dhw: bool) -> list:
        daily = []
        for short in DAY_ORDER:
            sps = []
            for sp in sorted(norm.get(short, []), key=lambda s: s["time"]):
                tod = sp["time"] + (":00" if len(sp["time"]) == 5 else "")
                if is_dhw:
                    sps.append({"dhw_state": sp["state"], "time_of_day": tod})
                else:
                    sps.append({"heat_setpoint": round(float(sp["temp"]), 1), "time_of_day": tod})
            daily.append({"day_of_week": SHORT_TO_DAY[short], "switchpoints": sps})
        return daily
