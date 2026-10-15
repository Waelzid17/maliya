"""
Copilote : comprend la question, va chercher les chiffres, répond.

1. Un classifieur d'intention (TF-IDF mots + caractères, régression logistique) entraîné
   sur des exemples en français, darija et anglais.
2. Extraction des entités : structure, mois, catégorie, client, projet.
3. Un « outil » par intention qui interroge le grand livre et rédige la réponse.
4. Optionnel : un LLM local reformule sans toucher aux chiffres.
"""
import re

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import FeatureUnion, make_pipeline

from ..analyses.rca import expliquer
from ..db import filtrer
from ..texte import MOIS, dh, date_fr, joli_libelle, mois_fr, sans_accents
from . import llm

EXEMPLES = {
    "solde": ["combien j'ai en banque", "quel est mon solde", "ma tréso aujourd'hui", "combien d'argent j'ai",
              "chhal 3andi f lbanka", "chhal fih l compte", "how much cash do i have", "solde de l'agence",
              "trésorerie totale", "il me reste combien", "état de mes comptes", "balance"],
    "depenses": ["combien j'ai dépensé", "mes dépenses du mois", "chhal khlest had chher", "dépenses en cloud",
                 "combien en restaurants", "où part mon argent", "top des dépenses", "combien coûte aws",
                 "dépenses de septembre", "what did i spend", "mes plus grosses dépenses", "frais de logiciels"],
    "revenus": ["combien j'ai encaissé", "chiffre d'affaires", "revenus du mois", "chhal dkhel", "ventes",
                "combien m'a payé", "encaissements de septembre", "how much revenue", "rentrées d'argent"],
    "pourquoi": ["pourquoi ma tréso a baissé", "explique la baisse", "pourquoi j'ai moins d'argent",
                 "3lach nqest lflous", "why did cash drop", "qu'est-ce qui s'est passé ce mois",
                 "d'où vient la baisse", "pourquoi le flux est négatif", "analyse les causes", "pourquoi"],
    "retards": ["qui me doit de l'argent", "factures en retard", "impayés", "chkoun ma khlsnich",
                "factures non payées", "clients en retard", "who owes me", "relances à faire", "créances"],
    "projets": ["rentabilité des projets", "le projet est rentable", "marge du projet", "budget dépassé",
                "quel projet perd de l'argent", "coût réel du projet", "projects profitability", "état des projets"],
    "prevision": ["prévision de trésorerie", "combien j'aurai dans 3 mois", "runway", "vais-je manquer d'argent",
                  "projection", "forecast", "chhal ghadi ykoun 3andi", "trésorerie future", "prochaines semaines"],
    "anomalies": ["quelque chose d'anormal", "anomalies", "doublons", "dépenses bizarres", "fraude",
                  "transactions suspectes", "chi haja ghriba", "anything weird", "erreurs de prélèvement"],
    "client": ["parle moi du client", "comment paie ce client", "profil client", "historique avec le client",
               "le client est fiable", "tell me about client", "parle moi de", "dis moi tout sur", "et lui il paie bien",
               "qu'est-ce que tu sais sur"],
    "remuneration": ["combien je peux me verser", "salaire dirigeant", "me payer plus", "ma rémunération",
                     "chhal nkhles rasi", "dividendes ou salaire", "how much can i pay myself"],
    "aide": ["que peux-tu faire", "aide", "bonjour", "salam", "help", "comment ça marche", "salut", "hello"],
}

CAT_MOTS = {
    "CLOUD": ["cloud", "aws", "hebergement", "serveur", "ovh", "hetzner"], "REPAS": ["resto", "restaurant", "cafe", "repas", "makla"],
    "SALAIRES": ["salaire", "paie"], "FREELANCE": ["freelance", "prestataire"], "LOGICIELS": ["logiciel", "abonnement", "saas", "outil"],
    "MARKETING": ["marketing", "pub", "publicite", "ads"], "LOYER": ["loyer", "bureau", "lkra"],
    "DEPLACEMENT": ["deplacement", "voyage", "transport", "train", "essence"], "IMPOTS": ["impot", "tva", "dgi"],
    "CNSS": ["cnss", "charges sociales"], "COURSES": ["courses", "marjane", "supermarche"], "LOISIRS": ["loisir", "sortie"],
    "TELECOM": ["telecom", "telephone", "internet", "fibre"],
}

MOTS_GENERIQUES = {"projet", "plateforme", "refonte", "cloud", "conseil", "mobile", "boutique", "ligne", "integration",
                   "site", "maintenance", "logistique", "shop", "hotels"}

AIDE = [
    "Combien j'ai en banque ?", "Pourquoi ma tréso a baissé en septembre ?", "Qui me doit de l'argent ?",
    "Combien j'ai dépensé en cloud ce mois-ci ?", "Quel projet perd de l'argent ?",
    "Combien je peux me verser ?", "Prévision sur 3 mois pour l'agence",
]


REGLES = [  # mots très sûrs : priment sur le classifieur
    ("anomalies", r"doublon|anomal|suspect|bizarre|fraude|ghrib"),
    ("pourquoi", r"\bpourquoi\b|\b3lach\b|\bwhy\b|\bexplique"),
    ("prevision", r"previs|projection|forecast|runway|dans \d+ (mois|semaines)|futur"),
    ("retards", r"retard|impaye|me doit|owes me|relance|ma khlsnich"),
    ("remuneration", r"me verser|me payer|ma remuneration|dividende|nkhles rasi"),
]

HORS_SUJET = ("Je ne réponds qu'aux questions sur tes finances : comptes, dépenses, factures, projets, prévisions. "
              "Essaie par exemple :")


def _point(s: str) -> str:
    return s if s.endswith(".") else s + "."


class Copilote:
    def __init__(self, cerveau):
        self.c = cerveau
        X, y = [], []
        for intent, ex in EXEMPLES.items():
            X += [sans_accents(e.lower()) for e in ex]
            y += [intent] * len(ex)
        self.clf = make_pipeline(
            FeatureUnion([("mots", TfidfVectorizer(ngram_range=(1, 2))),
                          ("car", TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 4)))]),
            LogisticRegression(max_iter=3000, C=12),
        ).fit(X, y)

    # ---------- compréhension ----------
    def intention(self, q):
        t = sans_accents(q.lower())
        for intent, motif in REGLES:
            if re.search(motif, t):
                return intent, 1.0
        p = self.clf.predict_proba([t])[0]
        i = int(np.argmax(p))
        return self.clf.classes_[i], float(p[i])

    def entites(self, q, structure_par_defaut=None):
        t = sans_accents(q.lower())
        e = {"structure_id": structure_par_defaut, "mois": None, "categorie": None, "client": None, "projet": None}
        if re.search(r"\bagence\b|zidane digital", t):
            e["structure_id"] = 1
        elif re.search(r"\bsociete\b|\bsarl\b|maliya sarl", t):
            e["structure_id"] = 2
        elif "projet atlas" in t:
            e["structure_id"] = 3
        elif re.search(r"\bperso\b|personnel|dyali", t):
            e["structure_id"] = 4
        elif re.search(r"\b(tout|toutes|global|consolide|total)\b", t):
            e["structure_id"] = None
        ref = self.c.ref
        for i, m in enumerate(MOIS):
            if sans_accents(m) in t:
                annee = ref.year if i + 1 <= ref.month else ref.year - 1
                e["mois"] = f"{annee}-{i + 1:02d}"
        if re.search(r"mois dernier|mois precedent|last month|chher li fat", t):
            p = (pd.Timestamp(ref).replace(day=1) - pd.offsets.MonthBegin(1))
            e["mois"] = p.strftime("%Y-%m")
        elif re.search(r"ce mois|had chher|this month", t):
            e["mois"] = pd.Timestamp(ref).strftime("%Y-%m")
        for code, mots in CAT_MOTS.items():
            if any(re.search(rf"\b{m}", t) for m in mots):
                e["categorie"] = code
                break
        for r in self.c.clients.itertuples():
            premier = sans_accents(r.nom.lower()).split()[0]
            if len(premier) > 3 and re.search(rf"\b{premier}", t):
                e["client"] = (int(r.id), r.nom)
        for r in self.c.projets.itertuples():
            mots = [w for w in sans_accents(r.nom.lower()).split() if len(w) > 3 and w not in MOTS_GENERIQUES]
            if any(re.search(rf"\b{w}\b", t) for w in mots):
                e["projet"] = (int(r.id), r.nom)
        return e

    # ---------- outils ----------
    def _nom_structure(self, sid):
        if not sid:
            return "toutes tes structures"
        return self.c.structures.set_index("id").nom.get(sid, "cette structure")

    def _periode(self, mois):
        if mois:
            d = pd.Timestamp(f"{mois}-01")
        else:
            d = pd.Timestamp(self.c.ref).replace(day=1)
        return d, d + pd.offsets.MonthBegin(1)

    def solde(self, e, q):
        s = self.c.structures
        if e["structure_id"]:
            r = s[s.id == e["structure_id"]].iloc[0]
            texte = f"{r.nom} a {dh(r.solde)} en banque aujourd'hui."
            return {"reponse": texte, "faits": {"structure": r.nom, "solde": r.solde}}
        lignes = [f"{r.nom} : {dh(r.solde)}" for r in s.itertuples()]
        total = s.solde.sum()
        return {"reponse": f"Tu as {dh(total)} au total, réparti comme ceci :", "points": lignes,
                "graphique": {"type": "barres", "donnees": [{"label": r.nom, "valeur": round(r.solde)} for r in s.itertuples()]},
                "faits": {"total": total, "par_structure": dict(zip(s.nom, s.solde))}}

    def depenses(self, e, q):
        d0, d1 = self._periode(e["mois"])
        t = filtrer(self.c.tx, e["structure_id"])
        t = t[(t.date_op >= d0) & (t.date_op < d1) & (t.montant < 0) & (t.cat_code != "TRANSFERT")]
        qui = self._nom_structure(e["structure_id"])
        verbe = "tu as dépensé" if not e["structure_id"] else f"{qui} a dépensé"
        if e["categorie"]:
            t = t[t.cat_code == e["categorie"]]
            lib = self.c.categories.set_index("code").libelle[e["categorie"]]
            if t.empty:
                return {"reponse": f"Aucune dépense « {lib} » en {mois_fr(d0)} pour {qui}.", "faits": {}}
            tops = t.sort_values("montant").head(5)
            return {"reponse": f"En {mois_fr(d0)}, {verbe} {dh(-t.montant.sum())} en {lib.lower()}.",
                    "points": [f"{date_fr(r.date_op)} — {joli_libelle(r.libelle)} : {dh(-r.montant)}" for r in tops.itertuples()],
                    "sources": [int(i) for i in tops.id], "faits": {"total": -t.montant.sum(), "categorie": lib}}
        par = t.assign(cat=t.cat_libelle.fillna("Non catégorisé")).groupby("cat").montant.sum().sort_values().head(6)
        return {"reponse": f"En {mois_fr(d0)}, {verbe} {dh(-t.montant.sum())}. Les plus gros postes :",
                "points": [f"{c} : {dh(-v)}" for c, v in par.items()],
                "graphique": {"type": "barres", "donnees": [{"label": c, "valeur": round(-v)} for c, v in par.items()]},
                "faits": {"total": -t.montant.sum(), "postes": (-par).round().to_dict()}}

    def revenus(self, e, q):
        d0, d1 = self._periode(e["mois"])
        t = filtrer(self.c.tx, e["structure_id"])
        t = t[(t.date_op >= d0) & (t.date_op < d1) & (t.cat_code == "REV_CLIENT")]
        noms = self.c.clients.set_index("id").nom
        par = t.groupby("client_id").montant.sum().sort_values(ascending=False)
        pts = [f"{noms.get(int(c), '?')} : {dh(v)}" for c, v in par.items()]
        verbe = "tu as encaissé" if not e["structure_id"] else f"{self._nom_structure(e['structure_id'])} a encaissé"
        return {"reponse": f"En {mois_fr(d0)}, {verbe} {dh(t.montant.sum())}"
                           + (" :" if pts else "."), "points": pts, "faits": {"total": t.montant.sum()}}

    def pourquoi(self, e, q):
        r = expliquer(self.c.tx, self.c.factures_ouvertes, e["structure_id"], e["mois"], self.c.ref, self.c.noms_clients)
        pts = [f"{c['titre']}. {c['explication']}" for c in r["causes"]]
        pts += [f"À l'inverse, {c['titre'].lower()}." for c in r["compensations"]]
        return {"reponse": r["resume"], "points": pts, "rca": r,
                "actions": [{"label": "Voir l'analyse complète", "route": "/signaux"}],
                "faits": {"resume": r["resume"], "causes": [c["titre"] + " — " + c["explication"] for c in r["causes"]]}}

    def retards(self, e, q):
        o = [f for f in self.c.factures_ouvertes if f["jours_depasses"] > 0
             and (not e["structure_id"] or f["structure_id"] == e["structure_id"])]
        if not o:
            return {"reponse": "Personne n'est en retard en ce moment. Toutes les factures échues sont réglées.", "faits": {}}
        total = sum(f["montant_ttc"] for f in o)
        return {"reponse": f"{len(o)} facture{'s' if len(o) > 1 else ''} en retard, pour {dh(total)} :",
                "points": [f"{f['numero']} — {f['client']} : {dh(f['montant_ttc'])}, échue depuis {f['jours_depasses']} jours. "
                           + _point(f"Paiement probable vers le {date_fr(pd.Timestamp(f['date_paiement_probable']))}") for f in o],
                "actions": [{"label": "Préparer les relances", "route": "/factures"}],
                "faits": {"total": total, "factures": o}}

    def projets(self, e, q):
        p = self.c.projets_etat()
        if e["projet"]:
            p = [x for x in p if x["id"] == e["projet"][0]]
        clients_ = [x for x in p if x["client_id"]]
        internes = [x for x in p if not x["client_id"]]
        pts = []
        for x in sorted(clients_, key=lambda x: x["marge_pct"]):
            etat = (f"budget dépassé de {dh(x['cout_reel'] - x['budget'])}" if x["cout_reel"] > x["budget"]
                    else f"{x['consommation']:.0f} % du budget consommé")
            pts.append(f"{x['nom']} : marge {dh(x['marge'])} ({x['marge_pct']:.0f} %), {etat}")
        for x in internes:
            pts.append(f"{x['nom']} (projet interne, pas encore facturé) : {dh(x['cout_reel'])} investis, "
                       f"{x['consommation']:.0f} % du budget")
        pire = min(clients_, key=lambda x: x["marge_pct"]) if clients_ else None
        if pire and len(p) > 1:
            rep = (f"Aucun projet client ne perd d'argent pour l'instant. Le plus fragile est {pire['nom']}, "
                   f"avec une marge de {pire['marge_pct']:.0f} %." if pire["marge"] >= 0 else
                   f"{pire['nom']} perd de l'argent : {dh(pire['marge'])} de marge.")
        else:
            rep = "Voici où en est le projet :"
        return {"reponse": rep, "points": pts, "actions": [{"label": "Ouvrir les projets", "route": "/projets"}],
                "faits": {"projets": p}}

    def prevision(self, e, q):
        ids = [e["structure_id"]] if e["structure_id"] else list(self.c.structures.id)
        try:
            f = self.c.prevision.prevoir(ids, self.c.soldes)
        except ValueError as exc:
            return {"reponse": str(exc), "faits": {}}
        fin = f["prevision"][-1]
        rep = (f"D'ici le {date_fr(pd.Timestamp(fin['semaine']))}, {self._nom_structure(e['structure_id'])} devrait avoir autour de "
               f"{dh(fin['p50'])} (entre {dh(fin['p10'])} et {dh(fin['p90'])}).")
        if f["proba_solde_negatif"] > 0.05:
            rep += f" Il y a {f['proba_solde_negatif'] * 100:.0f} % de risque de passer sous zéro à un moment."
        return {"reponse": rep, "prevision": f, "actions": [{"label": "Ouvrir le simulateur", "route": "/scenarios"}],
                "faits": {"solde_actuel": f["solde_actuel"], "dans_13_semaines": fin}}

    def anomalies(self, e, q):
        a = self.c.anomalies.lister(e["structure_id"], depuis=pd.Timestamp(self.c.ref) - pd.Timedelta(days=60), limite=5)
        if not a:
            return {"reponse": "Rien d'anormal sur les deux derniers mois.", "faits": {}}
        return {"reponse": f"J'ai repéré {len(a)} mouvement{'s' if len(a) > 1 else ''} qui méritent un coup d'œil :",
                "points": [f"{joli_libelle(x['libelle'])} ({dh(-x['montant'])}, {date_fr(pd.Timestamp(x['date']))}) — {' '.join(x['raisons'])}" for x in a],
                "sources": [x["transaction_id"] for x in a], "faits": {"anomalies": a}}

    def client(self, e, q):
        if not e["client"]:
            return {"reponse": "De quel client parles-tu ? Donne-moi son nom.", "faits": {}}
        cid, nom = e["client"]
        prof = next((p for p in self.c.paiement.profil_clients() if p["client_id"] == cid), None)
        ouv = [f for f in self.c.factures_ouvertes if f["client_id"] == cid]
        enc = self.c.tx[(self.c.tx.client_id == cid) & (self.c.tx.montant > 0)].montant.sum()
        rep = f"{nom} t'a versé {dh(enc)} au total."
        if prof:
            rep += f" Il paie en moyenne {prof['retard_moyen']:.0f} jours après l'échéance ({prof['factures_payees']} factures réglées)."
        pts = [f"{f['numero']} : {dh(f['montant_ttc'])}, risque {f['risque']} — {f['raison']}" for f in ouv]
        return {"reponse": rep, "points": pts, "faits": {"encaisse": enc, "profil": prof, "ouvertes": ouv}}

    def remuneration(self, e, q):
        ref = pd.Timestamp(self.c.ref).replace(day=1)
        t = self.c.tx[self.c.tx.structure_id.isin([1, 2]) & (self.c.tx.date_op >= ref - pd.DateOffset(months=6))
                      & (self.c.tx.date_op < ref)]
        hors_remu = t[~t.libelle.str.contains("REMUNERATION|APPORT", case=False)]
        net = hors_remu.groupby(hors_remu.date_op.dt.to_period("M")).montant.sum()
        actuel = -t[t.libelle.str.contains("REMUNERATION", case=False)].groupby(t.date_op.dt.to_period("M")).montant.sum().median()
        mediane = float(net.median())
        prudent = max(0.0, mediane * 0.7)
        rep = (f"Avant ta rémunération, l'agence et la société dégagent environ {dh(mediane)} par mois (médiane sur 6 mois). "
               f"Tu te verses {dh(actuel)}. En gardant 30 % de marge de sécurité, tu pourrais aller jusqu'à {dh(prudent)} par mois.")
        return {"reponse": rep, "points": ["Le choix entre salaire, dividendes et compte courant d'associé change l'impôt : "
                                            "fais valider le montage par ton expert-comptable."],
                "actions": [{"label": "Tester dans le simulateur", "route": "/scenarios"}],
                "faits": {"marge_mensuelle": mediane, "remuneration_actuelle": actuel, "plafond_prudent": prudent}}

    def aide(self, e, q):
        return {"reponse": "Je lis tes comptes, tes factures et tes projets, et je réponds avec les vrais chiffres. "
                           "Tu peux me demander par exemple :", "points": AIDE, "faits": {}}

    # ---------- point d'entrée ----------
    def repondre(self, question: str, structure_id=None):
        intent, conf = self.intention(question)
        e = self.entites(question, structure_id)
        if e["client"] and (intent == "aide" or conf < 0.45):
            intent, conf = "client", max(conf, 0.5)
        if conf < 0.4:
            res = {"reponse": HORS_SUJET, "points": AIDE[:4], "faits": {}}
            if llm.disponible():
                s = self.c.structures
                faits = {"soldes": dict(zip(s.nom, s.solde.round())), "date": str(self.c.ref)}
                libre = llm.reformuler(question, faits, "Je ne suis pas sûre de comprendre la question.")
                if libre:
                    res["reponse_llm"] = libre
            res.update({"intention": "inconnue", "confiance": round(conf, 3), "entites": {},
                        "moteur": "LLM local (Ollama)" if res.get("reponse_llm") else "Maliya (règles + ML)"})
            res.pop("faits", None)
            return res
        res = getattr(self, intent)(e, question)
        res["intention"] = intent
        res["confiance"] = round(conf, 3)
        res["entites"] = {k: v for k, v in e.items() if v}
        brouillon = res["reponse"] + ("\n" + "\n".join(res.get("points", [])) if res.get("points") else "")
        reecrit = llm.reformuler(question, res.get("faits", {}), brouillon) if intent != "aide" else None
        res["reponse_llm"] = reecrit
        res["moteur"] = "LLM local (Ollama)" if reecrit else "Maliya (règles + ML)"
        res.pop("faits", None)
        return res
