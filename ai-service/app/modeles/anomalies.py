"""
Détection d'anomalies — ensemble de deux modèles.

1. Isolation Forest (scikit-learn) : isole les points rares dans l'espace des caractéristiques.
2. Autoencodeur (PyTorch) : apprend à reconstruire un mouvement « normal » ;
   une grosse erreur de reconstruction signale un mouvement qui ne ressemble à rien de connu.

Le score final est la moyenne des rangs des deux modèles. Chaque alerte est accompagnée
de raisons lisibles calculées sur les données (jamais inventées).
"""
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

from ..texte import dh, date_fr, marchand

try:
    import torch
    from torch import nn
    TORCH = True
except ImportError:  # pragma: no cover
    TORCH = False

COLS = ["log_montant", "z_marchand", "ratio_marchand", "jour_mois", "week_end", "doublon", "sans_categorie", "nouveau"]


def caracteristiques(tx: pd.DataFrame) -> pd.DataFrame:
    d = tx[(tx.montant < 0) & (~tx.inter_structure)].copy()
    d["marchand"] = d.libelle.map(marchand)
    d["abs"] = -d.montant
    d["log_montant"] = np.log1p(d["abs"])
    g = d.groupby(["structure_id", "marchand"])["abs"]
    # statistiques calculées sur l'historique antérieur uniquement (pas de fuite du futur)
    d = d.sort_values("date_op")
    d["med_prec"] = g.transform(lambda s: s.expanding().median().shift(1))
    d["std_prec"] = g.transform(lambda s: s.expanding().std().shift(1))
    d["n_prec"] = g.cumcount()
    d["ratio_marchand"] = (d["abs"] / d["med_prec"]).fillna(1.0).clip(0, 20)
    d["z_marchand"] = ((d["abs"] - d["med_prec"]) / d["std_prec"].replace(0, np.nan)).fillna(0).clip(-10, 10)
    d["jour_mois"] = d.date_op.dt.day / 31
    d["week_end"] = (d.date_op.dt.weekday >= 5).astype(float)
    d["nouveau"] = (d["n_prec"] == 0).astype(float)
    d["sans_categorie"] = d.categorie_id.isna().astype(float)

    d["doublon"] = 0.0
    d["doublon_de"] = None
    for (_, _), grp in d.groupby(["structure_id", "marchand"]):
        grp = grp.sort_values(["date_op", "id"])
        rows = list(grp.itertuples())
        for i in range(1, len(rows)):
            a, b = rows[i - 1], rows[i]
            if a.abs >= 150 and (b.date_op - a.date_op).days <= 3 and abs(a.abs - b.abs) <= 0.02 * a.abs:
                d.loc[b.Index, "doublon"] = 1.0
                d.loc[b.Index, "doublon_de"] = int(a.id)
    return d


if TORCH:
    class _AE(nn.Module):
        def __init__(self, n):
            super().__init__()
            self.enc = nn.Sequential(nn.Linear(n, 16), nn.ReLU(), nn.Linear(16, 3))
            self.dec = nn.Sequential(nn.ReLU(), nn.Linear(3, 16), nn.ReLU(), nn.Linear(16, n))

        def forward(self, x):
            return self.dec(self.enc(x))


class DetecteurAnomalies:
    def __init__(self):
        self.d = None
        self.moteurs = ["Isolation Forest"] + (["Autoencodeur (PyTorch)"] if TORCH else [])

    def entrainer(self, tx: pd.DataFrame):
        d = caracteristiques(tx)
        X = StandardScaler().fit_transform(d[COLS].values)
        iso = IsolationForest(n_estimators=300, contamination=0.03, random_state=7).fit(X)
        s_iso = -iso.score_samples(X)
        rangs = [pd.Series(s_iso).rank(pct=True).values]
        if TORCH:
            torch.manual_seed(7)
            ae = _AE(X.shape[1])
            opt = torch.optim.Adam(ae.parameters(), lr=5e-3)
            Xt = torch.tensor(X, dtype=torch.float32)
            for _ in range(400):
                opt.zero_grad()
                perte = ((ae(Xt) - Xt) ** 2).mean()
                perte.backward()
                opt.step()
            with torch.no_grad():
                err = ((ae(Xt) - Xt) ** 2).mean(dim=1).numpy()
            rangs.append(pd.Series(err).rank(pct=True).values)
        d["score"] = np.mean(rangs, axis=0)
        self.d = d
        return self

    @staticmethod
    def _raisons(r, par_id):
        raisons = []
        if r.doublon:
            o = par_id.get(r.doublon_de)
            raisons.append(f"Même montant chez le même fournisseur le {date_fr(o.date_op)} : doublon probable."
                           if o is not None else "Doublon probable.")
        if r.ratio_marchand >= 1.8 and r.n_prec >= 3:
            raisons.append(f"{r.ratio_marchand:.1f}× le montant habituel ({dh(r.med_prec)}) chez ce fournisseur.")
        if r.nouveau and r["abs"] >= 2000:
            raisons.append("Premier paiement à ce fournisseur, et le montant est élevé.")
        if r.sans_categorie and r["abs"] >= 2000:
            raisons.append("Aucune catégorie, ni justificatif rattaché.")
        if r.week_end and r["abs"] >= 3000:
            raisons.append("Dépense importante un week-end.")
        return raisons

    def lister(self, structure_id=None, depuis=None, limite=8, seuil=0.9):
        d = self.d
        if structure_id:
            d = d[d.structure_id == int(structure_id)]
        if depuis is not None:
            d = d[d.date_op >= pd.Timestamp(depuis)]
        par_id = {int(r.id): r for r in self.d.itertuples()}
        out = []
        for _, r in d.sort_values("score", ascending=False).iterrows():
            raisons = self._raisons(r, par_id)
            if not raisons or (r.score < seuil and not r.doublon):
                continue
            out.append({
                "transaction_id": int(r.id),
                "date": r.date_op.date().isoformat(),
                "libelle": r.libelle,
                "montant": float(r.montant),
                "structure": r.structure,
                "structure_id": int(r.structure_id),
                "score": round(float(r.score), 3),
                "raisons": raisons,
                "type": "doublon" if r.doublon else "montant_inhabituel" if r.ratio_marchand >= 1.8 else "inhabituel",
            })
            if len(out) >= limite:
                break
        return out

