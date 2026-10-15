"""
Prédiction des retards de paiement — gradient boosting.

Pour chaque facture déjà payée, on connaît le retard réel (date de paiement − échéance).
On apprend ce retard à partir du passé du client au moment de la facture
(retard moyen, dernier retard, tendance), du montant et de l'ancienneté de la relation.
Trois modèles : médiane, quantile 20 % et quantile 80 %, pour donner une fourchette.
"""
from datetime import timedelta

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor

from ..texte import dh, date_fr

FEATS = ["retard_moyen", "dernier_retard", "tendance", "nb_prec", "log_ttc", "anciennete"]


def _historique(f: pd.DataFrame, ref) -> pd.DataFrame:
    f = f.sort_values("date_emission").copy()
    ref = pd.Timestamp(ref)
    f["retard"] = np.where(f.date_paiement.notna(),
                           (f.date_paiement - f.date_echeance).dt.days, np.nan)
    rows = []
    for cid, g in f.groupby("client_id"):
        passes = []  # (date_paiement, retard) des factures déjà réglées
        premiere = g.date_emission.min()
        for r in g.itertuples():
            connus = [x for d, x in passes if d <= r.date_emission]
            rows.append({
                "id": r.id,
                "retard_moyen": np.mean(connus) if connus else np.nan,
                "dernier_retard": connus[-1] if connus else np.nan,
                "tendance": (np.mean(connus[-3:]) - np.mean(connus[:3])) if len(connus) >= 4 else 0.0,
                "nb_prec": len(connus),
                "log_ttc": np.log1p(r.montant_ttc),
                "anciennete": (r.date_emission - premiere).days / 30,
            })
            if not np.isnan(r.retard):
                passes.append((r.date_paiement, r.retard))
                passes.sort()
    h = pd.DataFrame(rows)
    out = f.merge(h, on="id")
    moy = out.retard.mean()
    out["retard_moyen"] = out.retard_moyen.fillna(moy)
    out["dernier_retard"] = out.dernier_retard.fillna(moy)
    out["jours_depasses"] = np.where(out.date_paiement.isna(), (ref - out.date_echeance).dt.days, np.nan)
    return out


class RisquePaiement:
    def __init__(self):
        self.modeles = {}
        self.h = None
        self.mae = None

    def entrainer(self, factures: pd.DataFrame, ref):
        self.ref = pd.Timestamp(ref)
        self.h = _historique(factures, ref)
        app = self.h.dropna(subset=["retard"])
        X, y = app[FEATS].values, app.retard.values
        for nom, kw in {"p50": dict(loss="absolute_error"),
                        "p20": dict(loss="quantile", alpha=0.2),
                        "p80": dict(loss="quantile", alpha=0.8)}.items():
            self.modeles[nom] = GradientBoostingRegressor(n_estimators=250, max_depth=2, learning_rate=0.05,
                                                          subsample=0.8, random_state=7, **kw).fit(X, y)
        self.mae = float(np.mean(np.abs(self.modeles["p50"].predict(X) - y)))
        return self

    def factures_ouvertes(self, structure_id=None):
        o = self.h[self.h.date_paiement.isna()].copy()
        if structure_id:
            o = o[o.structure_id == int(structure_id)]
        if o.empty:
            return []
        X = o[FEATS].values
        res = []
        for (_, r), p20, p50, p80 in zip(o.iterrows(), self.modeles["p20"].predict(X),
                                          self.modeles["p50"].predict(X), self.modeles["p80"].predict(X)):
            retard = max(float(p50), float(r.jours_depasses or 0))
            date_prob = r.date_echeance + timedelta(days=round(retard))
            if date_prob < self.ref:
                date_prob = self.ref + timedelta(days=7)
            niveau = "élevé" if retard > 30 else "moyen" if retard > 10 else "faible"
            if niveau == "élevé":
                raison = f"{r.client} paie en moyenne {r.retard_moyen:.0f} jours après l'échéance"
                if r.tendance > 5:
                    raison += f", et ce retard s'allonge (+{r.tendance:.0f} j sur ses dernières factures)"
                raison += "."
            elif niveau == "moyen":
                raison = f"Retard habituel de {r.retard_moyen:.0f} jours pour ce client."
            else:
                raison = "Client ponctuel jusqu'ici."
            res.append({
                "facture_id": int(r.id),
                "numero": r.numero,
                "client": r.client,
                "client_id": int(r.client_id),
                "structure_id": int(r.structure_id),
                "montant_ttc": float(r.montant_ttc),
                "echeance": r.date_echeance.date().isoformat(),
                "jours_depasses": int(r.jours_depasses),
                "retard_prevu": round(retard),
                "fourchette": [round(min(float(p20), retard)), round(max(float(p80), retard))],
                "date_paiement_probable": date_prob.date().isoformat(),
                "risque": niveau,
                "raison": raison,
            })
        return sorted(res, key=lambda x: -x["retard_prevu"])

    def profil_clients(self):
        p = self.h.dropna(subset=["retard"]).groupby(["client_id", "client"]).agg(
            retard_moyen=("retard", "mean"), factures=("id", "count")).reset_index()
        return [{"client_id": int(r.client_id), "client": r.client, "retard_moyen": round(float(r.retard_moyen), 1),
                 "factures_payees": int(r.factures)} for r in p.itertuples()]

    def phrase(self, f):
        return (f"{f['numero']} ({dh(f['montant_ttc'])}, {f['client']}) : paiement attendu vers le "
                f"{date_fr(pd.Timestamp(f['date_paiement_probable']))}.")
