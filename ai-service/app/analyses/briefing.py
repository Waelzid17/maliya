"""Le mot du jour : quelques notes courtes, triées par importance, écrites à partir des modèles."""
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd

from ..texte import dh, date_fr, joli_libelle, mois_fr
from .rca import expliquer

ORDRE = {"URGENT": 0, "ATTENTION": 1, "INFO": 2}


def salutation(prenom="Wael"):
    h = datetime.now(ZoneInfo("Africa/Casablanca")).hour
    if h < 5:
        return f"Encore debout, {prenom} ?"
    if h < 12:
        return f"Bonjour {prenom},"
    if h < 18:
        return f"Bon après-midi {prenom},"
    return f"Bonsoir {prenom},"


def construire(c, structure_id=None):
    notes = []
    ids = [structure_id] if structure_id else list(c.structures.id)
    try:
        f = c.prevision.prevoir(ids, c.soldes)
    except ValueError:
        f = None
    if f:
        fin = f["prevision"][-1]
        risque = f["proba_solde_negatif"]
        notes.append({
            "genre": "tresorerie",
            "titre": f"Tu as {dh(f['solde_actuel'])} en banque.",
            "texte": (f"Au rythme actuel, ce sera plutôt {dh(fin['p50'])} vers le {date_fr(pd.Timestamp(fin['semaine']))}"
                      f" (fourchette {dh(fin['p10'])} à {dh(fin['p90'])})."
                      + (f" Attention : {risque * 100:.0f} % de risque de passer sous zéro d'ici là." if risque > 0.05 else "")),
            "gravite": "URGENT" if risque > 0.25 else "ATTENTION" if risque > 0.05 else "INFO",
            "action": {"label": "Voir la prévision", "route": "/scenarios"},
        })

    ouv = [x for x in c.factures_ouvertes if x["jours_depasses"] > 0 and (not structure_id or x["structure_id"] == structure_id)]
    if ouv:
        total = sum(x["montant_ttc"] for x in ouv)
        pire = max(ouv, key=lambda x: x["montant_ttc"])
        notes.append({
            "genre": "retards",
            "titre": f"On te doit {dh(total)} en factures échues.",
            "texte": (f"Le plus gros morceau : {pire['client']}, {dh(pire['montant_ttc'])} ({pire['numero']}), "
                      f"échue depuis {pire['jours_depasses']} jours. {pire['raison']} J'ai préparé une relance."),
            "gravite": "URGENT" if total > 50000 else "ATTENTION",
            "action": {"label": "Relire la relance", "route": "/factures"},
        })

    anom = c.anomalies.lister(structure_id, depuis=pd.Timestamp(c.ref) - pd.Timedelta(days=21), limite=3)
    if anom:
        a = anom[0]
        autres = (f" Il y a {len(anom) - 1} autre{'s' if len(anom) > 2 else ''} mouvement{'s' if len(anom) > 2 else ''} à vérifier."
                  if len(anom) > 1 else "")
        notes.append({
            "genre": "anomalie",
            "titre": f"{joli_libelle(a['libelle'])}, {dh(-a['montant'])} le {date_fr(pd.Timestamp(a['date']))}",
            "texte": " ".join(a["raisons"]) + autres,
            "gravite": "ATTENTION",
            "action": {"label": "Examiner", "route": "/signaux"},
        })

    for p in c.projets_etat():
        if structure_id and p["structure_id"] != structure_id:
            continue
        if p["statut"] == "EN_COURS" and p["consommation"] >= 90:
            depasse = p["cout_reel"] > p["budget"]
            notes.append({
                "genre": "projet",
                "titre": (f"{p['nom']} a dépassé son budget." if depasse
                          else f"{p['nom']} a consommé {p['consommation']:.0f} % de son budget."),
                "texte": (f"{dh(p['cout_reel'])} dépensés sur {dh(p['budget'])} prévus, à un rythme de "
                          f"{dh(p['rythme_mensuel'])} par mois."
                          + (f" Au rythme actuel, le budget sera épuisé vers le {date_fr(pd.Timestamp(p['budget_epuise_vers']))}"
                             if p["budget_epuise_vers"] else "")
                          + (" Il faudra sans doute refacturer le hors-périmètre." if p["marge_pct"] < 30 else "")).rstrip(".") + ".",
                "gravite": "ATTENTION",
                "action": {"label": "Ouvrir le projet", "route": "/projets"},
            })
            break

    nc = c.tx[c.tx.categorie_id.isna()]
    if structure_id:
        nc = nc[nc.structure_id == structure_id]
    if len(nc):
        notes.append({
            "genre": "categorisation",
            "titre": f"{len(nc)} mouvement{'s' if len(nc) > 1 else ''} sans catégorie.",
            "texte": "J'ai une proposition pour chacun. Il te suffit de valider ou de corriger.",
            "gravite": "INFO",
            "action": {"label": "Valider les catégories", "route": "/mouvements?a_classer=1"},
        })

    r = expliquer(c.tx, c.factures_ouvertes, structure_id, None, c.ref, c.noms_clients)
    if r["causes"] and r["ecart"] < 0:
        notes.append({
            "genre": "rca",
            "titre": "Ce mois-ci est plus serré que le précédent." if r["periode"]["en_cours"]
                     else f"{mois_fr(pd.Timestamp(r['periode']['mois'] + '-01')).capitalize()} a été plus serré.",
            "texte": r["resume"] + " " + r["causes"][0]["explication"],
            "gravite": "INFO",
            "action": {"label": "Comprendre pourquoi", "route": "/signaux"},
        })

    notes.sort(key=lambda n: ORDRE[n["gravite"]])
    for i, n in enumerate(notes):
        n["id"] = i + 1
    return {"salutation": salutation(), "notes": notes, "genere_le": datetime.now().isoformat(timespec="seconds")}
