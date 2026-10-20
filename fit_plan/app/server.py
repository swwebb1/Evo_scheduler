"""Fit Plan backend — FastAPI served through Home Assistant ingress.

Two JSON documents live in /data (persisted by the Supervisor and included in HA backups):
  plan.json  — targets, weekly schedule, kettlebell sessions, week-by-week progression, exercise library
  log.json   — weigh-ins (with optional waist) and completed sessions
"""
from __future__ import annotations

import json
import logging
import os
import tempfile
from pathlib import Path

from fastapi import Body, FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles

from defaults import default_log, default_plan
from migrate import migrate

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
_LOGGER = logging.getLogger("fitplan")

DATA = Path(os.getenv("FIT_DATA", "/data"))
PLAN = DATA / "plan.json"
LOG = DATA / "log.json"
STATIC = Path(__file__).parent / "static"


def _read(path: Path, factory):
    if path.is_file():
        try:
            return json.loads(path.read_text())
        except ValueError:
            _LOGGER.warning("%s unreadable; keeping a copy and using defaults", path.name)
            path.rename(path.with_suffix(".corrupt.json"))
    data = factory()
    _write(path, data)
    return data


def _write(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    with os.fdopen(fd, "w") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)
    os.replace(tmp, path)


app = FastAPI(title="Fit Plan")


@app.get("/api/plan")
def get_plan():
    plan = _read(PLAN, default_plan)
    if migrate(plan):
        if PLAN.is_file():
            _write(PLAN.with_suffix(".v1-backup.json"), json.loads(PLAN.read_text()))
        _write(PLAN, plan)
        _LOGGER.info("Plan upgraded to version %s", plan["version"])
    return plan


@app.put("/api/plan")
def put_plan(plan: dict = Body(...)):
    for key in ("sessions", "schedule", "weeks", "targets"):
        if key not in plan:
            raise HTTPException(400, f"Plan is missing '{key}'")
    if not isinstance(plan["sessions"], list):
        raise HTTPException(400, "'sessions' must be a list")
    _write(PLAN, plan)
    return plan


@app.post("/api/plan/reset")
def reset_plan():
    if PLAN.is_file():
        _write(PLAN.with_suffix(".backup.json"), json.loads(PLAN.read_text()))
    plan = default_plan()
    _write(PLAN, plan)
    return plan


@app.get("/api/log")
def get_log():
    return _read(LOG, default_log)


@app.put("/api/log")
def put_log(log: dict = Body(...)):
    if not isinstance(log.get("weights"), list) or not isinstance(log.get("done"), list):
        raise HTTPException(400, "Log needs 'weights' and 'done' lists")
    log["weights"].sort(key=lambda w: w.get("date", ""))
    _write(LOG, log)
    return log


@app.get("/api/health")
def health():
    return {"ok": True}


app.mount("/", StaticFiles(directory=str(STATIC), html=True), name="spa")
