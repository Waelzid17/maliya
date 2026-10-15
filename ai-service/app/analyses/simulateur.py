"""
Jumeau financier : projection sur 12 mois, avec et sans tes hypothèses.

Base : la prévision du LSTM pour les mois qu'elle couvre entièrement (≈ 3 mois),
puis le flux net moyen des 12 derniers mois complets.
Chaque scénario ajoute ou retire des flux mois par mois. Les coûts employeur sont des
approximations (charges patronales CNSS/AMO au Maroc ≈ 21 % du brut) à valider avec ton comptable.
"""
import numpy as np
import pandas as pd

from ..db import filtrer
from ..texte import dh, mois_fr

COEF_NET_VERS_COUT = 1.48  # net -> brut (~1.22) puis + charges patronales (~1.21)


def simuler(tx: pd.DataFrame, solde_actuel: float, scenarios: list, structure_id=None, ref=None, horizon=12,
            flux_ia: dict | None = None, fin_ia=None):
    t = filtrer(tx, structure_id)
    ref = pd.Timestamp(ref)
    debut_mois = ref.replace(day=1)
    hist = t[(t.date_op >= debut_mois - pd.DateOffset(months=12)) & (t.date_op < debut_mois)]
    net_mensuel = hist.groupby(hist.date_op.dt.to_period("M")).montant.sum()
    base_flux = float(net_mensuel.mean()) if len(net_mensuel) else 0.0
    h6 = hist[hist.date_op >= debut_mois - pd.DateOffset(months=6)]
    revenus_client = h6[h6.cat_code == "REV_CLIENT"].groupby("client_id").montant.sum() / 6

    mois = [debut_mois + pd.DateOffset(months=i + 1) for i in range(horizon)]
    base = np.full(horizon, base_flux)
    mois_ia = 0
    if flux_ia and fin_ia is not None:
        reste_mois_courant = flux_ia.get(debut_mois.strftime("%Y-%m"), 0.0)
        for i, m in enumerate(mois):
            fin_m = m + pd.offsets.MonthEnd(0)
            if fin_m <= pd.Timestamp(fin_ia) and m.strftime("%Y-%m") in flux_ia:
                base[i] = flux_ia[m.strftime("%Y-%m")] + (reste_mois_courant if i == 0 else 0.0)
                mois_ia = i + 1
            else:
                break
    delta = np.zeros(horizon)
    notes = []

    for s in scenarios:
        typ = s.get("type")
        k0 = max(0, int(s.get("dans_mois", 1)) - 1)
        if typ == "embauche":
            cout = float(s.get("salaire_net", 10000)) * COEF_NET_VERS_COUT
            delta[k0:] -= cout
            notes.append(f"Embauche à {dh(s.get('salaire_net', 10000))} net : environ {dh(cout)} par mois pour l'entreprise.")
        elif typ == "perte_client":
            cid = int(s["client_id"])
            perte = float(revenus_client.get(cid, 0.0))
            delta[k0:] -= perte
            notes.append(f"Perte du client : {dh(perte)} d'encaissements en moins chaque mois (moyenne des 6 derniers mois).")
        elif typ == "nouveau_contrat":
            m = float(s.get("montant_mensuel", 0)) * 1.2
            delta[k0:] += m
            notes.append(f"Nouveau contrat : +{dh(m)} TTC par mois.")
        elif typ == "retard_paiement":
            jours = float(s.get("jours", 30))
            rev = float(revenus_client.sum())
            decale = rev * min(jours, 90) / 30
            delta[k0] -= decale
            if k0 + 3 < horizon:
                delta[k0 + 3] += decale
            notes.append(f"Retards de {jours:.0f} jours : environ {dh(decale)} d'encaissements décalés.")
        elif typ == "depense":
            delta[k0] -= float(s.get("montant", 0))
            notes.append(f"Dépense ponctuelle de {dh(s.get('montant', 0))}.")
        elif typ == "remuneration":
            delta[k0:] -= float(s.get("variation_mensuelle", 0))
            notes.append(f"Ta rémunération change de {dh(s.get('variation_mensuelle', 0), signe=True)} par mois.")

    sol_base = solde_actuel + np.cumsum(base)
    sol_scen = solde_actuel + np.cumsum(base + delta)

    def rupture(serie):
        idx = np.where(serie < 0)[0]
        return mois_fr(mois[idx[0]]) if len(idx) else None

    r_base, r_scen = rupture(sol_base), rupture(sol_scen)
    if not scenarios:
        verdict = (f"Sans rien changer, tu passes sous zéro en {r_base}." if r_base else
                   f"Sans rien changer, tu serais autour de {dh(sol_base[-1])} en {mois_fr(mois[-1])}.")
    elif r_scen and not r_base:
        verdict = f"Avec ces hypothèses, la trésorerie passe sous zéro en {r_scen}."
    elif r_scen:
        verdict = f"La trésorerie passe sous zéro en {r_scen} (contre {r_base} sans ces hypothèses)."
    else:
        verdict = (f"La trésorerie reste positive sur 12 mois : {dh(sol_scen[-1])} en {mois_fr(mois[-1])}, "
                   f"contre {dh(sol_base[-1])} sans ces hypothèses.")
    return {
        "flux_mensuel_base": round(base_flux, 2),
        "mois_prevus_par_lstm": mois_ia,
        "solde_actuel": round(solde_actuel, 2),
        "mois": [m.strftime("%Y-%m") for m in mois],
        "base": [round(float(v), 2) for v in sol_base],
        "scenario": [round(float(v), 2) for v in sol_scen],
        "rupture_base": r_base,
        "rupture_scenario": r_scen,
        "verdict": verdict,
        "notes": notes,
    }
