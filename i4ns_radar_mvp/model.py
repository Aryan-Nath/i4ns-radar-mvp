"""Small MLP that updates the forecast from recent observations.

Input  (64): last 6 hours of observations (5 vars, normalised) = 30
             + hour-of-day sin/cos + day-of-year sin/cos = 4
             + original forecast minus current obs, next 6 hours (normalised) = 30
Output (30): next 1..6 hours x 5 vars, as change from the current observation
             (in units of each variable's std).
"""
import numpy as np
import torch
from torch import nn

from .data import VARS, ROOT

ARTIFACT = ROOT / "artifacts" / "radar_mlp.pt"
LOOK, AHEAD, NV = 6, 6, len(VARS)


class Net(nn.Module):
    def __init__(self, n_in=LOOK * NV + 4 + AHEAD * NV, n_out=AHEAD * NV, hidden=128):
        super().__init__()
        self.net = nn.Sequential(nn.Linear(n_in, hidden), nn.ReLU(), nn.Dropout(0.1),
                                 nn.Linear(hidden, hidden), nn.ReLU(), nn.Linear(hidden, n_out))

    def forward(self, x):
        return self.net(x)


def make_features(obs_win, fc_next, t, mean, std):
    """obs_win (6,5) hours t-5..t; fc_next (6,5) hours t+1..t+6; t = origin Timestamp."""
    cur = obs_win[-1]
    h = 2 * np.pi * t.hour / 24
    d = 2 * np.pi * t.day_of_year / 365.25
    return np.concatenate([((obs_win - mean) / std).ravel(),
                           [np.sin(h), np.cos(h), np.sin(d), np.cos(d)],
                           ((fc_next - cur) / std).ravel()]).astype(np.float32)


class Predictor:
    """Wraps the trained net + normalisation stats."""

    def __init__(self, path=ARTIFACT):
        ck = torch.load(path, weights_only=False)
        self.mean, self.std = ck["mean"], ck["std"]
        self.net = Net()
        self.net.load_state_dict(ck["state"])
        self.net.eval()

    def predict(self, obs_win, fc_next, t):
        """Return (6,5) predicted values for hours t+1..t+6."""
        x = torch.from_numpy(make_features(obs_win, fc_next, t, self.mean, self.std))[None]
        with torch.no_grad():
            delta = self.net(x)[0].numpy().reshape(AHEAD, NV)
        return obs_win[-1] + delta * self.std
