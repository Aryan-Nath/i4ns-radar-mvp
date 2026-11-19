"""Train the MLP on 2023 only. Usage: python scripts/train.py"""
import sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import pandas as pd
import torch
from torch import nn

from i4ns_radar_mvp.data import load_years, VARS
from i4ns_radar_mvp.forecast import climatology, forecast_day, ISSUE_HOUR, LAST_HOUR
from i4ns_radar_mvp.model import Net, make_features, ARTIFACT, LOOK, AHEAD

TRAIN_YEAR = 2023


def build_samples(hourly, clim, mean, std):
    """One sample per (day, origin hour 08..19); skip any with missing data."""
    X, Y, days = [], [], []
    vals = hourly
    for date in pd.date_range(f"{TRAIN_YEAR}-01-01", f"{TRAIN_YEAR}-12-31"):
        fc = forecast_day(hourly, clim, date)
        if fc is None:
            continue
        for h in range(ISSUE_HOUR, LAST_HOUR):
            t = date + pd.Timedelta(hours=h)
            idx = pd.date_range(t - pd.Timedelta(hours=LOOK - 1), t + pd.Timedelta(hours=AHEAD), freq="h")
            if idx[0] < hourly.index[0] or idx[-1] > hourly.index[-1]:
                continue
            w = hourly.loc[idx].values
            if np.isnan(w).any():
                continue
            obs_win, fut = w[:LOOK], w[LOOK:]
            fc_next = fc.loc[t + pd.Timedelta(hours=1): t + pd.Timedelta(hours=AHEAD)].values
            if np.isnan(fc_next).any():
                continue
            X.append(make_features(obs_win, fc_next, t, mean, std))
            Y.append(((fut - obs_win[-1]) / std).ravel().astype(np.float32))
            days.append(date)
    return np.array(X), np.array(Y), np.array(days)


def main():
    torch.manual_seed(0); np.random.seed(0)
    hourly = load_years([TRAIN_YEAR])          # only the training year is loaded
    assert hourly.index.year.max() == TRAIN_YEAR
    clim = climatology(hourly)
    mean, std = hourly.mean().values, hourly.std().values
    X, Y, days = build_samples(hourly, clim, mean, std)
    print(f"{len(X)} training windows from {len(set(days))} days")
    cut = days[int(len(days) * 0.85)]          # last ~15% of the year (chronological) = validation
    tr, va = days < cut, days >= cut
    Xt, Yt, Xv, Yv = map(torch.from_numpy, (X[tr], Y[tr], X[va], Y[va]))
    print(f"train {len(Xt)}  val {len(Xv)} (from {pd.Timestamp(cut).date()})")

    net = Net(); opt = torch.optim.Adam(net.parameters(), lr=1e-3, weight_decay=1e-4)
    loss_fn = nn.MSELoss(); best, best_state, bad = 1e9, None, 0
    t0 = time.time()
    for ep in range(300):
        net.train(); perm = torch.randperm(len(Xt))
        for i in range(0, len(Xt), 64):
            b = perm[i:i + 64]
            opt.zero_grad(); loss_fn(net(Xt[b]), Yt[b]).backward(); opt.step()
        net.eval()
        with torch.no_grad():
            v = loss_fn(net(Xv), Yv).item()
        if v < best - 1e-4:
            best, bad = v, 0
            best_state = {k: x.clone() for k, x in net.state_dict().items()}
        else:
            bad += 1
        if ep % 10 == 0:
            print(f"epoch {ep:3d} val_loss {v:.4f}")
        if bad >= 25:
            break
    print(f"stopped at epoch {ep}, best val loss {best:.4f} "
          f"(zero-change baseline {(Yv ** 2).mean().item():.4f}), {time.time() - t0:.1f}s")
    ARTIFACT.parent.mkdir(exist_ok=True)
    torch.save({"state": best_state, "mean": mean, "std": std}, ARTIFACT)
    print("saved", ARTIFACT)


if __name__ == "__main__":
    main()
