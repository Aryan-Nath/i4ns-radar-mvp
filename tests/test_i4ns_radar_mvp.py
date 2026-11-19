import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
from fastapi.testclient import TestClient

from i4ns_radar_mvp import bounds as B
from i4ns_radar_mvp.bounds import make_bounds, find_flag, out_of_bounds
from i4ns_radar_mvp.data import VARS


def test_bounds_math():
    fc = pd.DataFrame({"wind": [20.0], "temp": [-5.0], "rh": [50.0], "sea": [10.0], "pres": [1010.0]})
    lo, hi = make_bounds(fc)
    assert abs(lo["wind"][0] - (20 - 11.5)) < 0.01 and abs(hi["wind"][0] - 31.5) < 0.01
    assert (lo["temp"][0], hi["temp"][0]) == (-8.0, -2.0)
    assert (lo["rh"][0], hi["rh"][0]) == (35.0, 65.0)
    assert (lo["sea"][0], hi["sea"][0]) == (8.5, 11.5)
    assert (lo["pres"][0], hi["pres"][0]) == (1005.0, 1015.0)


def _oob(fc_wind, act_wind):
    fc = pd.DataFrame(10.0, index=[0], columns=VARS); fc["wind"] = fc_wind
    act = fc.copy(); act["wind"] = act_wind
    lo, hi = make_bounds(fc)
    return bool(out_of_bounds(act, lo, hi)["wind"][0])


def test_wind_light_wind_rule():
    assert not _oob(2.0, 13.0)        # miss 11 mph < 11.5: in bounds
    assert not _oob(0.5, 12.5)        # miss 12 mph but both < 13.8 mph (12 kt): ignored
    assert _oob(2.0, 14.0)            # miss 12 mph and actual >= 13.8: out
    assert _oob(20.0, 8.0)            # miss 12 mph and forecast >= 13.8: out
    assert not _oob(20.0, 9.0)        # miss 11 mph: in


def _frames(wind_actual):
    idx = pd.date_range("2024-05-01 08:00", periods=13, freq="h")
    fc = pd.DataFrame(20.0, index=idx, columns=VARS)
    act = fc.copy(); act["wind"] = wind_actual
    lo, hi = make_bounds(fc)
    return act, lo, hi


def test_flag_needs_two_consecutive_hours():
    w = [20.0] * 13; w[3] = 40.0; w[5] = 40.0        # isolated misses, not consecutive
    assert find_flag(*_frames(w)) is None
    w[6] = 40.0                                       # 13:00 and 14:00
    f = find_flag(*_frames(w))
    assert f["time"] == pd.Timestamp("2024-05-01 14:00")   # confirmed at the 2nd hour
    assert f["variables"] == ["wind"] and f["values"]["wind"] == 40.0


def test_flag_second_hour_is_flag_time():
    w = [20.0] * 13; w[3] = 40.0; w[4] = 40.0         # 11:00, 12:00
    assert find_flag(*_frames(w))["time"] == pd.Timestamp("2024-05-01 12:00")


def test_no_flag_inside_bounds_or_missing():
    w = [25.0] * 13; w[4] = float("nan")
    assert find_flag(*_frames(w)) is None
    w = [20.0] * 13; w[3] = 40.0; w[4] = float("nan"); w[5] = 40.0; w[6] = 40.0   # NaN breaks a run
    f = find_flag(*_frames(w)); assert f["time"] == pd.Timestamp("2024-05-01 14:00")


def test_no_2024_in_training():
    from scripts import train
    assert train.TRAIN_YEAR == 2023
    from i4ns_radar_mvp.data import load_years
    assert load_years([train.TRAIN_YEAR]).index.max() < pd.Timestamp("2024-01-01")
    src = (Path(train.__file__)).read_text()
    assert "2024" not in src


def test_api_returns_200():
    import api
    r = TestClient(api.app).get("/api/day", params={"date": "2024-12-04"})
    assert r.status_code == 200
    j = r.json()
    assert len(j["hours"]) == 13 and j["flag"] is not None
    assert {"forecast", "lo", "hi", "actual", "in_bounds", "nn_updated"} <= set(j["hours"][0]["vars"]["wind"])
