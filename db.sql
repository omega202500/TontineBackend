-- ============================================================
-- BASE DE DONNÉES COMPLÈTE – SYSTÈME DE GESTION DES TONTINES
-- ============================================================

-- ── 1. MEMBRES ──────────────────────────────────────────────
CREATE TABLE membres (
    id              TEXT PRIMARY KEY,
    nom             TEXT NOT NULL,
    prenom          TEXT NOT NULL,
    age             INTEGER,
    ville           TEXT,
    telephone       TEXT UNIQUE NOT NULL,
    numero_cni      TEXT,
    photo_url       TEXT,
    password        TEXT,
    est_fondateur   BOOLEAN DEFAULT FALSE,
    statut          TEXT DEFAULT 'EN_ATTENTE'
                    CHECK(statut IN ('EN_ATTENTE','ACTIF','SUSPENDU','REFUSE','ARCHIVE')),
    lot_souhaite    TEXT,
    mobile_money    TEXT,         -- numéro MTN/Orange Money
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Fondateur par défaut
INSERT OR IGNORE INTO membres (id, nom, prenom, telephone, password, est_fondateur, statut)
VALUES ('fondateur-001', 'Admin', 'Tontine', '690000000',
        '$2b$12$hashed_admin1234', TRUE, 'ACTIF');

-- ── 2. TONTINES ─────────────────────────────────────────────
CREATE TABLE tontines (
    id                  TEXT PRIMARY KEY,
    nom                 TEXT NOT NULL,
    description         TEXT,
    frequence           TEXT DEFAULT 'HEBDOMADAIRE'
                        CHECK(frequence IN ('HEBDOMADAIRE','MENSUELLE','BIMENSUELLE')),
    jour_semaine        TEXT,             -- ex: LUNDI
    heure_debut         TIME NOT NULL,    -- ex: 08:00
    heure_fin           TIME NOT NULL,    -- ex: 18:00
    date_debut          DATE NOT NULL,
    reglement           TEXT,
    statut              TEXT DEFAULT 'ACTIVE'
                        CHECK(statut IN ('ACTIVE','SUSPENDUE','CLOTUREE')),
    fondateur_id        TEXT NOT NULL,
    nb_max_membres      INTEGER DEFAULT 30,
    montant_sention     DECIMAL(10,2) DEFAULT 500,
    delai_grace_h       INTEGER DEFAULT 24,  -- heures
    delai_echange_h     INTEGER DEFAULT 48,  -- heures avant séance
    quorum_vote         INTEGER DEFAULT 50,  -- % minimum
    duree_vote_h        INTEGER DEFAULT 72,  -- heures
    created_at          DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (fondateur_id) REFERENCES membres(id)
);

-- ── 3. LOTS ─────────────────────────────────────────────────
CREATE TABLE lots (
    id                  TEXT PRIMARY KEY,
    tontine_id          TEXT NOT NULL,
    nom                 TEXT NOT NULL,           -- ex: "Lot 5000"
    montant_cotisation  DECIMAL(10,2) NOT NULL,
    nb_max_membres      INTEGER DEFAULT 30,
    cycle_actuel        INTEGER DEFAULT 1,
    option_integration  TEXT DEFAULT 'ANTICIPEE'
                        CHECK(option_integration IN ('ANTICIPEE','DEDUCTION')),
    statut              TEXT DEFAULT 'ACTIF'
                        CHECK(statut IN ('ACTIF','CLOS','SUSPENDU')),
    prochain_bouffeur_id TEXT,
    created_at          DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (tontine_id) REFERENCES tontines(id),
    FOREIGN KEY (prochain_bouffeur_id) REFERENCES membres(id)
);

-- ── 4. ADHÉSIONS LOT ────────────────────────────────────────
CREATE TABLE adhesions_lot (
    id                  TEXT PRIMARY KEY,
    membre_id           TEXT NOT NULL,
    lot_id              TEXT NOT NULL,
    numero_tirage       INTEGER,             -- rang de bouffement
    a_bouffe            BOOLEAN DEFAULT FALSE,
    date_bouffement     DATETIME,
    statut              TEXT DEFAULT 'ACTIF'
                        CHECK(statut IN ('ACTIF','SUSPENDU','EXCLU')),
    membres_passes      INTEGER DEFAULT 0,   -- nb membres ayant bouffé avant intégration
    date_adhesion       DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (membre_id) REFERENCES membres(id),
    FOREIGN KEY (lot_id) REFERENCES lots(id),
    UNIQUE(membre_id, lot_id)
);

-- ── 5. SÉANCES ──────────────────────────────────────────────
CREATE TABLE seances (
    id              TEXT PRIMARY KEY,
    tontine_id      TEXT NOT NULL,
    lot_id          TEXT NOT NULL,
    date_seance     DATE NOT NULL,
    heure_ouverture TIME NOT NULL,
    heure_cloture   TIME NOT NULL,
    statut          TEXT DEFAULT 'PLANIFIEE'
                    CHECK(statut IN ('PLANIFIEE','OUVERTE','CLOTUREE')),
    bouffeur_id     TEXT,
    montant_pot     DECIMAL(10,2),
    pv_url          TEXT,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (tontine_id) REFERENCES tontines(id),
    FOREIGN KEY (lot_id) REFERENCES lots(id),
    FOREIGN KEY (bouffeur_id) REFERENCES membres(id)
);

-- ── 6. PAIEMENTS ────────────────────────────────────────────
CREATE TABLE paiements (
    id                  TEXT PRIMARY KEY,
    membre_id           TEXT NOT NULL,
    seance_id           TEXT NOT NULL,
    lot_id              TEXT NOT NULL,
    montant_lot         DECIMAL(10,2) NOT NULL,
    montant_sention     DECIMAL(10,2) DEFAULT 0,
    montant_total       DECIMAL(10,2) NOT NULL,
    heure_envoi         DATETIME NOT NULL,
    retard              BOOLEAN DEFAULT FALSE,
    mode_paiement       TEXT DEFAULT 'MOBILE_MONEY'
                        CHECK(mode_paiement IN ('MOBILE_MONEY','ESPECES','MTN','ORANGE')),
    reference_transaction TEXT,
    statut              TEXT DEFAULT 'EN_ATTENTE'
                        CHECK(statut IN ('EN_ATTENTE','VALIDE','REJETE','REMBOURSE')),
    motif_rejet         TEXT,
    confirme_par        TEXT,   -- trésorier si espèces
    created_at          DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (membre_id) REFERENCES membres(id),
    FOREIGN KEY (seance_id) REFERENCES seances(id),
    FOREIGN KEY (lot_id) REFERENCES lots(id)
);

-- ── 7. COMPTES ──────────────────────────────────────────────
CREATE TABLE comptes (
    id              TEXT PRIMARY KEY,
    tontine_id      TEXT NOT NULL,
    lot_id          TEXT,           -- NULL si compte global tontine
    type_compte     TEXT NOT NULL
                    CHECK(type_compte IN ('TONTINE','EPARGNE','SENTION')),
    solde           DECIMAL(10,2) DEFAULT 0,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (tontine_id) REFERENCES tontines(id),
    FOREIGN KEY (lot_id) REFERENCES lots(id)
);

-- ── 8. TRANSACTIONS COMPTES ─────────────────────────────────
CREATE TABLE transactions (
    id              TEXT PRIMARY KEY,
    compte_id       TEXT NOT NULL,
    membre_id       TEXT,
    type_operation  TEXT NOT NULL
                    CHECK(type_operation IN (
                        'COTISATION','SENTION','BOUFFEMENT',
                        'EPARGNE_DEPOT','EPARGNE_RETRAIT',
                        'PRET_DECAISSEMENT','PRET_REMBOURSEMENT',
                        'AIDE_SENTION','CASSATION','INTERET'
                    )),
    montant         DECIMAL(10,2) NOT NULL,
    sens            TEXT CHECK(sens IN ('CREDIT','DEBIT')),
    reference       TEXT,
    description     TEXT,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (compte_id) REFERENCES comptes(id),
    FOREIGN KEY (membre_id) REFERENCES membres(id)
);

-- ── 9. ÉPARGNES ─────────────────────────────────────────────
CREATE TABLE epargnes (
    id              TEXT PRIMARY KEY,
    membre_id       TEXT NOT NULL,
    tontine_id      TEXT NOT NULL,
    solde           DECIMAL(10,2) DEFAULT 0,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (membre_id) REFERENCES membres(id),
    FOREIGN KEY (tontine_id) REFERENCES tontines(id),
    UNIQUE(membre_id, tontine_id)
);

-- ── 10. PRÊTS ───────────────────────────────────────────────
CREATE TABLE prets (
    id                  TEXT PRIMARY KEY,
    emprunteur_id       TEXT NOT NULL,
    tontine_id          TEXT NOT NULL,
    montant             DECIMAL(10,2) NOT NULL,
    taux_interet        DECIMAL(5,2) DEFAULT 5.0,   -- % par mois
    penalite_retard     DECIMAL(10,2) DEFAULT 1000, -- FCFA/jour
    montant_total_du    DECIMAL(10,2),
    montant_rembourse   DECIMAL(10,2) DEFAULT 0,
    date_debut          DATE,
    date_echeance       DATE NOT NULL,
    motif               TEXT,
    statut              TEXT DEFAULT 'EN_ATTENTE'
                        CHECK(statut IN (
                            'EN_ATTENTE','APPROUVE','REFUSE',
                            'EN_COURS','REMBOURSE','DEFAUT'
                        )),
    nb_relances         INTEGER DEFAULT 0,
    valide_par          TEXT,
    created_at          DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (emprunteur_id) REFERENCES membres(id),
    FOREIGN KEY (tontine_id) REFERENCES tontines(id),
    FOREIGN KEY (valide_par) REFERENCES membres(id)
);

-- ── 11. REMBOURSEMENTS PRÊTS ────────────────────────────────
CREATE TABLE remboursements (
    id              TEXT PRIMARY KEY,
    pret_id         TEXT NOT NULL,
    montant         DECIMAL(10,2) NOT NULL,
    date_paiement   DATETIME DEFAULT CURRENT_TIMESTAMP,
    type_remboursement TEXT DEFAULT 'PARTIEL'
                    CHECK(type_remboursement IN ('PARTIEL','TOTAL')),
    FOREIGN KEY (pret_id) REFERENCES prets(id)
);

-- ── 12. CASSATIONS ──────────────────────────────────────────
CREATE TABLE cassations (
    id                  TEXT PRIMARY KEY,
    tontine_id          TEXT NOT NULL,
    type_cassation      TEXT NOT NULL
                        CHECK(type_cassation IN (
                            'VACANCES_SCOLAIRES',
                            'RENTREE_SCOLAIRE',
                            'FETES_FIN_ANNEE'
                        )),
    montant_total       DECIMAL(10,2),
    montant_par_membre  DECIMAL(10,2),
    date_distribution   DATE NOT NULL,
    statut              TEXT DEFAULT 'PLANIFIEE'
                        CHECK(statut IN ('PLANIFIEE','EFFECTUEE','ANNULEE')),
    created_at          DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (tontine_id) REFERENCES tontines(id)
);

-- ── 13. AIDE SENTION ────────────────────────────────────────
CREATE TABLE aides_sention (
    id              TEXT PRIMARY KEY,
    membre_id       TEXT NOT NULL,
    tontine_id      TEXT NOT NULL,
    motif           TEXT NOT NULL
                    CHECK(motif IN ('MALADIE','DECES','MARIAGE','FETE','AUTRE')),
    montant         DECIMAL(10,2) NOT NULL,
    description     TEXT,
    statut          TEXT DEFAULT 'EN_ATTENTE'
                    CHECK(statut IN ('EN_ATTENTE','APPROUVEE','REFUSEE','VERSEE')),
    valide_par      TEXT,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (membre_id) REFERENCES membres(id),
    FOREIGN KEY (tontine_id) REFERENCES tontines(id),
    FOREIGN KEY (valide_par) REFERENCES membres(id)
);

-- ── 14. LITIGES ─────────────────────────────────────────────
CREATE TABLE litiges (
    id              TEXT PRIMARY KEY,
    signale_par     TEXT NOT NULL,
    tontine_id      TEXT NOT NULL,
    type_litige     TEXT NOT NULL
                    CHECK(type_litige IN (
                        'CONTRIBUTION_MANQUANTE',
                        'RANG_CONTESTE',
                        'PRET_NON_REMBOURSE',
                        'AUTRE'
                    )),
    description     TEXT NOT NULL,
    statut          TEXT DEFAULT 'OUVERT'
                    CHECK(statut IN ('OUVERT','EN_TRAITEMENT','RESOLU','ESCALADE')),
    decision        TEXT,
    date_limite     DATETIME,   -- +7j auto escalade
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (signale_par) REFERENCES membres(id),
    FOREIGN KEY (tontine_id) REFERENCES tontines(id)
);

-- ── 15. NOTIFICATIONS ───────────────────────────────────────
CREATE TABLE notifications (
    id              TEXT PRIMARY KEY,
    membre_id       TEXT NOT NULL,
    tontine_id      TEXT,
    type_notif      TEXT NOT NULL
                    CHECK(type_notif IN (
                        'RAPPEL_COTISATION','PAIEMENT_CONFIRME',
                        'PAIEMENT_REJETE','BOUFFEMENT','SENTION',
                        'REMBOURSEMENT','CASSATION','DEMANDE_ACCEPTEE',
                        'DEMANDE_REFUSEE','LITIGE','AIDE_SENTION'
                    )),
    titre           TEXT NOT NULL,
    message         TEXT NOT NULL,
    canal           TEXT DEFAULT 'PUSH'
                    CHECK(canal IN ('PUSH','SMS','EMAIL')),
    lu              BOOLEAN DEFAULT FALSE,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (membre_id) REFERENCES membres(id),
    FOREIGN KEY (tontine_id) REFERENCES tontines(id)
);

-- ── 16. AUDIT LOG ───────────────────────────────────────────
CREATE TABLE audit_logs (
    id              TEXT PRIMARY KEY,
    auteur_id       TEXT NOT NULL,
    action          TEXT NOT NULL,
    table_cible     TEXT,
    entite_id       TEXT,
    details         TEXT,           -- JSON
    ip_address      TEXT,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (auteur_id) REFERENCES membres(id)
);

-- ── INDEX pour performance ───────────────────────────────────
CREATE INDEX idx_paiements_membre    ON paiements(membre_id);
CREATE INDEX idx_paiements_seance    ON paiements(seance_id);
CREATE INDEX idx_adhesions_lot       ON adhesions_lot(lot_id);
CREATE INDEX idx_adhesions_membre    ON adhesions_lot(membre_id);
CREATE INDEX idx_notifications_membre ON notifications(membre_id);
CREATE INDEX idx_transactions_compte  ON transactions(compte_id);
CREATE INDEX idx_seances_tontine     ON seances(tontine_id);
CREATE INDEX idx_litiges_tontine     ON litiges(tontine_id);