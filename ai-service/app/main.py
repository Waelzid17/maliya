"""
Maliya — service IA.

Toutes les routes lisent le grand livre PostgreSQL (lecture seule) et renvoient des analyses.
Les modèles se ré-entraînent tout seuls quand les données changent.
"""
import logging
import os
import threading
import time
from contextlib import asynccontextmanager
from datetime import date

import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from . import db
from .analyses import briefing, rca, saisie, simulateur
from .copilote import llm
from .copilote.assistant import Copilote
from .modeles.anomalies import DetecteurAnomalies
from .modeles.categoriseur import Categoriseur
from .modeles.paiement import RisquePaiement
from .modeles.prevision import Prevision
from .texte import aujourd_hui, dh, date_fr

log = logging.getLogger("maliya.ia")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


MIN_MOUVEMENTS = 60  # en dessous, on ne prétend pas prédire quoi que ce soit


class Cerveau:
    """Garde les données et les modèles en mémoire, et les remet à jour quand le grand livre bouge."""

    def __init__(self):
        self.verrou = threading.Lock()
        self.signature = None
        self.pret = False
        self.metriques = {}
        self.assez = False

    def _signature(self):
        s = db.query("""SELECT (SELECT COUNT(*) FROM transaction) n, (SELECT COALESCE(MAX(id),0) FROM transaction) m,
                               (SELECT COUNT(categorie_id) FROM transaction) c,
                               (SELECT COUNT(*) FROM facture) f, (SELECT COUNT(date_paiement) FROM facture) p""")
        return tuple(int(v) for v in s.iloc[0])

    def charger(self, force=False):
        sig = self._signature()
        if sig == self.signature and not force:
            return
        with self.verrou:
            if sig == self.signature and not force:  # une autre requête vient de tout recharger
                return
            t0 = time.time()
            # Le LSTM est le plus long à entraîner : seulement au démarrage ou quand de nouveaux mouvements arrivent
            refaire_lstm = force or self.signature is None or sig[1] != self.signature[1] or not hasattr(self, "prevision")
            self.ref = aujourd_hui()
            self.tx = db.transactions()
            self.factures = db.factures()
            self.structures = db.structures()
            self.soldes = dict(zip(self.structures.id, self.structures.solde))
            self.categories = db.categories()
            self.clients = db.clients()
            self.noms_clients = dict(zip(self.clients.id, self.clients.nom))
            self.projets = db.projets()

            self.categoriseur = Categoriseur().entrainer(self.tx)
            self.assez = len(self.tx) >= MIN_MOUVEMENTS and self.factures.date_paiement.notna().sum() >= 5
            if not self.assez:
                self.signature = sig
                self.pret = True
                self.factures_ouvertes = []
                self.metriques = {"historique": "insuffisant", "mouvements": len(self.tx), "date_reference": self.ref.isoformat()}
                log.info("Seulement %d mouvements : modèles prédictifs en attente", len(self.tx))
                return
            self.anomalies = DetecteurAnomalies().entrainer(self.tx)
            self.paiement = RisquePaiement().entrainer(self.factures, self.ref)
            self.factures_ouvertes = self.paiement.factures_ouvertes()
            if refaire_lstm:
                self.prevision = Prevision().entrainer(self.tx, list(self.structures.id), self.ref)
            self.copilote = Copilote(self)
            self.signature = sig
            self.pret = True
            self.metriques = {
                "categorisation": {"modele": "TF-IDF caractères + régression logistique",
                                   "exemples": self.categoriseur.n_exemples,
                                   "precision_validation_croisee": self.categoriseur.score_cv},
                "prevision": {"modele": self.prevision.moteur, "perte_huber_finale": self.prevision.perte_finale},
                "anomalies": {"modeles": self.anomalies.moteurs},
                "paiements": {"modele": "Gradient boosting (médiane + quantiles 20/80)",
                              "erreur_moyenne_jours": round(self.paiement.mae, 1)},
                "copilote": {"intention": "TF-IDF mots+caractères + régression logistique",
                             "llm_local": llm.OLLAMA_MODELE if llm.disponible() else None},
                "entraine_en_secondes": round(time.time() - t0, 1),
                "date_reference": self.ref.isoformat(),
            }
            log.info("Modèles prêts en %.1fs (%d mouvements)", time.time() - t0, len(self.tx))

    def projets_etat(self):
        out = []
        fact = self.factures.groupby("projet_id").montant_ht.sum()
        ref = pd.Timestamp(self.ref)
        for p in self.projets.itertuples():
            couts = self.tx[(self.tx.projet_id == p.id) & (self.tx.montant < 0)]
            recents = couts[couts.date_op >= ref - pd.DateOffset(months=3)]
            rythme = -recents.montant.sum() / 3 if len(recents) else 0.0
            facture_ht = float(fact.get(p.id, 0.0))
            cout = float(p.cout_reel)
            marge = facture_ht - cout
            reste = float(p.budget) - cout
            epuise = None
            if p.statut == "EN_COURS" and rythme > 0 and reste > 0:
                epuise = (ref + pd.Timedelta(days=int(reste / rythme * 30))).date().isoformat()
            out.append({
                "id": int(p.id), "nom": p.nom, "structure_id": int(p.structure_id),
                "client_id": int(p.client_id) if pd.notna(p.client_id) else None,
                "statut": p.statut, "budget": float(p.budget), "cout_reel": round(cout, 2),
                "facture_ht": round(facture_ht, 2), "encaisse": round(float(p.encaisse), 2),
                "marge": round(marge, 2), "marge_pct": round(100 * marge / facture_ht, 1) if facture_ht else -100.0,
                "consommation": round(100 * cout / float(p.budget), 1) if p.budget else 0.0,
                "rythme_mensuel": round(rythme, 2), "budget_epuise_vers": epuise,
            })
        return out


cerveau = Cerveau()


def _charger_au_demarrage():
    for _ in range(40):
        try:
            cerveau.charger()
            return
        except Exception as exc:  # la base démarre peut-être encore
            log.warning("Base pas encore prête (%s), nouvel essai dans 3 s", exc)
            time.sleep(3)


@asynccontextmanager
async def cycle_de_vie(_app):
    threading.Thread(target=_charger_au_demarrage, daemon=True).start()
    yield


app = FastAPI(title="Maliya — service IA", version="1.0.0", lifespan=cycle_de_vie)


def _pret(historique=True):
    try:
        cerveau.charger()
    except Exception as exc:  # base indisponible au démarrage, par exemple
        log.exception("Chargement impossible")
        raise HTTPException(503, f"Le service IA ne peut pas lire la base : {exc}") from exc
    if historique and not cerveau.assez:
        raise HTTPException(409, f"Il me faut au moins {MIN_MOUVEMENTS} mouvements et quelques factures payées "
                                 "avant de pouvoir prévoir ou expliquer. Continue à noter tes mouvements.")
    return cerveau


@app.get("/sante")
def sante():
    return {"statut": "ok" if cerveau.pret else "en_preparation", "llm_local": llm.disponible()}


@app.get("/modeles")
def modeles():
    return _pret(historique=False).metriques


@app.post("/entrainer")
def entrainer():
    cerveau.charger(force=True)
    return cerveau.metriques


@app.get("/briefing")
def get_briefing(structure_id: int | None = None):
    c = _pret()
    b = briefing.construire(c, structure_id)
    b["salutation"] = briefing.salutation(os.getenv("MALIYA_PRENOM", "Wael"))
    return b


@app.get("/prevision")
def prevision(structure_id: int | None = None, semaines: int = 13):
    c = _pret()
    ids = [structure_id] if structure_id else list(c.structures.id)
    try:
        return c.prevision.prevoir(ids, c.soldes, semaines=min(max(semaines, 4), 26))
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc


@app.get("/anomalies")
def anomalies(structure_id: int | None = None, jours: int = 60):
    c = _pret()
    return c.anomalies.lister(structure_id, depuis=pd.Timestamp(c.ref) - pd.Timedelta(days=jours), limite=12)


@app.get("/paiements")
def paiements(structure_id: int | None = None):
    c = _pret()
    return [f for f in c.factures_ouvertes if not structure_id or f["structure_id"] == structure_id]


@app.get("/rca")
def get_rca(structure_id: int | None = None, mois: str | None = None):
    c = _pret()
    return rca.expliquer(c.tx, c.factures_ouvertes, structure_id, mois, c.ref, c.noms_clients)


@app.get("/projets")
def projets():
    return _pret().projets_etat()


class Question(BaseModel):
    question: str
    structure_id: int | None = None


@app.post("/copilote")
def copilote(q: Question):
    if not q.question.strip():
        raise HTTPException(400, "La question est vide.")
    return _pret().copilote.repondre(q.question, q.structure_id)


class Simulation(BaseModel):
    structure_id: int | None = None
    scenarios: list[dict] = []


@app.post("/simulation")
def simulation(s: Simulation):
    c = _pret()
    ids = [s.structure_id] if s.structure_id else list(c.structures.id)
    solde = sum(c.soldes.get(i, 0.0) for i in ids)
    # Les premiers mois suivent la prévision du LSTM, pour rester cohérent avec le reste de l'app
    flux, fin = None, None
    try:
        f = c.prevision.prevoir(ids, c.soldes, semaines=13)
        flux, precedent = {}, f["solde_actuel"]
        for p in f["prevision"]:
            cle = p["semaine"][:7]
            flux[cle] = flux.get(cle, 0.0) + p["p50"] - precedent
            precedent = p["p50"]
        fin = pd.Timestamp(f["prevision"][-1]["semaine"]) + pd.Timedelta(days=6)
    except ValueError:
        pass  # pas d'historique : on projette avec la moyenne seule
    return simulateur.simuler(c.tx, solde, s.scenarios, s.structure_id, c.ref, flux_ia=flux, fin_ia=fin)


class Mouvement(BaseModel):
    libelle: str
    montant: float


@app.post("/categoriser")
def categoriser(m: Mouvement):
    c = _pret(historique=False)
    r = c.categoriseur.predire(m.libelle, m.montant)
    ids = dict(zip(c.categories.code, c.categories.id))
    libs = dict(zip(c.categories.code, c.categories.libelle))
    r["categorie_id"] = int(ids[r["categorie"]])
    r["categorie_libelle"] = libs[r["categorie"]]
    for a in r["alternatives"]:
        a["categorie_id"] = int(ids[a["categorie"]])
        a["categorie_libelle"] = libs[a["categorie"]]
    return r


@app.get("/a-classer")
def a_classer(structure_id: int | None = None):
    """Propositions de catégorie pour tous les mouvements qui n'en ont pas."""
    c = _pret()
    nc = c.tx[c.tx.categorie_id.isna()]
    if structure_id:
        nc = nc[nc.structure_id == structure_id]
    return [{"transaction_id": int(r.id), "libelle": r.libelle, "montant": float(r.montant),
             "date": r.date_op.date().isoformat(), "structure": r.structure,
             **categoriser(Mouvement(libelle=r.libelle, montant=float(r.montant)))}
            for r in nc.sort_values("date_op", ascending=False).itertuples()]


class Saisie(BaseModel):
    texte: str


@app.post("/saisie")
def saisie_naturelle(s: Saisie):
    c = _pret(historique=False)
    r = saisie.analyser(
        s.texte, c.categoriseur,
        [(int(x.id), x.nom, x.type) for x in c.structures.itertuples()],
        [(int(x.id), x.nom, int(x.structure_id)) for x in c.projets.itertuples()],
        [(int(x.id), x.nom) for x in c.clients.itertuples()],
        c.ref,
    )
    ids = dict(zip(c.categories.code, c.categories.id))
    libs = dict(zip(c.categories.code, c.categories.libelle))
    r["categorie"]["categorie_id"] = int(ids[r["categorie"]["categorie"]])
    r["categorie"]["categorie_libelle"] = libs[r["categorie"]["categorie"]]
    return r


class Relance(BaseModel):
    facture_id: int


@app.post("/relance")
def relance(r: Relance):
    """Rédige une relance dont le ton dépend du profil du client. Rien n'est envoyé : c'est un brouillon."""
    c = _pret()
    f = next((x for x in c.factures_ouvertes if x["facture_id"] == r.facture_id), None)
    if not f:
        raise HTTPException(404, "Cette facture n'est pas en attente de paiement.")
    ech = date_fr(pd.Timestamp(f["echeance"]))
    if f["jours_depasses"] <= 0:
        ton, texte = "cordial", (
            f"Bonjour,\n\nPetit rappel amical : la facture {f['numero']} de {dh(f['montant_ttc'])} arrive à échéance le {ech}. "
            f"N'hésitez pas à me dire si vous avez besoin d'un document.\n\nBonne journée,\nWael")
    elif f["risque"] == "élevé" and f["jours_depasses"] > 30:
        ton, texte = "ferme", (
            f"Bonjour,\n\nSauf erreur de ma part, la facture {f['numero']} de {dh(f['montant_ttc'])}, échue le {ech}, "
            f"reste impayée depuis {f['jours_depasses']} jours. Pouvez-vous me confirmer une date de règlement cette semaine ? "
            f"Sans retour d'ici vendredi, je serai obligé de suspendre les prochaines livraisons.\n\nCordialement,\nWael Zidane")
    else:
        ton, texte = "courtois", (
            f"Bonjour,\n\nJe me permets de revenir vers vous au sujet de la facture {f['numero']} ({dh(f['montant_ttc'])}), "
            f"échue le {ech}. Pouvez-vous me dire quand le virement est prévu ?\n\nMerci d'avance,\nWael")
    return {"facture": f, "ton": ton, "message": texte, "canal_conseille": "WhatsApp" if f["risque"] != "élevé" else "Email"}


@app.get("/")
def racine():
    return {"service": "Maliya IA", "date_reference": date.today().isoformat() if not cerveau.pret else cerveau.ref.isoformat()}
