"""Accès lecture seule au grand livre. L'IA lit les chiffres ici, elle ne les invente jamais."""
import os
from decimal import Decimal

import pandas as pd
import psycopg2

DSN = os.getenv("DATABASE_URL", "postgresql://maliya:maliya@localhost:5432/maliya")


def query(sql: str, params=None) -> pd.DataFrame:
    with psycopg2.connect(DSN) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            cols = [d[0] for d in cur.description]
            rows = [[float(v) if isinstance(v, Decimal) else v for v in r] for r in cur.fetchall()]
    df = pd.DataFrame(rows, columns=cols)
    for c in df.columns:
        if c.startswith("date") and len(df):
            df[c] = pd.to_datetime(df[c])
    return df


def transactions() -> pd.DataFrame:
    return query("""
        SELECT t.id, t.structure_id, s.nom AS structure, t.projet_id, t.categorie_id,
               c.code AS cat_code, c.libelle AS cat_libelle, t.client_id, t.date_op,
               t.libelle, t.montant, t.source, t.inter_structure
        FROM transaction t
        JOIN structure s ON s.id = t.structure_id
        LEFT JOIN categorie c ON c.id = t.categorie_id
        ORDER BY t.date_op, t.id
    """)


def factures() -> pd.DataFrame:
    return query("""
        SELECT f.id, f.numero, f.structure_id, f.client_id, cl.nom AS client, f.projet_id, f.objet,
               f.date_emission, f.date_echeance, f.date_paiement, f.montant_ht, f.montant_ttc,
               f.jours_retard, f.statut
        FROM v_facture f JOIN client cl ON cl.id = f.client_id
        ORDER BY f.date_emission
    """)


def structures() -> pd.DataFrame:
    return query("""
        SELECT s.id, s.nom, s.type, s.couleur,
               COALESCE((SELECT SUM(solde_initial) FROM compte_bancaire c WHERE c.structure_id = s.id), 0)
             + COALESCE((SELECT SUM(montant) FROM transaction t WHERE t.structure_id = s.id), 0) AS solde
        FROM structure s ORDER BY s.id
    """)


def categories() -> pd.DataFrame:
    return query("SELECT id, code, libelle, sens FROM categorie ORDER BY id")


def clients() -> pd.DataFrame:
    return query("SELECT id, nom, ville, secteur FROM client ORDER BY id")


def projets() -> pd.DataFrame:
    return query("""
        SELECT p.id, p.nom, p.structure_id, p.client_id, p.budget, p.statut, p.date_debut,
               COALESCE(SUM(CASE WHEN t.montant < 0 THEN -t.montant END), 0) AS cout_reel,
               COALESCE(SUM(CASE WHEN t.montant > 0 THEN t.montant END), 0) AS encaisse
        FROM projet p LEFT JOIN transaction t ON t.projet_id = p.id
        GROUP BY p.id ORDER BY p.id
    """)


def soldes_initiaux() -> dict:
    df = query("SELECT structure_id, SUM(solde_initial) AS s FROM compte_bancaire GROUP BY structure_id")
    return dict(zip(df.structure_id, df.s))


def filtrer(tx: pd.DataFrame, structure_id):
    """Une structure précise, ou la vue consolidée (sans les virements internes qui s'annulent)."""
    if structure_id:
        return tx[tx.structure_id == int(structure_id)]
    return tx[~tx.inter_structure]
