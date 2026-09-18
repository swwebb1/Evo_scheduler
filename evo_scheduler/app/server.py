"""Evo Scheduler backend — FastAPI app served through Home Assistant ingress.

Routes (the frontend calls these with paths relative to the ingress root):
    GET  /status                 -> {connected: bool, zones: int}
    GET  /zones                  -> Zone[]
    GET  /zones/{id}/live        -> Schedule
    POST /zones/{id}/push        -> {ok:true}   body: {schedule: Schedule}
    GET  /library                -> LibraryEntry[]
    PUT  /library                -> {ok:true}    body: LibraryEntry[]
The SPA is mounted at "/" last, so the API paths take priority.
Library lives in /data (persistent, included in add-on backups).
"""
from __future__ import annotations

import json
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Body, FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles

from evohomeasync2 import exceptions as evo_exc
from engine import EvoEngine

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
_LOGGER = logging.getLogger("evo.server")

OPTIONS = Path("/data/options.json")
LIBRARY = Path("/data/library.json")
STATIC = Path(__file__).parent / "static"

engine: EvoEngine | None = None


def load_options() -> dict:
    if OPTIONS.is_file():
        return json.loads(OPTIONS.read_text())
    return {  # dev fallback outside the add-on
        "username": os.getenv("EVO_USER", ""),
        "password": os.getenv("EVO_PASS", ""),
        "location_idx": int(os.getenv("EVO_LOC", "0")),
    }


@asynccontextmanager
async def lifespan(app: FastAPI):
    global engine
    opt = load_options()
    engine = EvoEngine(opt.get("username", ""), opt.get("password", ""),
                       int(opt.get("location_idx", 0)))
    try:
        await engine.start()
        _LOGGER.info("Connected to TCC — %d zone(s)", len(await engine.zones()))
    except Exception as err:  # keep serving so the UI can show the error
        _LOGGER.error("Startup: could not connect to Evohome/TCC: %s", err)
    yield
    if engine:
        await engine.close()


app = FastAPI(lifespan=lifespan, title="Evo Scheduler")


def _ready() -> EvoEngine:
    if engine is None or not engine.connected:
        raise HTTPException(503, "Not connected to Evohome yet — "
                                 "check the add-on log and your credentials.")
    return engine


@app.get("/status")
async def status():
    if engine and engine.connected:
        try:
            return {"connected": True, "zones": len(await engine.zones())}
        except Exception:
            pass
    return {"connected": False, "zones": 0}


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
        raise HTTPException(429, "TCC rate limit reached — wait a minute and retry")


@app.post("/zones/{zone_id}/push")
async def push(zone_id: str, payload: dict = Body(...)):
    sched = payload.get("schedule")
    if not isinstance(sched, dict):
        raise HTTPException(400, "Body must be {\"schedule\": {\"Mon\":[...], ...}}")
    try:
        return await _ready().push(zone_id, sched)
    except KeyError:
        raise HTTPException(404, "Unknown zone")
    except (evo_exc.BadScheduleUploadedError, evo_exc.InvalidScheduleError) as err:
        raise HTTPException(422, f"Evohome rejected the schedule: {err}")
    except evo_exc.ApiRateLimitExceededError:
        raise HTTPException(429, "TCC rate limit reached — wait a minute and retry")


@app.get("/library")
async def get_library():
    if LIBRARY.is_file():
        try:
            return json.loads(LIBRARY.read_text())
        except ValueError:
            _LOGGER.warning("library.json unreadable; starting empty")
    return []


@app.put("/library")
async def put_library(lib: list = Body(...)):
    try:
        LIBRARY.write_text(json.dumps(lib, indent=2))
    except OSError as err:
        raise HTTPException(500, f"Could not save library: {err}")
    return {"ok": True}


# SPA last, so API routes win
app.mount("/", StaticFiles(directory=str(STATIC), html=True), name="spa")
