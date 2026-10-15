"""
Saisie en langage naturel (français, darija en lettres latines, un peu d'anglais).

« khlesst 1200 dh l'hébergement dial projet atlas lbare7 »
→ sortie de 1 200 dh, hier, rattachée au projet Atlas, catégorie proposée par le modèle.
"""
import re
from datetime import timedelta
from difflib import SequenceMatcher

from ..texte import sans_accents

MOTS_SORTIE = ["khlest", "khlesst", "khallest", "khalst", "dfe3t", "dfa3t", "chrit", "chriit", "paye", "payé",
               "depense", "dépensé", "achete", "acheté", "paid", "spent", "bought", "sortie", "mchat"]
MOTS_ENTREE = ["tkhlest", "tkhallest", "khlsni", "khalsni", "wslni", "wsalni", "dkhel", "dkhal", "recu", "reçu",
               "encaisse", "encaissé", "received", "got paid", "entree", "rbe7t"]
JOURS = {"lbare7": 1, "lbareh": 1, "hier": 1, "yesterday": 1, "awel lbare7": 2, "avant-hier": 2,
         "lyoum": 0, "aujourd'hui": 0, "today": 0}


def _proche(texte, noms, seuil=0.82):
    """Cherche le nom le plus proche dans le texte (tolère les fautes de frappe)."""
    t = sans_accents(texte.lower())
    meilleur, score = None, 0.0
    for item in noms:
        nom = item[1]
        n = sans_accents(nom.lower())
        mots_nom = [m for m in n.split() if len(m) > 3 and m not in ("projet", "plateforme", "refonte", "maliya")] or n.split()
        for mot in mots_nom:
            for candidat in re.findall(r"[a-z0-9]+", t):
                s = SequenceMatcher(None, mot, candidat).ratio()
                if s > score:
                    meilleur, score = item, s
    return (meilleur, round(score, 2)) if score >= seuil else (None, 0.0)


def analyser(texte: str, categoriseur, structures, projets, clients, ref):
    brut = texte.strip()
    t = sans_accents(brut.lower())
    m = re.search(r"(\d+(?:[ . ]\d{3})*(?:[.,]\d+)?)\s*(k|mille)?\s*(dh|dhs|mad|dirhams?|€|eur|euros?)?", t)
    montant = None
    devise = "MAD"
    if m:
        num = m.group(1)
        if re.fullmatch(r"\d{1,3}([ .\u202f]\d{3})+(,\d+)?", num):  # 1 200 / 1.200 = milliers
            num = re.sub(r"[ .\u202f]", "", num)
        montant = float(num.replace(",", "."))
        if m.group(2):
            montant *= 1000
        if m.group(3) and m.group(3).startswith(("€", "eur")):
            devise = "EUR"

    sens = "SORTIE"
    if any(sans_accents(w) in t for w in MOTS_ENTREE):
        sens = "ENTREE"
    elif any(sans_accents(w) in t for w in MOTS_SORTIE):
        sens = "SORTIE"

    decalage = 0
    for mot, j in sorted(JOURS.items(), key=lambda x: -len(x[0])):
        if sans_accents(mot) in t:
            decalage = j
            break
    date_op = ref - timedelta(days=decalage)

    projet, sp = _proche(brut, projets)
    client, sc = _proche(brut, clients)
    structure = None
    for sid, nom, typ in structures:
        if typ == "PERSO" and re.search(r"\b(perso|personnel|dyali|ldar|maison)\b", t):
            structure = (sid, nom)
        elif typ == "AGENCE" and re.search(r"\bagence\b", t):
            structure = (sid, nom)
        elif typ == "SOCIETE" and re.search(r"\b(societe|sarl|boite)\b", t):
            structure = (sid, nom)
    if structure is None and projet:
        structure = next(((sid, nom) for sid, nom, _ in structures if sid == projet[2]), None)

    signe = 1 if sens == "ENTREE" else -1
    a_retirer = set(sans_accents(w) for w in MOTS_SORTIE + MOTS_ENTREE + list(JOURS))
    a_retirer |= {"dh", "dhs", "mad", "dial", "projet", "pour", "de", "le", "la", "l", "d", "f", "fi", "agence", "societe",
                  "perso", "eur", "euros"}
    for trouve in (projet, client):
        if trouve:
            a_retirer |= set(sans_accents(trouve[1].lower()).split())
    mots = [w for w in re.findall(r"[a-z]+", t) if w not in a_retirer]
    reste = " ".join(mots) or brut
    cat = categoriseur.predire(reste, signe * (montant or 1))
    return {
        "texte": brut,
        "montant": round(signe * montant, 2) if montant else None,
        "devise": devise,
        "sens": sens,
        "date": date_op.isoformat(),
        "projet": {"id": projet[0], "nom": projet[1]} if projet else None,
        "client": {"id": client[0], "nom": client[1]} if client else None,
        "structure": {"id": structure[0], "nom": structure[1]} if structure else None,
        "categorie": cat,
        "manque": [c for c, v in (("montant", montant), ("structure", structure)) if not v],
    }
