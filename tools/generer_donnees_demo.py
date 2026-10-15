"""
Génère backend/src/main/resources/db/demo/V2__donnees_demo.sql

Données fictives mais réalistes : 18 mois d'activité pour un entrepreneur de Tanger
qui gère une agence, une société, un projet et ses finances perso.
Quelques histoires sont cachées dedans pour que l'IA ait des choses à trouver :
  - Atlas Logistique paie de plus en plus tard (risque de paiement)
  - la facture AWS double en septembre 2026 (anomalie + RCA)
  - un gros freelance sur la plateforme Atlas fait déraper le budget (projet)
  - un prélèvement Adobe en double (anomalie / doublon)
  - une douzaine de mouvements récents pas encore catégorisés (catégorisation IA)

Usage : python tools/generer_donnees_demo.py
"""
import random
from datetime import date, timedelta
from pathlib import Path

random.seed(17)
AUJOURDHUI = date(2026, 10, 15)
DEBUT = date(2025, 4, 1)
SORTIE = Path(__file__).resolve().parents[1] / "backend/src/main/resources/db/demo/V2__donnees_demo.sql"

STRUCTURES = [
    (1, "Zidane Digital", "AGENCE", "#3B5BA9", "002765431000045"),
    (2, "Maliya SARL", "SOCIETE", "#2E8B6F", "003118842000071"),
    (3, "Projet Atlas", "PROJET", "#D99A1E", None),
    (4, "Perso", "PERSO", "#8A4F7D", None),
]
COMPTES = [
    (1, 1, "Compte pro principal", "Attijariwafa Bank", 320000),
    (2, 2, "Compte société", "CIH Bank", 70000),
    (3, 3, "Compte projet", "Bank of Africa", 60000),
    (4, 4, "Compte courant", "Banque Populaire", 30000),
]
CATEGORIES = [
    (1, "REV_CLIENT", "Revenus clients", "ENTREE"),
    (2, "SALAIRES", "Salaires", "SORTIE"),
    (3, "FREELANCE", "Freelances", "SORTIE"),
    (4, "LOYER", "Loyer & bureaux", "SORTIE"),
    (5, "CLOUD", "Hébergement & cloud", "SORTIE"),
    (6, "LOGICIELS", "Logiciels & abonnements", "SORTIE"),
    (7, "MARKETING", "Marketing", "SORTIE"),
    (8, "DEPLACEMENT", "Déplacements", "SORTIE"),
    (9, "MATERIEL", "Matériel", "SORTIE"),
    (10, "IMPOTS", "Impôts & TVA", "SORTIE"),
    (11, "CNSS", "Charges sociales", "SORTIE"),
    (12, "BANQUE", "Frais bancaires", "SORTIE"),
    (13, "REPAS", "Repas & cafés", "SORTIE"),
    (14, "TELECOM", "Téléphone & internet", "SORTIE"),
    (15, "TRANSFERT", "Transferts internes", "MIXTE"),
    (16, "COURSES", "Courses & maison", "SORTIE"),
    (17, "LOISIRS", "Loisirs", "SORTIE"),
]
CAT = {c[1]: c[0] for c in CATEGORIES}

CLIENTS = [
    # id, nom, ville, email, secteur, retard moyen (jours), dérive du retard par mois
    (1, "Atlas Logistique", "Tanger", "compta@atlas-logistique.example", "Logistique", 20, 2.2),
    (2, "Kasbah Ventures", "Casablanca", "finance@kasbah-ventures.example", "Investissement", 10, 0.3),
    (3, "Studio Zellige", "Fès", "bonjour@studio-zellige.example", "Artisanat", 4, 0.0),
    (4, "Riad Bleu Hôtels", "Chefchaouen", "direction@riadbleu.example", "Hôtellerie", 2, 0.0),
    (5, "Medina Shop", "Tétouan", "admin@medinashop.example", "E-commerce", 5, 0.1),
    (6, "Rif Agro", "Al Hoceima", "achats@rifagro.example", "Agroalimentaire", 12, 0.0),
    (7, "Normandie Tech", "Rouen", "ap@normandie-tech.example", "Logiciel", 0, 0.0),
]
RETARD = {c[0]: (c[5], c[6]) for c in CLIENTS}

PROJETS = [
    # id, structure, client, nom, budget, début, fin, statut
    (1, 1, 4, "Refonte site Riad Bleu", 60000, date(2025, 4, 10), date(2025, 9, 30), "TERMINE"),
    (2, 1, 5, "App mobile Medina Shop", 110000, date(2025, 10, 1), None, "EN_COURS"),
    (3, 1, 1, "Plateforme B2B Atlas Logistique", 145000, date(2025, 7, 1), None, "EN_COURS"),
    (4, 2, None, "Maliya SaaS", 260000, date(2025, 6, 1), None, "EN_COURS"),
    (5, 3, 2, "Observabilité Kasbah", 175000, date(2025, 9, 1), None, "EN_COURS"),
    (6, 2, 6, "Intégration ERP Rif Agro", 40000, date(2025, 4, 15), date(2026, 2, 28), "TERMINE"),
    (7, 2, 7, "Conseil cloud Normandie Tech", 25000, date(2026, 3, 1), None, "EN_COURS"),
    (8, 1, 3, "Boutique en ligne Studio Zellige", 30000, date(2026, 5, 1), None, "EN_COURS"),
]

transactions = []  # (compte, structure, projet, categorie, client, date, libelle, montant, source, inter)
factures = []      # (numero, structure, client, projet, objet, emission, echeance, paiement, ht, tva)


def tx(structure, d, libelle, montant, cat=None, projet=None, client=None, source="IMPORT", inter=False):
    if d > AUJOURDHUI:
        return
    transactions.append((structure, structure, projet, cat, client, d, libelle, round(montant, 2), source, inter))


def mois_iter():
    d = DEBUT
    while d <= AUJOURDHUI:
        yield d
        d = (d.replace(day=28) + timedelta(days=5)).replace(day=1)


def jour(m, j):
    try:
        return m.replace(day=j)
    except ValueError:
        return m.replace(day=28)


def bruit(x, pct=0.08):
    return x * (1 + random.uniform(-pct, pct))


compteurs = {1: 0, 2: 0, 3: 0}
PREFIXE = {1: "ZD", 2: "ML", 3: "PA"}


def facturer(structure, client, projet, objet, emission, ht):
    compteurs[structure] += 1
    numero = f"{PREFIXE[structure]}-{emission.year}-{compteurs[structure]:03d}"
    echeance = emission + timedelta(days=30)
    base, derive = RETARD[client]
    mois_ecoules = (emission.year - DEBUT.year) * 12 + emission.month - DEBUT.month
    retard = max(-3, int(random.gauss(base + derive * mois_ecoules, 4)))
    paiement = echeance + timedelta(days=retard)
    if paiement > AUJOURDHUI:
        paiement = None
    factures.append((numero, structure, client, projet, objet, emission, echeance, paiement, round(ht, 2), 20.0))
    if paiement:
        nom = next(c[1] for c in CLIENTS if c[0] == client).upper()
        tx(structure, paiement, f"VIR RECU {nom} {numero}", ht * 1.2, CAT["REV_CLIENT"], projet, client)


# ---------- Revenus : jalons facturés par projet ----------
def jalons(projet_id, structure, client, debut, fin, total, n, objet):
    fin = fin or AUJOURDHUI - timedelta(days=5)
    pas = (fin - debut).days / n
    for i in range(n):
        d = debut + timedelta(days=int(pas * (i + 1)))
        if d <= AUJOURDHUI:
            facturer(structure, client, projet_id, f"{objet} — jalon {i + 1}/{n}", d, bruit(total / n, 0.05))


jalons(1, 1, 4, date(2025, 4, 10), date(2025, 9, 30), 160000, 4, "Refonte site")
jalons(2, 1, 5, date(2025, 10, 1), date(2026, 12, 15), 380000, 7, "App mobile")
jalons(3, 1, 1, date(2025, 7, 1), date(2026, 12, 31), 520000, 9, "Plateforme B2B")
jalons(5, 3, 2, date(2025, 9, 1), date(2026, 11, 30), 210000, 7, "Observabilité")
jalons(6, 2, 6, date(2025, 4, 15), date(2026, 2, 28), 138000, 5, "Intégration ERP")
jalons(7, 2, 7, date(2026, 3, 1), date(2026, 12, 31), 110000, 5, "Conseil cloud")
jalons(8, 1, 3, date(2026, 5, 1), date(2026, 11, 30), 150000, 3, "Boutique en ligne")
# Maintenance mensuelle Riad Bleu après livraison
m = date(2025, 10, 5)
while m <= AUJOURDHUI:
    facturer(1, 4, 1, "Maintenance mensuelle", m, 3500)
    m = (m.replace(day=28) + timedelta(days=5)).replace(day=5)

# Contrats mensuels (retainers)
m = date(2025, 4, 25)
while m <= AUJOURDHUI:
    facturer(1, 3, None, "Accompagnement SEO & contenu", m, 6000)
    if m >= date(2025, 10, 25):
        facturer(1, 5, 2, "Hébergement & support app", m, 3000)
    m = (m.replace(day=28) + timedelta(days=5)).replace(day=25)

# ---------- Charges récurrentes ----------
for m in mois_iter():
    an, mo = m.year, m.month
    # --- Agence ---
    tx(1, jour(m, 5), "PRLV LOYER BUREAU BD PASTEUR TANGER", -6500, CAT["LOYER"])
    tx(1, jour(m, 28), "VIR SALAIRE DEV FRONT", -bruit(11500, 0.0), CAT["SALAIRES"])
    tx(1, jour(m, 28), "VIR SALAIRE DESIGNER UI", -bruit(9800, 0.0), CAT["SALAIRES"])
    tx(1, jour(m, 10), f"CNSS DAMANCOM {mo:02d}/{an}", -bruit(5600, 0.03), CAT["CNSS"])
    aws = bruit(2100, 0.12)
    if (an, mo) == (2026, 9):
        aws = 5240.0
    if (an, mo) == (2026, 10):
        aws = 4810.0
    tx(1, jour(m, 3), "CB AWS EMEA SARL AWS.AMAZON.COM", -aws, CAT["CLOUD"], projet=3)
    tx(1, jour(m, 6), "CB FIGMA INC SAN FRANCISCO", -bruit(185, 0.02), CAT["LOGICIELS"])
    tx(1, jour(m, 7), "CB GITHUB INC", -bruit(430, 0.02), CAT["LOGICIELS"])
    tx(1, jour(m, 8), "CB GOOGLE WORKSPACE", -bruit(295, 0.02), CAT["LOGICIELS"])
    tx(1, jour(m, 12), "PRLV ADOBE CREATIVE CLOUD", -bruit(610, 0.01), CAT["LOGICIELS"])
    tx(1, jour(m, 15), "PRLV ORANGE MAROC FIBRE PRO", -449, CAT["TELECOM"])
    tx(1, jour(m, 30) if mo != 2 else jour(m, 28), "FRAIS TENUE DE COMPTE", -88, CAT["BANQUE"])
    for _ in range(random.randint(3, 6)):
        lieu = random.choice(["CAFE HAFA", "CAFE BALDARU", "RESTAURANT EL MORO", "PAUL TANGER CITY MALL", "CAFE DE PARIS TANGER"])
        tx(1, jour(m, random.randint(1, 27)), f"CB {lieu}", -bruit(random.choice([60, 95, 140, 320]), 0.2), CAT["REPAS"], source=random.choice(["IMPORT", "SMS"]))
    if random.random() < 0.45:
        tx(1, jour(m, random.randint(1, 27)), random.choice(["CB META ADS IRELAND", "CB LINKEDIN ADS", "CB GOOGLE ADS"]), -bruit(1800, 0.4), CAT["MARKETING"])
    if random.random() < 0.3:
        tx(1, jour(m, random.randint(1, 27)), random.choice(["ONCF AL BORAQ TANGER CASA", "CB ROYAL AIR MAROC", "CB AFRIQUIA TANGER"]), -bruit(750, 0.4), CAT["DEPLACEMENT"])
    if mo in (1, 4, 7, 10):
        tx(1, jour(m, 20), f"DGI TVA T{(mo - 1) // 3 or 4} SIMPL", -bruit(14500, 0.15), CAT["IMPOTS"])
    # Freelances sur la plateforme Atlas
    if date(2025, 8, 1) <= m:
        montant = bruit(6000, 0.2)
        if (an, mo) == (2026, 9):
            montant = 18500.0
        tx(1, jour(m, 18), "VIR FREELANCE BACKEND JAVA", -montant, CAT["FREELANCE"], projet=3)
    if date(2025, 10, 1) <= m:
        tx(1, jour(m, 19), "VIR FREELANCE FLUTTER", -bruit(5200, 0.15), CAT["FREELANCE"], projet=2)
    if date(2026, 5, 1) <= m:
        tx(1, jour(m, 21), "CB SHOPIFY PLUS", -bruit(320, 0.02), CAT["LOGICIELS"], projet=8)
        tx(1, jour(m, 22), "VIR FREELANCE INTEGRATEUR SHOPIFY", -bruit(4200, 0.1), CAT["FREELANCE"], projet=8)
    if date(2025, 4, 1) <= m <= date(2025, 9, 30):
        tx(1, jour(m, 17), "VIR FREELANCE DEV WORDPRESS", -bruit(7800, 0.1), CAT["FREELANCE"], projet=1)

    # Rémunération du dirigeant : agence -> perso
    d = jour(m, 27)
    tx(1, d, "VIR INTERNE VERS PERSO REMUNERATION", -12000, CAT["TRANSFERT"], inter=True)
    tx(4, d, "VIR RECU ZIDANE DIGITAL REMUNERATION", 12000, CAT["TRANSFERT"], inter=True)

    # --- Société ---
    tx(2, jour(m, 4), "CB OVHCLOUD", -bruit(780, 0.1), CAT["CLOUD"], projet=4)
    tx(2, jour(m, 9), "CB JETBRAINS", -bruit(260, 0.02), CAT["LOGICIELS"], projet=4)
    tx(2, jour(m, 30) if mo != 2 else jour(m, 28), "COMMISSION TENUE COMPTE CIH", -65, CAT["BANQUE"])
    if date(2025, 4, 1) <= m <= date(2026, 2, 28):
        tx(2, jour(m, 16), "VIR FREELANCE CONSULTANT ODOO", -bruit(4300, 0.1), CAT["FREELANCE"], projet=6)
    if date(2026, 3, 1) <= m:
        tx(2, jour(m, 6), "CB GOOGLE CLOUD EMEA", -bruit(1400, 0.15), CAT["CLOUD"], projet=7)
    if date(2026, 1, 1) <= m:
        tx(2, jour(m, 28), "VIR SALAIRE DEV BACKEND", -14000, CAT["SALAIRES"], projet=4)
        tx(2, jour(m, 10), f"CNSS DAMANCOM {mo:02d}/{an}", -bruit(3700, 0.03), CAT["CNSS"])
    if mo in (1, 4, 7, 10):
        tx(2, jour(m, 20), f"DGI TVA T{(mo - 1) // 3 or 4} SIMPL", -bruit(6500, 0.2), CAT["IMPOTS"])
    if random.random() < 0.25:
        tx(2, jour(m, random.randint(1, 27)), "CB CASA COWORK SPACE", -bruit(900, 0.1), CAT["LOYER"])

    # --- Projet Atlas (structure projet) ---
    if date(2025, 9, 1) <= m:
        tx(3, jour(m, 14), "VIR FREELANCE SRE KUBERNETES", -bruit(9500, 0.12), CAT["FREELANCE"], projet=5)
        tx(3, jour(m, 3), "CB GRAFANA LABS", -bruit(540, 0.05), CAT["LOGICIELS"], projet=5)
        tx(3, jour(m, 5), "CB HETZNER ONLINE GMBH", -bruit(1150, 0.1), CAT["CLOUD"], projet=5)
        if random.random() < 0.4:
            tx(3, jour(m, random.randint(1, 27)), "ONCF AL BORAQ TANGER CASA VOYAGE", -bruit(690, 0.2), CAT["DEPLACEMENT"], projet=5)

    # --- Perso ---
    tx(4, jour(m, 2), "VIR LOYER APPARTEMENT MALABATA", -4500, CAT["LOYER"])
    tx(4, jour(m, 16), "PRLV INWI FORFAIT MOBILE", -199, CAT["TELECOM"])
    for _ in range(random.randint(4, 7)):
        lieu = random.choice(["CB MARJANE TANGER", "CB CARREFOUR MARKET", "CB ASWAK ASSALAM", "CB BIM MAROC"])
        tx(4, jour(m, random.randint(1, 27)), lieu, -bruit(480, 0.4), CAT["COURSES"], source=random.choice(["IMPORT", "SMS"]))
    for _ in range(random.randint(1, 3)):
        lieu = random.choice(["CB CINEMA PATHE TANGER", "CB STEAM GAMES", "CB DECATHLON TANGER", "CB SPOTIFY"])
        tx(4, jour(m, random.randint(1, 27)), lieu, -bruit(220, 0.5), CAT["LOISIRS"])

# Achat de matériel ponctuel
tx(1, date(2025, 6, 12), "CB ELECTROPLANET MACBOOK PRO", -24500, CAT["MATERIEL"])
tx(2, date(2026, 1, 8), "CB ELECTROPLANET ECRANS DELL", -7800, CAT["MATERIEL"], projet=4)
# Apport perso vers la société
tx(4, date(2026, 8, 3), "VIR APPORT EN COMPTE COURANT MALIYA", -30000, CAT["TRANSFERT"], inter=True)
tx(2, date(2026, 8, 3), "VIR RECU APPORT ASSOCIE W.Z.", 30000, CAT["TRANSFERT"], inter=True)
# Doublon Adobe ce mois-ci (même jour, même montant)
tx(1, date(2026, 10, 12), "PRLV ADOBE CREATIVE CLOUD", -611.40, CAT["LOGICIELS"])
# Achat inhabituel
tx(1, date(2026, 10, 9), "CB AMAZON MKTPLACE EU", -7890, None, source="SMS")

# Mouvements récents pas encore catégorisés (l'IA doit proposer)
non_categorises = [
    (1, date(2026, 10, 2), "CB NOTION LABS INC", -132, "IMPORT"),
    (1, date(2026, 10, 4), "CB CAFE HAFA TANGER", -85, "SMS"),
    (1, date(2026, 10, 6), "CB LINKEDIN PREMIUM", -410, "IMPORT"),
    (1, date(2026, 10, 7), "VIR M. EL AMRANI MISSION UX", -4500, "WHATSAPP"),
    (1, date(2026, 10, 11), "CB SHELL TANGER ROUTE RABAT", -520, "SMS"),
    (2, date(2026, 10, 3), "CB DIGITALOCEAN.COM", -615, "IMPORT"),
    (2, date(2026, 10, 10), "CB APPLE.COM/BILL", -129, "IMPORT"),
    (3, date(2026, 10, 8), "CB DATADOG INC", -880, "IMPORT"),
    (4, date(2026, 10, 9), "CB GLOVO TANGER", -146, "SMS"),
    (4, date(2026, 10, 12), "CB NETFLIX.COM", -95, "IMPORT"),
    (4, date(2026, 10, 13), "CB MARJANE MALL TANGER", -612, "SMS"),
    (1, date(2026, 10, 14), "CB RESTAURANT LE SALON BLEU", -380, "VOCAL"),
]
for s, d, lib, mt, src in non_categorises:
    tx(s, d, lib, mt, None, source=src)

# Les SMS / WhatsApp / vocaux sont catégorisés par l'IA avec un score de confiance
transactions.sort(key=lambda t: (t[5], t[1]))


def q(v):
    if v is None:
        return "NULL"
    if isinstance(v, bool):
        return "TRUE" if v else "FALSE"
    if isinstance(v, (int, float)):
        return f"{v}"
    if isinstance(v, date):
        return f"'{v.isoformat()}'"
    return "'" + str(v).replace("'", "''") + "'"


lignes = ["-- Données de démo générées par tools/generer_donnees_demo.py — fictives", ""]
for s in STRUCTURES:
    lignes.append(f"INSERT INTO structure (id, nom, type, couleur, ice) VALUES ({q(s[0])}, {q(s[1])}, {q(s[2])}, {q(s[3])}, {q(s[4])});")
for c in COMPTES:
    lignes.append(f"INSERT INTO compte_bancaire (id, structure_id, nom, banque, solde_initial) VALUES ({', '.join(q(x) for x in c)});")
for c in CLIENTS:
    lignes.append(f"INSERT INTO client (id, nom, ville, email, secteur) VALUES ({', '.join(q(x) for x in c[:5])});")
for p in PROJETS:
    lignes.append(f"INSERT INTO projet (id, structure_id, client_id, nom, budget, date_debut, date_fin, statut) VALUES ({', '.join(q(x) for x in p)});")

lignes.append("")
for f in factures:
    statut = "PAYEE" if f[7] else "ENVOYEE"
    lignes.append(
        "INSERT INTO facture (numero, structure_id, client_id, projet_id, objet, date_emission, date_echeance, date_paiement, montant_ht, tva_taux, statut) "
        f"VALUES ({', '.join(q(x) for x in f)}, {q(statut)});")

lignes.append("")
lot = []
for t in transactions:
    compte, structure, projet, cat, client, d, lib, mt, src, inter = t
    par_ia = src in ("SMS", "WHATSAPP", "VOCAL") and cat is not None
    conf = round(random.uniform(0.82, 0.99), 3) if par_ia else None
    lot.append(f"({q(compte)}, {q(structure)}, {q(projet)}, {q(cat)}, {q(client)}, {q(d)}, {q(lib)}, {q(mt)}, {q(src)}, {q(par_ia)}, {q(conf)}, {q(inter)})")
for i in range(0, len(lot), 200):
    lignes.append("INSERT INTO transaction (compte_id, structure_id, projet_id, categorie_id, client_id, date_op, libelle, montant, source, categorie_par_ia, confiance_ia, inter_structure) VALUES")
    lignes.append(",\n".join(lot[i:i + 200]) + ";")

lignes += [
    "",
    "SELECT setval('structure_id_seq', (SELECT MAX(id) FROM structure));",
    "SELECT setval('compte_bancaire_id_seq', (SELECT MAX(id) FROM compte_bancaire));",
    "SELECT setval('client_id_seq', (SELECT MAX(id) FROM client));",
    "SELECT setval('projet_id_seq', (SELECT MAX(id) FROM projet));",
]

SORTIE.write_text("\n".join(lignes) + "\n", encoding="utf-8")

# Petit contrôle : solde minimal par structure
soldes = {c[1]: c[4] for c in COMPTES}
mini = dict(soldes)
for t in transactions:
    soldes[t[1]] += t[7]
    mini[t[1]] = min(mini[t[1]], soldes[t[1]])
print(f"{len(transactions)} mouvements, {len(factures)} factures -> {SORTIE.name}")
for s in STRUCTURES:
    print(f"  {s[1]:<16} solde final {soldes[s[0]]:>12,.0f}   plus bas {mini[s[0]]:>12,.0f}")
