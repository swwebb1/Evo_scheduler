"""Evo Scheduler backend — FastAPI served through Home Assistant ingress."""
from __future__ import annotations

import asyncio
import json
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

from fastapi import Body, FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles

from evohomeasync2 import exceptions as evo_exc
from engine import EvoEngine

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
_LOGGER = logging.getLogger("evo.server")

OPTIONS = Path("/data/options.json")
LIBRARY = Path("/data/library.json")
SHORTCUTS = Path("/data/shortcuts.json")
STATE = Path("/data/state.json")
STATIC = Path(__file__).parent / "static"

engine: EvoEngine | None = None


def load_options() -> dict:
    if OPTIONS.is_file():
        return json.loads(OPTIONS.read_text())
    return {"username": os.getenv("EVO_USER", ""), "password": os.getenv("EVO_PASS", ""),
            "location_idx": int(os.getenv("EVO_LOC", "0"))}


def _read(path: Path, default):
    if path.is_file():
        try:
            return json.loads(path.read_text())
        except ValueError:
            _LOGGER.warning("%s unreadable; using default", path.name)
    return default


def _write(path: Path, data) -> None:
    path.write_text(json.dumps(data, indent=2))


@asynccontextmanager
async def lifespan(app: FastAPI):
    global engine
    opt = load_options()
    engine = EvoEngine(opt.get("username", ""), opt.get("password", ""),
                       int(opt.get("location_idx", 0)))
    try:
        await engine.start()
        _LOGGER.info("Connected to TCC — %d zone(s)", len(await engine.zones()))
    except Exception as err:
        _LOGGER.error("Startup: could not connect to Evohome/TCC: %s", err)
    asyncio.create_task(_dayoff_watch())
    yield
    if engine:
        await engine.close()


app = FastAPI(lifespan=lifespan, title="Evo Scheduler")


def _ready() -> EvoEngine:
    if engine is None or not engine.connected:
        raise HTTPException(503, "Not connected to Evohome yet — check the add-on log and credentials.")
    return engine


def _lib() -> list:
    return _read(LIBRARY, [])


def _lib_entry(lib_id: str) -> dict:
    for e in _lib():
        if e.get("id") == lib_id:
            return e
    raise HTTPException(404, "Unknown plan")


def _seed_shortcuts(zones: list[dict]) -> list:
    by_name = {z["name"].lower(): z["id"] for z in zones}
    def ids(*names):
        return [by_name[n.lower()] for n in names if n.lower() in by_name]
    seeds = [{"id": "sc_lounge", "name": "Lounge + Kitchen", "zoneIds": ids("Living Room", "Kitchen"), "temp": 21, "minutes": 120},
             {"id": "sc_bed", "name": "Bedroom", "zoneIds": ids("Bedroom"), "temp": 21, "minutes": 60}]
    return [s for s in seeds if s["zoneIds"]]


# ---- everyday --------------------------------------------------------------
@app.get("/status")
async def status():
    if not (engine and engine.connected):
        return {"connected": False, "plan": None, "zones": []}
    try:
        zones = await engine.snapshot()
    except Exception as err:
        _LOGGER.warning("snapshot failed: %s", err)
        zones = []
    return {"connected": True, "plan": _read(STATE, {}).get("plan"), "zones": zones}


@app.post("/apply")
async def apply(payload: dict = Body(...)):
    eng = _ready()
    entry = _lib_entry(payload.get("libraryId", ""))
    zone_ids = payload.get("zoneIds") or list(entry.get("schedules", {}).keys())
    results = []
    for zid in zone_ids:
        sched = entry.get("schedules", {}).get(zid)
        if not sched:
            results.append({"zone": zid, "status": "skipped"})
            continue
        try:
            await eng.push(zid, sched)
            results.append({"zone": zid, "status": "ok"})
        except (evo_exc.BadScheduleUploadedError, evo_exc.InvalidScheduleError) as err:
            results.append({"zone": zid, "status": f"rejected: {err}"})
        except evo_exc.ApiRateLimitExceededError:
            results.append({"zone": zid, "status": "rate-limited"})
    applied = [r["zone"] for r in results if r["status"] == "ok"]
    plan = {"name": entry.get("name"), "libraryId": entry.get("id"),
            "zoneIds": applied, "zoneCount": len(applied),
            "appliedAt": datetime.now(timezone.utc).isoformat()}
    if applied:
        _write(STATE, {"plan": plan})
    return {"ok": bool(applied), "results": results, "plan": plan}


@app.post("/boost")
async def boost(payload: dict = Body(...)):
    eng = _ready()
    zone_ids = payload.get("zoneIds") or []
    if not zone_ids:
        raise HTTPException(400, "No rooms given")
    if "temp" not in payload:
        raise HTTPException(400, "Need temp")
    if not payload.get("minutes") and not payload.get("until"):
        raise HTTPException(400, "Need minutes or until")
    try:
        return await eng.boost(zone_ids, float(payload["temp"]),
                               minutes=payload.get("minutes"), until_iso=payload.get("until"))
    except evo_exc.ApiRateLimitExceededError:
        raise HTTPException(429, "TCC rate limit — wait a minute and retry")


@app.post("/cancel")
async def cancel(payload: dict = Body(...)):
    return await _ready().cancel(payload.get("zoneIds") or [])


@app.get("/shortcuts")
async def get_shortcuts():
    sc = _read(SHORTCUTS, None)
    if sc is None:
        try:
            sc = _seed_shortcuts(await _ready().zones())
        except Exception:
            sc = []
        _write(SHORTCUTS, sc)
    return sc


@app.put("/shortcuts")
async def put_shortcuts(sc: list = Body(...)):
    _write(SHORTCUTS, sc)
    return {"ok": True}


# ---- editor ----------------------------------------------------------------
@app.get("/zones")
async def get_zones():
    return await _ready().zones()


@app.get("/zones/{zone_id}/live")
async def get_live(zone_id: str):
    try:
        return await _ready().get_live(zone_id)
    except KeyError:
        raise HTTPException(404, "Unknown zone")
    except evo_exc.InvalidScheduleError:
        raise HTTPException(404, "No schedule available for this zone")
    except evo_exc.ApiRateLimitExceededError:
        raise HTTPException(429, "TCC rate limit — wait a minute and retry")


@app.post("/zones/{zone_id}/push")
async def push(zone_id: str, payload: dict = Body(...)):
    sched = payload.get("schedule")
    if not isinstance(sched, dict):
        raise HTTPException(400, "Body must be {\"schedule\": {...}}")
    try:
        return await _ready().push(zone_id, sched)
    except KeyError:
        raise HTTPException(404, "Unknown zone")
    except (evo_exc.BadScheduleUploadedError, evo_exc.InvalidScheduleError) as err:
        raise HTTPException(422, f"Evohome rejected the schedule: {err}")
    except evo_exc.ApiRateLimitExceededError:
        raise HTTPException(429, "TCC rate limit — wait a minute and retry")


@app.get("/library")
async def get_library():
    return _lib()


@app.put("/library")
async def put_library(lib: list = Body(...)):
    try:
        _write(LIBRARY, lib)
    except OSError as err:
        raise HTTPException(500, f"Could not save library: {err}")
    return {"ok": True}


# ---- day off ---------------------------------------------------------------
DAYOFF_CONFIG = Path("/data/dayoff_config.json")
DAYOFF_STATE = Path("/data/dayoff_state.json")


def _dayoff_default_cfg():
    return {"planId": None, "sourceDay": "Sat", "zoneIds": []}


@app.get("/dayoff/config")
async def dayoff_get_config():
    return _read(DAYOFF_CONFIG, _dayoff_default_cfg())


@app.put("/dayoff/config")
async def dayoff_put_config(cfg: dict = Body(...)):
    _write(DAYOFF_CONFIG, {"planId": cfg.get("planId"),
                           "sourceDay": cfg.get("sourceDay", "Sat"),
                           "zoneIds": cfg.get("zoneIds") or []})
    return {"ok": True}


@app.get("/dayoff")
async def dayoff_status():
    st = _read(DAYOFF_STATE, {}) or {}
    if not st.get("active"):
        return {"active": False}
    return {"active": True, "revertAt": st.get("revertAt"), "planName": st.get("planName"),
            "sourceDay": st.get("sourceDay"), "zoneCount": len(st.get("zones", {}))}


@app.post("/dayoff/activate")
async def dayoff_activate():
    eng = _ready()
    cfg = _read(DAYOFF_CONFIG, _dayoff_default_cfg())
    if not cfg.get("planId") or not cfg.get("zoneIds"):
        raise HTTPException(400, "Day off isn't set up yet")
    plan = _lib_entry(cfg["planId"])
    src_day = cfg.get("sourceDay", "Sat")
    dow = eng.today_dow()
    saved = {}
    for zid in cfg["zoneIds"]:
        src = (plan.get("schedules", {}).get(zid) or {}).get(src_day)
        if not src:
            continue
        try:
            live = await eng.get_live(zid)
        except Exception as err:
            _LOGGER.warning("day-off get_live %s failed: %s", zid, err)
            continue
        saved[zid] = live.get(dow, [])
        newsched = dict(live)
        newsched[dow] = src
        try:
            await eng.push(zid, newsched)
        except Exception as err:
            _LOGGER.warning("day-off push %s failed: %s", zid, err)
            saved.pop(zid, None)
    if not saved:
        raise HTTPException(422, "Nothing applied — check the plan covers those rooms")
    state = {"active": True, "revertAt": eng.next_midnight_iso(), "dow": dow, "zones": saved,
             "planName": plan.get("name"), "sourceDay": src_day, "zoneCount": len(saved)}
    _write(DAYOFF_STATE, state)
    return {"active": True, "revertAt": state["revertAt"], "planName": state["planName"],
            "sourceDay": src_day, "zoneCount": len(saved)}


@app.post("/dayoff/cancel")
async def dayoff_cancel():
    await _revert_dayoff()
    return {"ok": True}


async def _revert_dayoff():
    st = _read(DAYOFF_STATE, None)
    if not st or not st.get("active"):
        return
    dow = st.get("dow")
    for zid, orig in (st.get("zones") or {}).items():
        try:
            live = await engine.get_live(zid)
            live[dow] = orig
            await engine.push(zid, live)
        except Exception as err:
            _LOGGER.warning("day-off revert %s failed: %s", zid, err)
    _write(DAYOFF_STATE, {"active": False})
    _LOGGER.info("Day off reverted to normal schedule")


async def _dayoff_watch():
    while True:
        try:
            st = _read(DAYOFF_STATE, None)
            if st and st.get("active") and engine and engine.connected:
                if engine.now_ge(st.get("revertAt")):
                    _LOGGER.info("Day off reached midnight — reverting")
                    await _revert_dayoff()
        except Exception as err:
            _LOGGER.warning("day-off watch error: %s", err)
        await asyncio.sleep(60)


app.mount("/", StaticFiles(directory=str(STATIC), html=True), name="spa")
