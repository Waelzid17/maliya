"""
Prévision de trésorerie — deep learning.

Un LSTM (PyTorch) apprend la dynamique des flux nets hebdomadaires de toutes les
structures à la fois (chaque série normalisée à part), puis prévoit 13 semaines
de façon autorégressive. L'incertitude vient du Monte Carlo dropout : on garde
le dropout actif à l'inférence et on tire 200 trajectoires, d'où une fourchette
p10 / p50 / p90 du solde.

Si PyTorch n'est pas installé, un perceptron multicouche scikit-learn prend le relais.
"""
import numpy as np
import pandas as pd

try:
    import torch
    from torch import nn
    TORCH = True
except ImportError:  # pragma: no cover
    TORCH = False

FENETRE = 12


def series_hebdo(tx: pd.DataFrame, structure_ids, fin) -> dict:
    """Flux net par semaine (lundi) pour chaque structure, semaines vides comprises."""
    out = {}
    fin = pd.Timestamp(fin)
    for sid in structure_ids:
        t = tx[tx.structure_id == sid]
        if t.empty:
            continue
        s = t.set_index("date_op").montant.resample("W-MON", label="left", closed="left").sum()
        idx = pd.date_range(s.index.min(), fin - pd.Timedelta(days=fin.weekday()), freq="W-MON")
        s = s.reindex(idx, fill_value=0.0)
        # la semaine en cours est incomplète : on la retire de l'apprentissage
        s = s.iloc[:-1]
        if len(s) >= FENETRE + 6:  # moins de ~4 mois d'historique : pas de prévision honnête possible
            out[sid] = s
    return out


if TORCH:
    class _LSTM(nn.Module):
        def __init__(self, cache=48):
            super().__init__()
            self.lstm = nn.LSTM(input_size=2, hidden_size=cache, num_layers=2, batch_first=True, dropout=0.2)
            self.drop = nn.Dropout(0.25)
            self.tete = nn.Linear(cache, 1)

        def forward(self, x):
            h, _ = self.lstm(x)
            return self.tete(self.drop(h[:, -1, :])).squeeze(-1)


class Prevision:
    def __init__(self):
        self.modele = None
        self.stats = {}
        self.series = {}
        self.moteur = "LSTM (PyTorch)" if TORCH else "MLP (scikit-learn)"
        self.perte_finale = None

    @staticmethod
    def _entrees(valeurs: np.ndarray, debut_semaine: int):
        """Chaque pas = (flux normalisé, position dans le mois) — le mois porte les loyers, salaires, TVA."""
        pos = ((np.arange(len(valeurs)) + debut_semaine) % 52) / 52.0
        return np.stack([valeurs, np.sin(2 * np.pi * pos * 12)], axis=-1)

    def entrainer(self, tx: pd.DataFrame, structure_ids, fin, epoques: int = 220):
        self.series = series_hebdo(tx, structure_ids, fin)
        X, y = [], []
        for sid, s in self.series.items():
            mu, sigma = float(s.mean()), float(s.std() or 1.0)
            self.stats[sid] = (mu, sigma)
            z = (s.values - mu) / sigma
            feats = self._entrees(z, s.index[0].isocalendar().week)
            for i in range(len(z) - FENETRE):
                X.append(feats[i:i + FENETRE])
                y.append(z[i + FENETRE])
        X, y = np.array(X, dtype=np.float32), np.array(y, dtype=np.float32)
        if len(X) == 0:
            self.modele = None
            return self

        if TORCH:
            torch.manual_seed(7)
            self.modele = _LSTM()
            opt = torch.optim.Adam(self.modele.parameters(), lr=3e-3, weight_decay=1e-4)
            Xt, yt = torch.from_numpy(X), torch.from_numpy(y)
            self.modele.train()
            for _ in range(epoques):
                perm = torch.randperm(len(Xt))
                for i in range(0, len(Xt), 64):
                    b = perm[i:i + 64]
                    opt.zero_grad()
                    perte = nn.functional.huber_loss(self.modele(Xt[b]), yt[b])
                    perte.backward()
                    opt.step()
            self.perte_finale = float(perte.detach())
        else:
            from sklearn.neural_network import MLPRegressor
            self.modele = MLPRegressor(hidden_layer_sizes=(64, 32), max_iter=1500, random_state=7)
            self.modele.fit(X.reshape(len(X), -1), y)
        return self

    def _trajectoires(self, sid, semaines, tirages):
        s = self.series[sid]
        mu, sigma = self.stats[sid]
        z = list((s.values - mu) / sigma)
        debut = s.index[0].isocalendar().week
        if TORCH:
            self.modele.train()  # Monte Carlo dropout : le dropout reste actif
            hist = np.tile(np.array(z, dtype=np.float32), (tirages, 1))
            with torch.no_grad():
                for _ in range(semaines):
                    fen = hist[:, -FENETRE:]
                    pos0 = debut + hist.shape[1] - FENETRE
                    feats = np.stack([self._entrees(f, pos0) for f in fen]).astype(np.float32)
                    nxt = self.modele(torch.from_numpy(feats)).numpy()
                    hist = np.concatenate([hist, nxt[:, None]], axis=1)
            futur = hist[:, len(z):]
        else:
            rng = np.random.default_rng(7)
            hist = list(z)
            futur1 = []
            for _ in range(semaines):
                fen = self._entrees(np.array(hist[-FENETRE:]), debut + len(hist) - FENETRE)
                v = float(self.modele.predict(fen.reshape(1, -1))[0])
                hist.append(v)
                futur1.append(v)
            resid = np.std(z) * 0.35
            futur = np.array(futur1)[None, :] + rng.normal(0, resid, (tirages, semaines))
        return futur * sigma + mu

    def prevoir(self, structure_ids, soldes: dict, semaines: int = 13, tirages: int = 200):
        ids = [s for s in structure_ids if s in self.series]
        if not ids or self.modele is None:
            raise ValueError("Pas encore assez d'historique pour prévoir cette structure.")
        total = np.zeros((tirages, semaines))
        solde0 = 0.0
        for sid in ids:
            total += self._trajectoires(sid, semaines, tirages)
        solde0 = float(sum(soldes.get(sid, 0.0) for sid in structure_ids))
        cumul = solde0 + np.cumsum(total, axis=1)
        derniere = max(self.series[s].index[-1] for s in ids)
        dates = [derniere + pd.Timedelta(weeks=i + 1) for i in range(semaines)]
        p10, p50, p90 = np.percentile(cumul, [10, 50, 90], axis=0)
        hist = sum(self.series[s] for s in ids).iloc[-26:]
        return {
            "moteur": self.moteur,
            "solde_actuel": round(solde0, 2),
            "historique_flux": [{"semaine": d.date().isoformat(), "flux": round(float(v), 2)} for d, v in hist.items()],
            "prevision": [
                {"semaine": d.date().isoformat(), "p10": round(float(a), 2), "p50": round(float(b), 2), "p90": round(float(c), 2)}
                for d, a, b, c in zip(dates, p10, p50, p90)
            ],
            "proba_solde_negatif": round(float((cumul.min(axis=1) < 0).mean()), 3),
        }
