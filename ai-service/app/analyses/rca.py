"""
Analyse des causes (RCA) : « pourquoi mon flux de trésorerie a changé ? »

On compare deux mois, on décompose l'écart par catégorie, puis on descend d'un niveau
(client pour les revenus, fournisseur pour les dépenses) pour trouver le mouvement précis.
Chaque cause renvoie aux mouvements et factures qui la prouvent.
"""
import pandas as pd

from ..db import filtrer
from ..texte import dh, date_fr, joli_libelle, marchand, mois_fr


def _bornes(mois, ref):
    """Mois passé : mois complet contre le mois d'avant.
    Mois en cours : du 1er à aujourd'hui, contre la même période du mois précédent (comparaison à armes égales)."""
    ref = pd.Timestamp(ref)
    debut = pd.Timestamp(f"{mois}-01") if mois else ref.replace(day=1)
    prec = debut - pd.offsets.MonthBegin(1)
    if debut == ref.replace(day=1):
        jours = ref.day
        return prec, prec + pd.Timedelta(days=jours), debut, ref + pd.Timedelta(days=1), True
    return prec, debut, debut, debut + pd.offsets.MonthBegin(1), False


def expliquer(tx: pd.DataFrame, ouvertes: list, structure_id=None, mois=None, ref=None, clients=None):
    clients = clients or {}
    t = filtrer(tx, structure_id).copy()
    t["cat"] = t.cat_libelle.fillna("Non catégorisé")
    prec, fin_prec, debut, fin, en_cours = _bornes(mois, ref)
    a = t[(t.date_op >= debut) & (t.date_op < fin)]
    b = t[(t.date_op >= prec) & (t.date_op < fin_prec)]
    histo = t[(t.date_op >= debut - pd.DateOffset(months=6)) & (t.date_op < debut)]

    net_a, net_b = a.montant.sum(), b.montant.sum()
    ecart = net_a - net_b
    par_cat = pd.concat([a.groupby("cat").montant.sum().rename("actuel"),
                         b.groupby("cat").montant.sum().rename("precedent")], axis=1).fillna(0)
    par_cat["ecart"] = par_cat.actuel - par_cat.precedent
    par_cat = par_cat.sort_values("ecart")

    causes, compensations = [], []
    negatif_total = par_cat.ecart[par_cat.ecart < 0].sum() or -1
    cumul = 0.0
    for cat, r in par_cat.iterrows():
        if r.ecart >= -300 or len(causes) >= 4:
            break
        cumul += r.ecart
        cause = {"categorie": cat, "impact": round(float(r.ecart), 2), "preuves": []}
        if r.actuel >= 0 and r.precedent > 0:  # une entrée qui a baissé
            ca = a[a.cat == cat].groupby("client_id").montant.sum()
            cb = b[b.cat == cat].groupby("client_id").montant.sum()
            diff = (ca.reindex(cb.index.union(ca.index), fill_value=0)
                    - cb.reindex(cb.index.union(ca.index), fill_value=0)).sort_values()
            noms = []
            for cid, v in diff.items():
                if v >= -500 or pd.isna(cid):
                    continue
                nom = clients.get(int(cid), f"client #{int(cid)}")
                a_venir = [f for f in ouvertes if f["client_id"] == int(cid) and f["jours_depasses"] <= 0]
                phrase = f"{nom} a versé {dh(-v)} de moins"
                if a_venir:
                    phrase += f" (sa prochaine facture n'est due que le {date_fr(pd.Timestamp(a_venir[0]['echeance']))})"
                noms.append(phrase)
            echues = [f for f in ouvertes if f["jours_depasses"] > 0
                      and (not structure_id or f["structure_id"] == int(structure_id))]
            for f in sorted(echues, key=lambda x: -x["montant_ttc"])[:2]:
                noms.insert(0, f"{f['client']} n'a toujours pas réglé {f['numero']} ({dh(f['montant_ttc'])}), "
                               f"échue depuis {f['jours_depasses']} jours")
                cause["preuves"].append({"type": "facture", "id": f["facture_id"], "libelle": f"{f['numero']} — {f['client']}",
                                         "montant": f["montant_ttc"], "date": f["echeance"]})
            cause["titre"] = f"{cat} en baisse de {dh(-r.ecart)}"
            cause["explication"] = (_phrase("; ".join(noms[:3]))) if noms else \
                f"Moins d'encaissements que le mois précédent ({dh(r.actuel)} contre {dh(r.precedent)})."
        else:  # une dépense qui a augmenté
            da = a[a.cat == cat].copy()
            da["m"] = da.libelle.map(marchand)
            hm = histo[histo.cat == cat].copy()
            hm["m"] = hm.libelle.map(marchand)
            habituel = hm.groupby([hm.m, hm.date_op.dt.to_period("M")]).montant.sum().groupby(level=0).median()
            lignes = []
            for m, g in da.groupby("m"):
                tot = g.montant.sum()
                hab = habituel.get(m, 0.0)
                if tot < hab - 300 or (hab == 0 and tot < -300):
                    lignes.append((tot - hab, m, g, hab))
            lignes.sort(key=lambda x: x[0])
            phrases = []
            for surcout, m, g, hab in lignes[:2]:
                ex = g.sort_values("montant").iloc[0]
                if hab:
                    phrases.append(f"{joli_libelle(ex.libelle)} : {dh(-g.montant.sum())} contre {dh(-hab)} d'habitude")
                else:
                    phrases.append(f"nouvelle dépense {joli_libelle(ex.libelle)} ({dh(-g.montant.sum())})")
                cause["preuves"] += [{"type": "transaction", "id": int(x.id), "libelle": x.libelle,
                                      "montant": float(x.montant), "date": x.date_op.date().isoformat()}
                                     for x in g.itertuples()]
            cause["titre"] = f"{cat} : {dh(-r.ecart)} de plus"
            cause["explication"] = _phrase("; ".join(phrases)) if phrases else \
                f"{dh(-r.actuel)} ce mois-ci contre {dh(-r.precedent)} le mois d'avant."
        causes.append(cause)
        if cumul / negatif_total >= 0.85:
            break

    for cat, r in par_cat.sort_values("ecart", ascending=False).iterrows():
        if r.ecart <= 500 or len(compensations) >= 2:
            break
        compensations.append({"categorie": cat, "impact": round(float(r.ecart), 2),
                              "titre": f"{cat} : {dh(r.ecart, signe=True)}"})

    lib_a = f"du 1er au {pd.Timestamp(ref).day} {mois_fr(debut)}" if en_cours else f"en {mois_fr(debut)}"
    lib_b = f"sur la même période de {mois_fr(prec).split()[0]}" if en_cours else f"en {mois_fr(prec)}"
    que_b = f"que {lib_b}" if en_cours else f"qu'{lib_b}"
    part = min(100, round(100 * sum(c["impact"] for c in causes) / negatif_total)) if causes else 0
    if ecart < 0:
        resume = (f"{lib_a.capitalize()}, le flux net est de {dh(net_a)}, soit {dh(-ecart)} de moins {que_b}. "
                  f"{len(causes)} cause{'s' if len(causes) > 1 else ''} expliqu{'ent' if len(causes) > 1 else 'e'} {part} % de la baisse.")
    else:
        resume = (f"{lib_a.capitalize()}, le flux net est de {dh(net_a)}, soit {dh(ecart)} de mieux {que_b}.")
    return {
        "periode": {"mois": debut.strftime("%Y-%m"), "libelle": lib_a, "compare_a": lib_b, "en_cours": en_cours},
        "net_actuel": round(float(net_a), 2),
        "net_precedent": round(float(net_b), 2),
        "ecart": round(float(ecart), 2),
        "resume": resume,
        "causes": causes,
        "compensations": compensations,
    }


def _phrase(s: str) -> str:
    s = s[0].upper() + s[1:]
    return s if s.endswith(".") else s + "."
