"""Fixed forecast bounds and flag logic.

Wind thresholds and the persistence rule follow the NWS forecast-amendment criteria
(NWS Instruction 10-813, 30 Oct 2024, sec C1.3.2 and 4.7):
https://www.weather.gov/media/directives/010_pdfs/pd01008013curr.pdf
The other variables have no verified operational threshold; their values are
"empirical, tested on 2024 buoy data".
"""
import numpy as np
import pandas as pd

from .data import VARS

KT_TO_MPH = 1.15078

# --- Wind: NWSI 10-813 sec C1.3.2 ---
WIND_DIFF_KT = 10                        # out of bounds when |actual - forecast| >= 10 kt ...
WIND_MIN_KT = 12                         # ... AND (forecast >= 12 kt OR actual >= 12 kt); light-wind misses ignored
WIND_DIFF_MPH = WIND_DIFF_KT * KT_TO_MPH  # 11.5 mph
WIND_MIN_MPH = WIND_MIN_KT * KT_TO_MPH    # 13.8 mph

# --- Other variables: empirical, tested on 2024 buoy data ---
TEMP_BOUND_C = 3.0      # air temp +/- degC
RH_BOUND_PCT = 15.0     # relative humidity +/- %
SEA_BOUND_C = 1.5       # sea temp +/- degC
PRES_BOUND_HPA = 5.0    # pressure +/- hPa

# --- Persistence: NWSI 10-813 sec 4.7 ("criteria will persist") ---
PERSIST_HOURS = 2       # flag only after this many consecutive out-of-bounds hours; flag time = last of them

HALF_WIDTH = {"wind": WIND_DIFF_MPH, "temp": TEMP_BOUND_C, "rh": RH_BOUND_PCT,
              "sea": SEA_BOUND_C, "pres": PRES_BOUND_HPA}


def make_bounds(fc):
    """lo/hi = forecast -/+ fixed half-width per variable. For wind the band is
    forecast +/- 11.5 mph but it only applies when forecast or actual >= 13.8 mph (light-wind rule)."""
    w = pd.Series(HALF_WIDTH)[list(fc.columns)]
    return fc - w, fc + w


def out_of_bounds(actual, lo, hi):
    """Boolean frame: True where an actual value is out of bounds (NaN actual -> False).
    Wind additionally needs forecast >= 12 kt or actual >= 12 kt."""
    oob = (actual < lo) | (actual > hi)
    if "wind" in oob.columns:
        fc = (lo["wind"] + hi["wind"]) / 2
        a = actual["wind"]
        diff = (a - fc).abs() >= WIND_DIFF_MPH - 1e-9
        windy = (fc >= WIND_MIN_MPH - 1e-9) | (a >= WIND_MIN_MPH - 1e-9)
        oob["wind"] = diff & windy
    return oob


def find_flag(actual, lo, hi, last_hour=20, first_hour=9):
    """First hour (first_hour..last_hour) at which some variable has been out of bounds for
    PERSIST_HOURS consecutive hours (flag time = the confirming, last hour).
    Returns None or dict(time, variables, values, bounds)."""
    oob = out_of_bounds(actual, lo, hi)
    run = oob.copy()
    for k in range(1, PERSIST_HOURS):
        run = run & oob.shift(k, fill_value=False)
    for t in run.index:
        if first_hour <= t.hour <= last_hour and t.date() == run.index[0].date() and run.loc[t].any():
            vs = [v for v in VARS if run.loc[t, v]]
            return {"time": t, "variables": vs,
                    "values": {v: float(actual.loc[t, v]) for v in vs},
                    "bounds": {v: (float(lo.loc[t, v]), float(hi.loc[t, v])) for v in vs}}
    return None
