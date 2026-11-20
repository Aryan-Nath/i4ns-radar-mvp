"""FastAPI: GET /api/day?date=YYYY-MM-DD  ->  hourly forecast / bounds / actual / NN update."""
import math
from datetime import date as Date
from pathlib import Path

import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from i4ns_radar_mvp import bounds as B
from i4ns_radar_mvp.data import STATION, UNITS, VARS
from i4ns_radar_mvp.model import Predictor
from i4ns_radar_mvp.pipeline import resources, run_day

app = FastAPI(title="i4NS Radar MVP")
WEB_DIST = Path(__file__).resolve().parent / "web" / "dist"
_pred = None


def _num(x):
    return None if x is None or (isinstance(x, float) and math.isnan(x)) else round(float(x), 3)


@app.get("/api/day")
def get_day(date: Date):
    global _pred
    if _pred is None:
        try:
            _pred = Predictor()
        except FileNotFoundError as exc:
            raise HTTPException(
                503, "Model artifact is missing. Restore artifacts/radar_mlp.pt or run scripts/train.py."
            ) from exc
    try:
        hourly, clim = resources()
    except OSError as exc:
        raise HTTPException(
            503, "Buoy archive could not be loaded. Check data/raw/ and the NOAA download connection."
        ) from exc
    res = run_day(date, _pred, hourly, clim)
    if res is None:
        raise HTTPException(404, "No 08:00 observation for that day (or date outside data).")
    T = res["tables"]
    hours = []
    for t in T["actual"].index:
        row = {"hour": t.strftime("%Y-%m-%dT%H:%M"), "vars": {}}
        for v in VARS:
            row["vars"][v] = {
                "forecast": _num(T["forecast"].loc[t, v]), "lo": _num(T["lo"].loc[t, v]),
                "hi": _num(T["hi"].loc[t, v]), "actual": _num(T["actual"].loc[t, v]),
                "in_bounds": None if math.isnan(T["actual"].loc[t, v]) else bool(T["in_bounds"].loc[t, v]),
                "nn_updated": _num(T["nn_updated"].loc[t, v])}
        hours.append(row)
    f = res["flag"]
    flag = None if f is None else {"time": f["time"].strftime("%Y-%m-%dT%H:%M"), "variables": f["variables"],
                                   "values": f["values"], "bounds": f["bounds"]}
    nn_paths = {t.strftime("%Y-%m-%dT%H:%M"): {
        "hours": [(t + pd.Timedelta(hours=k + 1)).strftime("%Y-%m-%dT%H:%M") for k in range(len(p))],
        "vars": {v: [_num(p[k, j]) for k in range(len(p))] for j, v in enumerate(VARS)}}
        for t, p in res["paths"].items()}
    return {"nn_paths": nn_paths, "date": str(res["date"]), "bounds_rule": {"source": "NWSI 10-813 (wind, persistence); empirical for others",
                              "half_width": {k: round(x, 3) for k, x in B.HALF_WIDTH.items()},
                              "wind_note": "wind out of bounds only if |actual-forecast| >= 11.5 mph (10 kt) AND (forecast >= 13.8 mph (12 kt) OR actual >= 13.8 mph); light-wind misses ignored",
                              "persist_hours": B.PERSIST_HOURS},
             "units": UNITS, "timezone": "America/New_York", "station": STATION,
            "flag": flag, "hours": hours}


@app.get("/", include_in_schema=False)
def index():
    page = WEB_DIST / "index.html"
    if not page.is_file():
        raise HTTPException(503, "Dashboard build is missing. Run npm ci --prefix web, then ./run.sh.")
    return FileResponse(page)


app.mount("/assets", StaticFiles(directory=WEB_DIST / "assets", check_dir=False), name="assets")
