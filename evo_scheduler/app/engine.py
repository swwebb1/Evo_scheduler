"""Evohome engine — wrapper over evohome-async (evohomeasync2).

Talks to Honeywell/Resideo Total Connect Comfort (TCC). Converts between
TCC's schedule JSON and the normalised model the UI uses:

    Schedule = { "Mon": [ {"time":"HH:MM","temp":20.5} ...        # heating
                        | {"time":"HH:MM","state":"On"|"Off"} ], # dhw
                 ... "Sun": [...] }

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

DAY_TO_SHORT = {
    "Monday": "Mon", "Tuesday": "Tue", "Wednesday": "Wed", "Thursday": "Thu",
    "Friday": "Fri", "Saturday": "Sat", "Sunday": "Sun",
}
SHORT_TO_DAY = {v: k for k, v in DAY_TO_SHORT.items()}
DAY_ORDER = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

TOKEN_FILE = Path("/data/token.json")


def _num(v):
    try:
        return round(float(v), 1)
    except (TypeError, ValueError):
        return None


class FileTokenManager(AbstractTokenManager):
    """Persist the OAuth token to /data so we don't re-auth every call."""

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
        self._user = username
        self._pass = password
        self._loc_idx = loc_idx
        self._session: aiohttp.ClientSession | None = None
        self._tm: FileTokenManager | None = None
        self._evo: EvohomeClient | None = None
        self._tcs = None
        self._lock = asyncio.Lock()
        self._last_update = 0.0

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
            loc = self._evo.locations[self._loc_idx]
        except IndexError as err:
            raise RuntimeError(
                f"location_idx {self._loc_idx} out of range "
                f"({len(self._evo.locations)} location(s) found)") from err
        systems = [s for gwy in loc.gateways for s in gwy.systems]
        if not systems:
            raise RuntimeError("No temperature control system found")
        if len(systems) > 1:
            _LOGGER.warning("%d control systems found; using the first", len(systems))
        self._tcs = systems[0]

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

    # ---- live status (current temps / mode) ------------------------------
    async def _refresh(self, force: bool = False) -> None:
        if force or (time.monotonic() - self._last_update) > 15:
            async with self._lock:
                await self._evo.update()
                await self._tm.save_access_token()
                self._last_update = time.monotonic()

    async def snapshot(self) -> list[dict]:
        await self._refresh()
        out = []
        for z in self._entities():
            dhw = self._is_dhw(z)
            ss = {}
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
            entry = {"id": str(z.id), "type": "dhw" if dhw else "heating",
                     "name": (z.name or ("Hot Water" if dhw else str(z.id))),
                     "mode": mode}
            if dhw:
                entry["state"] = getattr(z, "state", None)
            else:
                try:
                    entry["current"] = _num(z.temperature)
                except Exception:
                    entry["current"] = None
                try:
                    entry["target"] = _num(z.target_heat_temperature)
                except Exception:
                    entry["target"] = None
            u = ss.get("until") or ss.get("time_until")
            if u:
                entry["until"] = u
            out.append(entry)
        return out

    # ---- schedules -------------------------------------------------------
    async def get_live(self, zone_id: str) -> dict:
        ent = self._find(zone_id)
        async with self._lock:
            daily = await ent.get_schedule()
            await self._tm.save_access_token()
        return self._to_norm(daily, self._is_dhw(ent))

    async def push(self, zone_id: str, norm: dict) -> dict:
        ent = self._find(zone_id)
        daily = self._to_tcc(norm, self._is_dhw(ent))
        async with self._lock:
            await ent.set_schedule(daily)
            await self._tm.save_access_token()
        return {"ok": True}

    # ---- boost (timed override) & cancel ---------------------------------
    async def boost(self, zone_ids: list[str], temp: float, minutes: int) -> dict:
        until = datetime.now(UTC) + timedelta(minutes=int(minutes))
        done = []
        async with self._lock:
            for zid in zone_ids:
                z = self._find(zid)
                if self._is_dhw(z):
                    continue
                await z.set_temperature(float(temp), until=until)
                done.append(str(zid))
            await self._tm.save_access_token()
        self._last_update = 0.0  # force fresh status next read
        return {"ok": True, "zones": done, "until": until.isoformat(), "temp": float(temp)}

    async def cancel(self, zone_ids: list[str]) -> dict:
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
                tod = sp["time"]
                if len(tod) == 5:
                    tod += ":00"
                if is_dhw:
                    sps.append({"dhw_state": sp["state"], "time_of_day": tod})
                else:
                    sps.append({"heat_setpoint": round(float(sp["temp"]), 1),
                                "time_of_day": tod})
            daily.append({"day_of_week": SHORT_TO_DAY[short], "switchpoints": sps})
        return daily
