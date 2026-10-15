"""Petits outils de langue : nettoyage des libellés bancaires, montants à la marocaine, mois en français."""
import re
import unicodedata
from datetime import date

MOIS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août",
        "septembre", "octobre", "novembre", "décembre"]

BRUIT_BANCAIRE = r"\b(cb|prlv|vir|virement|recu|reçu|sepa|carte|paiement|achat|retrait|dab|ref|fac)\b"


def sans_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def nettoyer_libelle(lib: str) -> str:
    s = sans_accents(lib.lower())
    s = re.sub(r"[a-z]{2}-\d{4}-\d{3}", " ", s)      # numéros de facture
    s = re.sub(r"\d+([/.,]\d+)*", " ", s)              # montants, dates
    s = re.sub(BRUIT_BANCAIRE, " ", s)
    s = re.sub(r"[^a-z ]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def marchand(lib: str) -> str:
    """Clé courte qui identifie le fournisseur : 'CB AWS EMEA SARL AWS.AMAZON.COM' -> 'aws emea sarl'."""
    mots = nettoyer_libelle(lib).split()
    return " ".join(mots[:3]) or lib.lower()


def dh(montant: float, signe: bool = False) -> str:
    """12400.5 -> '12 401 dh' (espace fine insécable comme séparateur de milliers)."""
    v = round(abs(montant))
    txt = f"{v:,}".replace(",", "\u202f") + "\u00a0dh"
    if signe:
        return ("+" if montant >= 0 else "−") + txt
    return ("−" if montant < 0 else "") + txt


def mois_fr(d) -> str:
    return f"{MOIS[d.month - 1]} {d.year}"


MOIS_COURTS = ["janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.", "nov.", "déc."]


def date_fr(d) -> str:
    """'4 janvier' : mois en toutes lettres, plus chaleureux et sans point d'abréviation en fin de phrase."""
    return f"{'1er' if d.day == 1 else d.day} {MOIS[d.month - 1]}"


def aujourd_hui() -> date:
    import os
    forcee = os.getenv("MALIYA_AUJOURDHUI")
    return date.fromisoformat(forcee) if forcee else date.today()


def joli_libelle(lib: str) -> str:
    """'CB AMAZON MKTPLACE EU' -> 'Amazon Mktplace Eu' : enlève le jargon bancaire du début."""
    s = re.sub(r"^(CB|PRLV|VIR RECU|VIR|PAIEMENT|ACHAT)\s+", "", lib.strip(), flags=re.I)
    petits = {"de", "du", "la", "le", "des", "et", "vers", "sur"}
    mots = [m.lower() if m.lower() in petits else (m if len(m) <= 3 and m.isupper() and m not in ("EU",) else m.capitalize())
            for m in s.split()]
    return " ".join(mots)
