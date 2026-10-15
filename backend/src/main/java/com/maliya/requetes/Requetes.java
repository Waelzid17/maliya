package com.maliya.requetes;

/**
 * Toutes les requêtes de lecture du backend, en SQL explicite.
 * Écritures : JPA (entités). Lectures et agrégats : SQL, plus lisible et plus rapide.
 *
 * Conventions :
 *  - :sid    = structure choisie, ou NULL pour la vue consolidée (virements internes exclus)
 *  - :ref    = date de référence (aujourd'hui, ou la date figée du mode démo)
 *  - les alias entre guillemets donnent directement les noms JSON en camelCase
 */
public final class Requetes {

    private Requetes() {
    }

    public static final String SOLDES = """
            SELECT s.id, s.nom, s.type, s.couleur,
                   COALESCE((SELECT SUM(c.solde_initial) FROM compte_bancaire c WHERE c.structure_id = s.id), 0)
                 + COALESCE((SELECT SUM(t.montant) FROM transaction t WHERE t.structure_id = s.id), 0) AS solde,
                   (SELECT COUNT(*) FROM transaction t WHERE t.structure_id = s.id AND t.categorie_id IS NULL) AS "aClasser"
            FROM structure s
            ORDER BY s.id
            """;

    public static final String FLUX_PERIODE = """
            SELECT COALESCE(SUM(t.montant) FILTER (WHERE t.montant > 0), 0) AS entrees,
                   COALESCE(SUM(-t.montant) FILTER (WHERE t.montant < 0), 0) AS sorties
            FROM transaction t
            WHERE t.date_op >= CAST(:debut AS DATE) AND t.date_op <= CAST(:fin AS DATE)
              AND (CAST(:sid AS BIGINT) IS NULL OR t.structure_id = CAST(:sid AS BIGINT))
              AND (CAST(:sid AS BIGINT) IS NOT NULL OR NOT t.inter_structure)
            """;

    public static final String SERIE_MENSUELLE = """
            WITH mois AS (
                SELECT generate_series(date_trunc('month', CAST(:ref AS DATE)) - INTERVAL '11 months',
                                       date_trunc('month', CAST(:ref AS DATE)), INTERVAL '1 month')::date AS m
            ), flux AS (
                SELECT date_trunc('month', t.date_op)::date AS m,
                       SUM(t.montant) FILTER (WHERE t.montant > 0) AS entrees,
                       SUM(-t.montant) FILTER (WHERE t.montant < 0) AS sorties,
                       SUM(t.montant) AS net
                FROM transaction t
                WHERE (CAST(:sid AS BIGINT) IS NULL OR t.structure_id = CAST(:sid AS BIGINT))
                  AND (CAST(:sid AS BIGINT) IS NOT NULL OR NOT t.inter_structure)
                GROUP BY 1
            ), initial AS (
                SELECT COALESCE(SUM(solde_initial), 0) AS v FROM compte_bancaire
                WHERE CAST(:sid AS BIGINT) IS NULL OR structure_id = CAST(:sid AS BIGINT)
            )
            SELECT to_char(mo.m, 'YYYY-MM') AS mois,
                   COALESCE(f.entrees, 0) AS entrees,
                   COALESCE(f.sorties, 0) AS sorties,
                   (SELECT v FROM initial) + COALESCE((SELECT SUM(f2.net) FROM flux f2 WHERE f2.m <= mo.m), 0) AS "soldeFin"
            FROM mois mo LEFT JOIN flux f ON f.m = mo.m
            ORDER BY mo.m
            """;

    public static final String DEPENSES_PAR_CATEGORIE = """
            SELECT COALESCE(c.libelle, 'Non catégorisé') AS categorie, c.code, SUM(-t.montant) AS montant
            FROM transaction t LEFT JOIN categorie c ON c.id = t.categorie_id
            WHERE t.montant < 0 AND NOT t.inter_structure
              AND t.date_op >= CAST(:debut AS DATE) AND t.date_op <= CAST(:fin AS DATE)
              AND (CAST(:sid AS BIGINT) IS NULL OR t.structure_id = CAST(:sid AS BIGINT))
            GROUP BY 1, 2
            ORDER BY 3 DESC
            """;

    public static final String FACTURES_RESUME = """
            SELECT COALESCE(SUM(ROUND(f.montant_ht * (1 + f.tva_taux / 100), 2)), 0) AS "aEncaisser",
                   COALESCE(SUM(ROUND(f.montant_ht * (1 + f.tva_taux / 100), 2))
                            FILTER (WHERE f.date_echeance < CAST(:ref AS DATE)), 0) AS "enRetard",
                   COUNT(*) FILTER (WHERE f.date_echeance < CAST(:ref AS DATE)) AS "nbEnRetard",
                   COUNT(*) AS "nbOuvertes"
            FROM facture f
            WHERE f.date_paiement IS NULL
              AND (CAST(:sid AS BIGINT) IS NULL OR f.structure_id = CAST(:sid AS BIGINT))
            """;

    public static final String SORTIES_MOYENNES_3_MOIS = """
            SELECT COALESCE(SUM(-t.montant), 0) / 3 AS moyenne
            FROM transaction t
            WHERE t.montant < 0
              AND t.date_op >= date_trunc('month', CAST(:ref AS DATE)) - INTERVAL '3 months'
              AND t.date_op < date_trunc('month', CAST(:ref AS DATE))
              AND (CAST(:sid AS BIGINT) IS NULL OR t.structure_id = CAST(:sid AS BIGINT))
              AND (CAST(:sid AS BIGINT) IS NOT NULL OR NOT t.inter_structure)
            """;

    private static final String MOUVEMENTS_FILTRE = """
            FROM transaction t
            JOIN structure s ON s.id = t.structure_id
            LEFT JOIN categorie c ON c.id = t.categorie_id
            LEFT JOIN projet p ON p.id = t.projet_id
            WHERE (CAST(:sid AS BIGINT) IS NULL OR t.structure_id = CAST(:sid AS BIGINT))
              AND (CAST(:cat AS BIGINT) IS NULL OR t.categorie_id = CAST(:cat AS BIGINT))
              AND (CAST(:aClasser AS BOOLEAN) = FALSE OR t.categorie_id IS NULL)
              AND (CAST(:q AS TEXT) IS NULL OR t.libelle ILIKE '%' || CAST(:q AS TEXT) || '%'
                   OR c.libelle ILIKE '%' || CAST(:q AS TEXT) || '%' OR p.nom ILIKE '%' || CAST(:q AS TEXT) || '%')
            """;

    public static final String MOUVEMENTS = """
            SELECT t.id, t.date_op::text AS "date", t.libelle, t.montant, t.source,
                   t.structure_id AS "structureId", s.nom AS structure, s.couleur,
                   t.categorie_id AS "categorieId", c.libelle AS categorie, c.code AS "categorieCode",
                   t.projet_id AS "projetId", p.nom AS projet,
                   t.categorie_par_ia AS "categorieParIa", t.confiance_ia AS "confianceIa",
                   t.inter_structure AS "interStructure"
            """ + MOUVEMENTS_FILTRE + """
            ORDER BY t.date_op DESC, t.id DESC
            LIMIT :taille OFFSET :decalage
            """;

    public static final String MOUVEMENTS_TOTAL = "SELECT COUNT(*) " + MOUVEMENTS_FILTRE;

    public static final String MOUVEMENT_PAR_ID = """
            SELECT t.id, t.date_op::text AS "date", t.libelle, t.montant, t.source,
                   t.structure_id AS "structureId", s.nom AS structure, s.couleur,
                   t.categorie_id AS "categorieId", c.libelle AS categorie, c.code AS "categorieCode",
                   t.projet_id AS "projetId", p.nom AS projet,
                   t.categorie_par_ia AS "categorieParIa", t.confiance_ia AS "confianceIa",
                   t.inter_structure AS "interStructure"
            FROM transaction t
            JOIN structure s ON s.id = t.structure_id
            LEFT JOIN categorie c ON c.id = t.categorie_id
            LEFT JOIN projet p ON p.id = t.projet_id
            WHERE t.id = :id
            """;

    public static final String FACTURES = """
            SELECT f.id, f.numero, f.objet, f.statut,
                   f.structure_id AS "structureId", s.nom AS structure, s.couleur,
                   f.client_id AS "clientId", cl.nom AS client,
                   f.projet_id AS "projetId", p.nom AS projet,
                   f.date_emission::text AS "dateEmission", f.date_echeance::text AS "dateEcheance",
                   f.date_paiement::text AS "datePaiement",
                   f.montant_ht AS "montantHt", f.tva_taux AS "tvaTaux",
                   ROUND(f.montant_ht * (1 + f.tva_taux / 100), 2) AS "montantTtc",
                   CASE WHEN f.date_paiement IS NULL THEN CAST(:ref AS DATE) - f.date_echeance END AS "joursDepasses"
            FROM facture f
            JOIN structure s ON s.id = f.structure_id
            JOIN client cl ON cl.id = f.client_id
            LEFT JOIN projet p ON p.id = f.projet_id
            WHERE (CAST(:sid AS BIGINT) IS NULL OR f.structure_id = CAST(:sid AS BIGINT))
              AND (CAST(:etat AS TEXT) IS NULL
                   OR (CAST(:etat AS TEXT) = 'OUVERTES' AND f.date_paiement IS NULL)
                   OR (CAST(:etat AS TEXT) = 'PAYEES' AND f.date_paiement IS NOT NULL))
            ORDER BY (f.date_paiement IS NULL) DESC,
                     CASE WHEN f.date_paiement IS NULL THEN f.date_echeance END ASC,
                     f.date_paiement DESC, f.id DESC
            LIMIT 200
            """;

    public static final String PROJETS = """
            SELECT p.id, p.nom, p.statut, p.budget,
                   p.structure_id AS "structureId", s.nom AS structure, s.couleur,
                   p.client_id AS "clientId", cl.nom AS client,
                   p.date_debut::text AS "dateDebut", p.date_fin::text AS "dateFin",
                   COALESCE(c.cout, 0) AS "coutReel",
                   COALESCE(c.rythme, 0) AS "rythmeMensuel",
                   COALESCE(f.ht, 0) AS "factureHt",
                   COALESCE(f.encaisse, 0) AS "encaisseHt"
            FROM projet p
            JOIN structure s ON s.id = p.structure_id
            LEFT JOIN client cl ON cl.id = p.client_id
            LEFT JOIN (
                SELECT projet_id, SUM(-montant) AS cout,
                       COALESCE(SUM(-montant) FILTER (WHERE date_op >= CAST(:ref AS DATE) - INTERVAL '3 months'), 0) / 3 AS rythme
                FROM transaction WHERE montant < 0 AND projet_id IS NOT NULL GROUP BY projet_id
            ) c ON c.projet_id = p.id
            LEFT JOIN (
                SELECT projet_id, SUM(montant_ht) AS ht,
                       COALESCE(SUM(montant_ht) FILTER (WHERE date_paiement IS NOT NULL), 0) AS encaisse
                FROM facture WHERE projet_id IS NOT NULL GROUP BY projet_id
            ) f ON f.projet_id = p.id
            WHERE CAST(:sid AS BIGINT) IS NULL OR p.structure_id = CAST(:sid AS BIGINT)
            ORDER BY CASE p.statut WHEN 'EN_COURS' THEN 0 WHEN 'PAUSE' THEN 1 ELSE 2 END, p.id
            """;

    public static final String CATEGORIES = "SELECT id, code, libelle, sens FROM categorie ORDER BY libelle";

    public static final String CLIENTS = "SELECT id, nom, ville, secteur, email FROM client ORDER BY nom";

    public static final String COMPTE_PRINCIPAL = "SELECT id FROM compte_bancaire WHERE structure_id = :sid ORDER BY id LIMIT 1";

    public static final String CATEGORIE_PAR_CODE = "SELECT id FROM categorie WHERE code = :code";

    public static final String DERNIER_NUMERO = """
            SELECT numero FROM facture WHERE structure_id = :sid ORDER BY id DESC LIMIT 1
            """;

    public static final String NUMERO_EXISTE = "SELECT COUNT(*) FROM facture WHERE numero = :numero";
}
