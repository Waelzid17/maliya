-- Maliya — schéma principal
-- Convention : montant > 0 = entrée d'argent, montant < 0 = sortie.

CREATE TABLE structure (
    id          BIGSERIAL PRIMARY KEY,
    nom         VARCHAR(120) NOT NULL,
    type        VARCHAR(20)  NOT NULL CHECK (type IN ('AGENCE','SOCIETE','PROJET','PERSO')),
    devise      VARCHAR(3)   NOT NULL DEFAULT 'MAD',
    couleur     VARCHAR(9)   NOT NULL DEFAULT '#3B5BA9',
    ice         VARCHAR(20),
    created_at  TIMESTAMP    NOT NULL DEFAULT now()
);

CREATE TABLE compte_bancaire (
    id            BIGSERIAL PRIMARY KEY,
    structure_id  BIGINT        NOT NULL REFERENCES structure(id),
    nom           VARCHAR(120)  NOT NULL,
    banque        VARCHAR(80),
    solde_initial NUMERIC(14,2) NOT NULL DEFAULT 0
);

CREATE TABLE categorie (
    id       BIGSERIAL PRIMARY KEY,
    code     VARCHAR(40)  NOT NULL UNIQUE,
    libelle  VARCHAR(80)  NOT NULL,
    sens     VARCHAR(6)   NOT NULL CHECK (sens IN ('ENTREE','SORTIE','MIXTE'))
);

CREATE TABLE client (
    id      BIGSERIAL PRIMARY KEY,
    nom     VARCHAR(120) NOT NULL,
    ville   VARCHAR(80),
    email   VARCHAR(160),
    secteur VARCHAR(80)
);

CREATE TABLE projet (
    id            BIGSERIAL PRIMARY KEY,
    structure_id  BIGINT        NOT NULL REFERENCES structure(id),
    client_id     BIGINT        REFERENCES client(id),
    nom           VARCHAR(120)  NOT NULL,
    budget        NUMERIC(14,2) NOT NULL DEFAULT 0,
    date_debut    DATE          NOT NULL,
    date_fin      DATE,
    statut        VARCHAR(12)   NOT NULL DEFAULT 'EN_COURS' CHECK (statut IN ('EN_COURS','TERMINE','PAUSE'))
);

CREATE TABLE transaction (
    id                BIGSERIAL PRIMARY KEY,
    compte_id         BIGINT        NOT NULL REFERENCES compte_bancaire(id),
    structure_id      BIGINT        NOT NULL REFERENCES structure(id),
    projet_id         BIGINT        REFERENCES projet(id),
    categorie_id      BIGINT        REFERENCES categorie(id),
    client_id         BIGINT        REFERENCES client(id),
    date_op           DATE          NOT NULL,
    libelle           VARCHAR(255)  NOT NULL,
    montant           NUMERIC(14,2) NOT NULL,
    source            VARCHAR(10)   NOT NULL DEFAULT 'MANUEL' CHECK (source IN ('IMPORT','SMS','WHATSAPP','MANUEL','VOCAL')),
    categorie_par_ia  BOOLEAN       NOT NULL DEFAULT FALSE,
    confiance_ia      NUMERIC(4,3),
    inter_structure   BOOLEAN       NOT NULL DEFAULT FALSE,
    created_at        TIMESTAMP     NOT NULL DEFAULT now()
);
CREATE INDEX idx_tx_structure_date ON transaction(structure_id, date_op);
CREATE INDEX idx_tx_categorie      ON transaction(categorie_id);
CREATE INDEX idx_tx_projet         ON transaction(projet_id);

CREATE TABLE facture (
    id             BIGSERIAL PRIMARY KEY,
    numero         VARCHAR(30)   NOT NULL UNIQUE,
    structure_id   BIGINT        NOT NULL REFERENCES structure(id),
    client_id      BIGINT        NOT NULL REFERENCES client(id),
    projet_id      BIGINT        REFERENCES projet(id),
    objet          VARCHAR(200)  NOT NULL,
    date_emission  DATE          NOT NULL,
    date_echeance  DATE          NOT NULL,
    date_paiement  DATE,
    montant_ht     NUMERIC(14,2) NOT NULL,
    tva_taux       NUMERIC(4,2)  NOT NULL DEFAULT 20.00,
    statut         VARCHAR(10)   NOT NULL DEFAULT 'ENVOYEE' CHECK (statut IN ('BROUILLON','ENVOYEE','PAYEE'))
);
CREATE INDEX idx_facture_client ON facture(client_id);

-- Notes écrites par l'IA dans la marge (briefings, alertes, explications)
CREATE TABLE note_ia (
    id            BIGSERIAL PRIMARY KEY,
    structure_id  BIGINT       REFERENCES structure(id),
    genre         VARCHAR(20)  NOT NULL,
    titre         VARCHAR(200) NOT NULL,
    contenu       TEXT         NOT NULL,
    gravite       VARCHAR(10)  NOT NULL DEFAULT 'INFO' CHECK (gravite IN ('INFO','ATTENTION','URGENT')),
    lue           BOOLEAN      NOT NULL DEFAULT FALSE,
    created_at    TIMESTAMP    NOT NULL DEFAULT now()
);

-- Vue pratique : facture TTC et retard
CREATE VIEW v_facture AS
SELECT f.*,
       ROUND(f.montant_ht * (1 + f.tva_taux / 100), 2) AS montant_ttc,
       CASE WHEN f.date_paiement IS NOT NULL THEN f.date_paiement - f.date_echeance
            ELSE CURRENT_DATE - f.date_echeance END AS jours_retard
FROM facture f;
