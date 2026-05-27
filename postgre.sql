-- ============================================================
-- BASE DE DONNÉES POSTGRESQL – SYSTÈME DE GESTION DES TONTINES
-- ============================================================

-- Extension UUID
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ── 1. MEMBRES ──────────────────────────────────────────────
CREATE TABLE membres (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    nom VARCHAR(100) NOT NULL,
    prenom VARCHAR(100) NOT NULL,
    age INTEGER,
    ville VARCHAR(150),
    telephone VARCHAR(30) UNIQUE NOT NULL,
    numero_cni VARCHAR(100),
    photo_url TEXT,
    password TEXT,
    est_fondateur BOOLEAN DEFAULT FALSE,

    statut VARCHAR(20) DEFAULT 'EN_ATTENTE'
        CHECK (statut IN ('EN_ATTENTE','ACTIF','SUSPENDU','REFUSE','ARCHIVE')),

    lot_souhaite TEXT,
    mobile_money VARCHAR(30),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Fondateur par défaut
INSERT INTO membres (
    id,
    nom,
    prenom,
    telephone,
    password,
    est_fondateur,
    statut
)
VALUES (
    '11111111-1111-1111-1111-111111111111',
    'Admin',
    'Tontine',
    '690000000',
    '$2b$12$hashed_admin1234',
    TRUE,
    'ACTIF'
)
ON CONFLICT (telephone) DO NOTHING;

-- ── 2. TONTINES ─────────────────────────────────────────────
CREATE TABLE tontines (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    nom VARCHAR(150) NOT NULL,
    description TEXT,

    frequence VARCHAR(30) DEFAULT 'HEBDOMADAIRE'
        CHECK(frequence IN ('HEBDOMADAIRE','MENSUELLE','BIMENSUELLE')),

    jour_semaine VARCHAR(20),

    heure_debut TIME NOT NULL,
    heure_fin TIME NOT NULL,

    date_debut DATE NOT NULL,

    reglement TEXT,

    statut VARCHAR(20) DEFAULT 'ACTIVE'
        CHECK(statut IN ('ACTIVE','SUSPENDUE','CLOTUREE')),

    fondateur_id UUID NOT NULL,

    nb_max_membres INTEGER DEFAULT 30,
    montant_sention NUMERIC(10,2) DEFAULT 500,
    delai_grace_h INTEGER DEFAULT 24,
    delai_echange_h INTEGER DEFAULT 48,
    quorum_vote INTEGER DEFAULT 50,
    duree_vote_h INTEGER DEFAULT 72,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (fondateur_id) REFERENCES membres(id)
);

-- ── 3. LOTS ─────────────────────────────────────────────────
CREATE TABLE lots (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    tontine_id UUID NOT NULL,

    nom VARCHAR(150) NOT NULL,

    montant_cotisation NUMERIC(10,2) NOT NULL,

    nb_max_membres INTEGER DEFAULT 30,
    cycle_actuel INTEGER DEFAULT 1,

    option_integration VARCHAR(20) DEFAULT 'ANTICIPEE'
        CHECK(option_integration IN ('ANTICIPEE','DEDUCTION')),

    statut VARCHAR(20) DEFAULT 'ACTIF'
        CHECK(statut IN ('ACTIF','CLOS','SUSPENDU')),

    prochain_bouffeur_id UUID,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (tontine_id) REFERENCES tontines(id),
    FOREIGN KEY (prochain_bouffeur_id) REFERENCES membres(id)
);

-- ── 4. ADHÉSIONS LOT ────────────────────────────────────────
CREATE TABLE adhesions_lot (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    membre_id UUID NOT NULL,
    lot_id UUID NOT NULL,

    numero_tirage INTEGER,

    a_bouffe BOOLEAN DEFAULT FALSE,

    date_bouffement TIMESTAMP,

    statut VARCHAR(20) DEFAULT 'ACTIF'
        CHECK(statut IN ('ACTIF','SUSPENDU','EXCLU')),

    membres_passes INTEGER DEFAULT 0,

    date_adhesion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (membre_id) REFERENCES membres(id),
    FOREIGN KEY (lot_id) REFERENCES lots(id),

    UNIQUE(membre_id, lot_id)
);

-- ── 5. SÉANCES ──────────────────────────────────────────────
CREATE TABLE seances (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    tontine_id UUID NOT NULL,
    lot_id UUID NOT NULL,

    date_seance DATE NOT NULL,

    heure_ouverture TIME NOT NULL,
    heure_cloture TIME NOT NULL,

    statut VARCHAR(20) DEFAULT 'PLANIFIEE'
        CHECK(statut IN ('PLANIFIEE','OUVERTE','CLOTUREE')),

    bouffeur_id UUID,

    montant_pot NUMERIC(10,2),

    pv_url TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (tontine_id) REFERENCES tontines(id),
    FOREIGN KEY (lot_id) REFERENCES lots(id),
    FOREIGN KEY (bouffeur_id) REFERENCES membres(id)
);

-- ── 6. PAIEMENTS ────────────────────────────────────────────
CREATE TABLE paiements (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    membre_id UUID NOT NULL,
    seance_id UUID NOT NULL,
    lot_id UUID NOT NULL,

    montant_lot NUMERIC(10,2) NOT NULL,
    montant_sention NUMERIC(10,2) DEFAULT 0,
    montant_total NUMERIC(10,2) NOT NULL,

    heure_envoi TIMESTAMP NOT NULL,

    retard BOOLEAN DEFAULT FALSE,

    mode_paiement VARCHAR(20) DEFAULT 'MOBILE_MONEY'
        CHECK(mode_paiement IN ('MOBILE_MONEY','ESPECES','MTN','ORANGE')),

    reference_transaction TEXT,

    statut VARCHAR(20) DEFAULT 'EN_ATTENTE'
        CHECK(statut IN ('EN_ATTENTE','VALIDE','REJETE','REMBOURSE')),

    motif_rejet TEXT,

    confirme_par UUID,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (membre_id) REFERENCES membres(id),
    FOREIGN KEY (seance_id) REFERENCES seances(id),
    FOREIGN KEY (lot_id) REFERENCES lots(id)
);

-- ── 7. COMPTES ──────────────────────────────────────────────
CREATE TABLE comptes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    tontine_id UUID NOT NULL,
    lot_id UUID,

    type_compte VARCHAR(20) NOT NULL
        CHECK(type_compte IN ('TONTINE','EPARGNE','SENTION')),

    solde NUMERIC(10,2) DEFAULT 0,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (tontine_id) REFERENCES tontines(id),
    FOREIGN KEY (lot_id) REFERENCES lots(id)
);

-- ── 8. TRANSACTIONS ─────────────────────────────────────────
CREATE TABLE transactions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    compte_id UUID NOT NULL,
    membre_id UUID,

    type_operation VARCHAR(50) NOT NULL
        CHECK(type_operation IN (
            'COTISATION',
            'SENTION',
            'BOUFFEMENT',
            'EPARGNE_DEPOT',
            'EPARGNE_RETRAIT',
            'PRET_DECAISSEMENT',
            'PRET_REMBOURSEMENT',
            'AIDE_SENTION',
            'CASSATION',
            'INTERET'
        )),

    montant NUMERIC(10,2) NOT NULL,

    sens VARCHAR(10)
        CHECK(sens IN ('CREDIT','DEBIT')),

    reference TEXT,
    description TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (compte_id) REFERENCES comptes(id),
    FOREIGN KEY (membre_id) REFERENCES membres(id)
);

-- ── 9. ÉPARGNES ─────────────────────────────────────────────
CREATE TABLE epargnes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    membre_id UUID NOT NULL,
    tontine_id UUID NOT NULL,

    solde NUMERIC(10,2) DEFAULT 0,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (membre_id) REFERENCES membres(id),
    FOREIGN KEY (tontine_id) REFERENCES tontines(id),

    UNIQUE(membre_id, tontine_id)
);

-- ── 10. PRÊTS ───────────────────────────────────────────────
CREATE TABLE prets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    emprunteur_id UUID NOT NULL,
    tontine_id UUID NOT NULL,

    montant NUMERIC(10,2) NOT NULL,

    taux_interet NUMERIC(5,2) DEFAULT 5.0,

    penalite_retard NUMERIC(10,2) DEFAULT 1000,

    montant_total_du NUMERIC(10,2),

    montant_rembourse NUMERIC(10,2) DEFAULT 0,

    date_debut DATE,

    date_echeance DATE NOT NULL,

    motif TEXT,

    statut VARCHAR(20) DEFAULT 'EN_ATTENTE'
        CHECK(statut IN (
            'EN_ATTENTE',
            'APPROUVE',
            'REFUSE',
            'EN_COURS',
            'REMBOURSE',
            'DEFAUT'
        )),

    nb_relances INTEGER DEFAULT 0,

    valide_par UUID,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (emprunteur_id) REFERENCES membres(id),
    FOREIGN KEY (tontine_id) REFERENCES tontines(id),
    FOREIGN KEY (valide_par) REFERENCES membres(id)
);

-- ── 11. REMBOURSEMENTS ──────────────────────────────────────
CREATE TABLE remboursements (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    pret_id UUID NOT NULL,

    montant NUMERIC(10,2) NOT NULL,

    date_paiement TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    type_remboursement VARCHAR(20) DEFAULT 'PARTIEL'
        CHECK(type_remboursement IN ('PARTIEL','TOTAL')),

    FOREIGN KEY (pret_id) REFERENCES prets(id)
);

-- ── INDEX ───────────────────────────────────────────────────
CREATE INDEX idx_paiements_membre ON paiements(membre_id);
CREATE INDEX idx_paiements_seance ON paiements(seance_id);
CREATE INDEX idx_adhesions_lot ON adhesions_lot(lot_id);
CREATE INDEX idx_adhesions_membre ON adhesions_lot(membre_id);
CREATE INDEX idx_transactions_compte ON transactions(compte_id);
CREATE INDEX idx_seances_tontine ON seances(tontine_id);