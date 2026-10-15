-- Catégories : référentiel commun, présent même sans les données de démo.
-- Les ids sont fixes : le service IA et les données de démo s'appuient sur les codes.

INSERT INTO categorie (id, code, libelle, sens) VALUES
    (1, 'REV_CLIENT', 'Revenus clients', 'ENTREE'),
    (2, 'SALAIRES', 'Salaires', 'SORTIE'),
    (3, 'FREELANCE', 'Freelances', 'SORTIE'),
    (4, 'LOYER', 'Loyer & bureaux', 'SORTIE'),
    (5, 'CLOUD', 'Hébergement & cloud', 'SORTIE'),
    (6, 'LOGICIELS', 'Logiciels & abonnements', 'SORTIE'),
    (7, 'MARKETING', 'Marketing', 'SORTIE'),
    (8, 'DEPLACEMENT', 'Déplacements', 'SORTIE'),
    (9, 'MATERIEL', 'Matériel', 'SORTIE'),
    (10, 'IMPOTS', 'Impôts & TVA', 'SORTIE'),
    (11, 'CNSS', 'Charges sociales', 'SORTIE'),
    (12, 'BANQUE', 'Frais bancaires', 'SORTIE'),
    (13, 'REPAS', 'Repas & cafés', 'SORTIE'),
    (14, 'TELECOM', 'Téléphone & internet', 'SORTIE'),
    (15, 'TRANSFERT', 'Transferts internes', 'MIXTE'),
    (16, 'COURSES', 'Courses & maison', 'SORTIE'),
    (17, 'LOISIRS', 'Loisirs', 'SORTIE');
SELECT setval('categorie_id_seq', (SELECT MAX(id) FROM categorie));
