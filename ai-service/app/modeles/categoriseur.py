"""
Catégorisation des mouvements — machine learning classique.

TF-IDF sur n-grammes de caractères (robuste aux libellés bancaires tronqués)
+ régression logistique multinomiale. Entraîné sur l'historique déjà catégorisé
de l'utilisateur, enrichi d'un petit lexique français / darija / marques courantes
au Maroc pour démarrer même sans historique.
"""
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import cross_val_score
from sklearn.pipeline import make_pipeline

from ..texte import nettoyer_libelle

LEXIQUE = {
    "REPAS": ["cafe", "restaurant", "glovo", "jumia food", "makla", "ftour", "pizza", "snack", "salon de the",
              "kahwa", "mcdonalds", "starbucks", "boulangerie", "patisserie"],
    "CLOUD": ["aws", "amazon web services", "digitalocean", "ovhcloud", "hetzner", "gcp google cloud", "azure",
              "vercel", "netlify", "cloudflare", "heroku", "linode", "datadog", "sentry", "hebergement", "serveur",
              "vps", "nom de domaine", "domaine", "hosting"],
    "LOGICIELS": ["notion", "figma", "github", "gitlab", "jetbrains", "slack", "zoom", "canva", "adobe",
                  "microsoft", "google workspace", "openai", "anthropic", "linkedin premium", "apple com bill",
                  "dropbox", "atlassian", "jira", "grafana labs", "shopify"],
    "DEPLACEMENT": ["oncf", "al boraq", "royal air maroc", "ram", "taxi", "careem", "indrive", "shell", "afriquia",
                    "total energies", "essence", "lbenzine", "petrom", "autoroute adm", "peage", "ctm", "ryanair"],
    "TELECOM": ["orange maroc", "inwi", "maroc telecom", "iam", "fibre", "forfait", "recharge"],
    "COURSES": ["marjane", "carrefour", "aswak assalam", "bim", "acima", "label vie", "hanout", "souk", "khodra"],
    "LOISIRS": ["netflix", "spotify", "steam", "cinema", "pathe", "playstation", "decathlon", "megarama", "disney"],
    "LOYER": ["loyer", "lkra", "kra", "bail", "cowork", "bureau", "syndic"],
    "SALAIRES": ["salaire", "paie", "khlass"],
    "FREELANCE": ["freelance", "mission", "prestation", "consultant", "malt", "upwork", "auto entrepreneur"],
    "MARKETING": ["meta ads", "facebook ads", "google ads", "linkedin ads", "tiktok ads", "sponsoring", "flyers"],
    "MATERIEL": ["electroplanet", "macbook", "ecran", "clavier", "souris", "imprimante", "bureau vallee", "ikea",
                 "amazon mktplace", "amazon marketplace", "jumia", "aliexpress", "pc portable", "telephone pro"],
    "IMPOTS": ["dgi", "tva", "impot", "simpl", "taxe professionnelle", "is acompte"],
    "CNSS": ["cnss", "damancom", "amo", "cimr"],
    "BANQUE": ["frais tenue", "commission", "agios", "frais bancaires", "cotisation carte"],
    "REV_CLIENT": ["recu client", "reglement facture", "paiement facture", "encaissement", "wslni", "khlsni"],
}


def _texte(libelle: str, montant: float) -> str:
    return f"{nettoyer_libelle(libelle)} {'zzentree' if montant > 0 else 'zzsortie'}"


class Categoriseur:
    def __init__(self):
        self.pipe = None
        self.codes = []
        self.score_cv = None
        self.n_exemples = 0

    def entrainer(self, tx: pd.DataFrame):
        hist = tx.dropna(subset=["cat_code"])
        hist = hist[hist.cat_code != "TRANSFERT"]
        X = [_texte(l, m) for l, m in zip(hist.libelle, hist.montant)]
        y = list(hist.cat_code)
        for code, mots in LEXIQUE.items():
            sens = 1 if code == "REV_CLIENT" else -1
            for mot in mots:
                X += [_texte(mot, sens)] * 3
                y += [code] * 3
        self.pipe = make_pipeline(
            TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), sublinear_tf=True, min_df=1),
            LogisticRegression(max_iter=3000, C=8.0),
        )
        self.pipe.fit(X, y)
        self.codes = list(self.pipe.classes_)
        self.n_exemples = len(X)
        try:
            self.score_cv = float(np.mean(cross_val_score(self.pipe, X, y, cv=4)))
        except ValueError:
            self.score_cv = None
        return self

    def predire(self, libelle: str, montant: float, top: int = 3):
        proba = self.pipe.predict_proba([_texte(libelle, montant)])[0]
        ordre = np.argsort(proba)[::-1][:top]
        meilleur = float(proba[ordre[0]])
        return {
            "categorie": self.codes[ordre[0]],
            "confiance": round(meilleur, 3),
            "niveau": "sûr" if meilleur >= 0.6 else "plutôt sûr" if meilleur >= 0.35 else "à vérifier",
            "alternatives": [{"categorie": self.codes[i], "confiance": round(float(proba[i]), 3)} for i in ordre[1:]],
        }
