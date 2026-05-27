from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.database import get_db
from app.routers.auth import get_current_membre, get_fondateur, notifier_fondateurs
from app.services.pawapay_service import (
    initier_depot, verifier_statut_depot,
    initier_payout, get_config_active, valider_numero
)
from app.models.membre import Membre, StatutMembre
from app.models.paiement import Paiement
from app.models.pret import Pret
from app.models.enums import StatutPaiement, TypeNotif, StatutPret
from app.models.notification import Notification
from app.models.lot import Lot, AdhesionLot
from app.models.seance import Seance
import uuid

router = APIRouter(prefix="/payments", tags=["PawaPay"])

# ── Stockage en mémoire des transactions en cours ──
# En production : utiliser une table BDD
_transactions: dict = {}

# ════════════════════════════════════════════
# SCHÉMAS
# ════════════════════════════════════════════

class InitierRequest(BaseModel):
    telephone: str
    montant: float
    provider: Optional[str] = None         # MTN_MOMO_CMR ou ORANGE_CMR
    type_transaction: str                  # COTISATION, EPARGNE, PRET_DEPOT, BOUFFEMENT
    seance_id: Optional[str] = None
    lot_id: Optional[str]    = None
    pret_id: Optional[str]   = None

class PayoutRequest(BaseModel):
    telephone: str
    montant: float
    provider: Optional[str] = None
    description: str = "Bouffement tontine"
    membre_id: Optional[str] = None

class DemandeRetrait(BaseModel):
    montant: float
    telephone: str
    provider: Optional[str] = None

class DemandePret(BaseModel):
    montant: float
    date_echeance: str
    motif: Optional[str] = None
    tontine_id: Optional[str] = None

class ReponsePret(BaseModel):
    pret_id: str
    accepte: bool

# ════════════════════════════════════════════
# ROUTES UTILITAIRES
# ════════════════════════════════════════════

@router.get("/config")
def get_config(membre=Depends(get_current_membre)):
    """Retourne les opérateurs disponibles pour le Cameroun."""
    return get_config_active()

@router.post("/valider-numero")
def valider_tel(data: dict, membre=Depends(get_current_membre)):
    """Valide un numéro et détecte l'opérateur."""
    tel = data.get("telephone", "")
    return valider_numero(tel)

# ════════════════════════════════════════════
# INITIER UN PAIEMENT
# ════════════════════════════════════════════

@router.post("/initier")
def initier_paiement(
    data: InitierRequest,
    db: Session = Depends(get_db),
    membre=Depends(get_current_membre)
):
    """
    Initie un dépôt PawaPay.
    Utilisé pour : cotisation, dépôt épargne, remboursement prêt.
    """
    resultat = initier_depot(
        telephone=data.telephone,
        montant=data.montant,
        provider=data.provider,
        type_transaction=data.type_transaction,
    )

    if not resultat["success"]:
        raise HTTPException(status_code=400, detail=resultat["message"])

    deposit_id = resultat["deposit_id"]
    _transactions[deposit_id] = {
        "membre_id":        membre.id,
        "telephone":        data.telephone,
        "montant":          data.montant,
        "type_transaction": data.type_transaction,
        "seance_id":        data.seance_id,
        "lot_id":           data.lot_id,
        "pret_id":          data.pret_id,
        "statut":           "EN_COURS",
        "created_at":       datetime.utcnow().isoformat(),
    }

    return {
        "deposit_id": deposit_id,
        "operateur":  resultat.get("operateur"),
        "statut":     resultat.get("statut"),
        "message":    resultat.get("message"),
    }

# ════════════════════════════════════════════
# VÉRIFIER STATUT (polling toutes les 5s)
# ════════════════════════════════════════════

@router.get("/status/{deposit_id}")
def verifier_statut(
    deposit_id: str,
    db: Session = Depends(get_db),
    membre=Depends(get_current_membre)
):
    resultat = verifier_statut_depot(deposit_id)
    tx = _transactions.get(deposit_id, {})

    if resultat["completed"] and tx.get("statut") != "VALIDE":
        _transactions[deposit_id]["statut"] = "VALIDE"
        type_tx = tx.get("type_transaction", "")

        if type_tx == "COTISATION":
            _enregistrer_cotisation(db, tx, deposit_id)
        elif type_tx == "EPARGNE":
            _enregistrer_epargne(db, tx, deposit_id)
        elif type_tx == "REMBOURSEMENT":
            _enregistrer_remboursement(db, tx, deposit_id)

        _envoyer_notif_succes(db, tx, type_tx)

    return {
        "deposit_id":   deposit_id,
        "statut_pawapay": resultat["statut"],
        "completed":    resultat["completed"],
        "failed":       resultat["failed"],
        "processing":   resultat.get("processing", False),
        "transaction":  tx,
    }

# ════════════════════════════════════════════
# CALLBACK PAWAPAY (webhook automatique)
# ════════════════════════════════════════════

@router.post("/callback")
async def callback(request: Request, db: Session = Depends(get_db)):
    body = await request.json()
    deposit_id = body.get("depositId") or body.get("payoutId")
    statut = body.get("status", "")

    if deposit_id and deposit_id in _transactions:
        tx = _transactions[deposit_id]
        if statut == "COMPLETED" and tx.get("statut") != "VALIDE":
            _transactions[deposit_id]["statut"] = "VALIDE"
            type_tx = tx.get("type_transaction", "")
            if type_tx == "COTISATION":
                _enregistrer_cotisation(db, tx, deposit_id)
            elif type_tx == "EPARGNE":
                _enregistrer_epargne(db, tx, deposit_id)
            _envoyer_notif_succes(db, tx, type_tx)

        elif statut in ["FAILED", "REJECTED"]:
            _transactions[deposit_id]["statut"] = "ECHOUE"
            if tx.get("membre_id"):
                db.add(Notification(
                    id=str(uuid.uuid4()),
                    membre_id=tx["membre_id"],
                    type_notif=TypeNotif.PAIEMENT_REJETE,
                    titre="❌ Paiement échoué",
                    message="Votre paiement Mobile Money a échoué. Réessayez.",
                ))
                db.commit()

    return {"received": True}

# ════════════════════════════════════════════
# BOUFFEMENT — virement vers le membre
# ════════════════════════════════════════════

@router.post("/bouffement")
def bouffement_payout(
    data: PayoutRequest,
    db: Session = Depends(get_db),
    fondateur=Depends(get_fondateur)
):
    """Le fondateur déclenche le virement du bouffement vers le membre."""
    resultat = initier_payout(
        telephone=data.telephone,
        montant=data.montant,
        provider=data.provider,
        description=data.description,
    )
    if not resultat["success"]:
        raise HTTPException(status_code=400, detail=resultat["message"])

    # Notifier le membre bénéficiaire
    if data.membre_id:
        db.add(Notification(
            id=str(uuid.uuid4()),
            membre_id=data.membre_id,
            type_notif=TypeNotif.BOUFFEMENT,
            titre="🎉 Bouffement reçu !",
            message=f"Félicitations ! {int(data.montant):,} FCFA ont été envoyés "
                    f"sur votre {data.provider or 'Mobile Money'} ({data.telephone}).",
        ))
        db.commit()

    return {
        "message": resultat["message"],
        "payout_id": resultat.get("payout_id"),
    }

# ════════════════════════════════════════════
# DÉPÔT ÉPARGNE — retrait vers le membre
# ════════════════════════════════════════════

@router.post("/retrait-epargne")
def retrait_epargne(
    data: DemandeRetrait,
    db: Session = Depends(get_db),
    membre=Depends(get_current_membre)
):
    """Le membre retire son épargne vers son Mobile Money."""
    resultat = initier_payout(
        telephone=data.telephone,
        montant=data.montant,
        provider=data.provider,
        description="Retrait épargne tontine",
    )
    if not resultat["success"]:
        raise HTTPException(status_code=400, detail=resultat["message"])
    return {"message": resultat["message"], "payout_id": resultat.get("payout_id")}

# ════════════════════════════════════════════
# DEMANDE DE PRÊT — logique épargne
# ════════════════════════════════════════════

@router.post("/demande-pret")
def demander_pret(
    data: DemandePret,
    db: Session = Depends(get_db),
    membre=Depends(get_current_membre)
):
    """
    Un membre demande un prêt.
    Le système cherche un épargnant ayant un solde suffisant
    et lui envoie une notification pour accepter/refuser.
    """
    # 1. Trouver la tontine du membre si non précisée
    tontine_id = data.tontine_id
    if not tontine_id:
        adhesion = db.query(AdhesionLot).filter(
            AdhesionLot.membre_id == membre.id
        ).first()
        if adhesion:
            lot = db.query(Lot).filter(Lot.id == adhesion.lot_id).first()
            if lot:
                tontine_id = lot.tontine_id

    if not tontine_id:
        raise HTTPException(status_code=400, detail="Vous n'êtes membre d'aucune tontine")

    # 2. Créer la demande de prêt
    pret = Pret(
        id=str(uuid.uuid4()),
        emprunteur_id=membre.id,
        tontine_id=tontine_id,
        montant=data.montant,
        date_echeance=data.date_echeance,
        motif=data.motif,
        statut=StatutPret.EN_ATTENTE,
    )
    db.add(pret)
    db.flush()  # pour avoir pret.id

    # 3. Notifier le fondateur
    notifier_fondateurs(
        db,
        titre="🏦 Nouvelle demande de prêt",
        message=f"{membre.prenom} {membre.nom} demande un prêt de "
                f"{int(data.montant):,} FCFA — Motif: {data.motif or 'Non précisé'} "
                f"— Échéance: {data.date_echeance} — ID: {pret.id}",
        type_notif=TypeNotif.REMBOURSEMENT,
    )

    # 4. Chercher un épargnant avec un solde suffisant
    # (simplification : chercher dans les paiements d'épargne)
    epargnants_eligibles = _trouver_epargnants(db, tontine_id, data.montant, membre.id)

    for epargnant in epargnants_eligibles:
        db.add(Notification(
            id=str(uuid.uuid4()),
            membre_id=epargnant.id,
            tontine_id=tontine_id,
            type_notif=TypeNotif.REMBOURSEMENT,
            titre="💰 Demande de prêt sur votre épargne",
            message=f"{membre.prenom} {membre.nom} souhaite emprunter "
                    f"{int(data.montant):,} FCFA sur votre épargne. "
                    f"Voulez-vous accepter ? ID_PRET:{pret.id}",
        ))

    db.commit()

    return {
        "message": "Demande de prêt soumise. Le fondateur et les épargnants ont été notifiés.",
        "pret_id": pret.id,
        "epargnants_notifies": len(epargnants_eligibles),
    }

@router.post("/repondre-pret")
def repondre_pret(
    data: ReponsePret,
    db: Session = Depends(get_db),
    membre=Depends(get_current_membre)
):
    """
    Un épargnant accepte ou refuse de prêter son épargne.
    """
    pret = db.query(Pret).filter(Pret.id == data.pret_id).first()
    if not pret:
        raise HTTPException(status_code=404, detail="Prêt introuvable")

    if pret.statut != StatutPret.EN_ATTENTE:
        raise HTTPException(status_code=400, detail="Ce prêt a déjà été traité")

    if data.accepte:
        pret.statut = StatutPret.APPROUVE
        pret.valide_par = membre.id
        # Notifier l'emprunteur
        db.add(Notification(
            id=str(uuid.uuid4()),
            membre_id=pret.emprunteur_id,
            tontine_id=pret.tontine_id,
            type_notif=TypeNotif.REMBOURSEMENT,
            titre="✅ Prêt approuvé !",
            message=f"Votre demande de prêt de {int(float(pret.montant)):,} FCFA "
                    f"a été approuvée par {membre.prenom} {membre.nom}. "
                    f"Les fonds seront versés sur votre Mobile Money.",
        ))
    else:
        pret.statut = StatutPret.REFUSE
        db.add(Notification(
            id=str(uuid.uuid4()),
            membre_id=pret.emprunteur_id,
            tontine_id=pret.tontine_id,
            type_notif=TypeNotif.REMBOURSEMENT,
            titre="❌ Prêt refusé",
            message=f"Votre demande de prêt de {int(float(pret.montant)):,} FCFA "
                    f"a été refusée. D'autres épargnants ont peut-être été notifiés.",
        ))

    db.commit()
    return {"message": "Réponse enregistrée", "statut": pret.statut}

# ════════════════════════════════════════════
# HELPERS INTERNES
# ════════════════════════════════════════════

def _trouver_epargnants(db, tontine_id: str, montant_demande: float, emprunteur_id: str):
    """
    Cherche les membres ayant déposé une épargne >= montant demandé
    dans la même tontine, excluant l'emprunteur.
    """
    # Récupérer les lots de la tontine
    lots = db.query(Lot).filter(Lot.tontine_id == tontine_id).all()
    lot_ids = [l.id for l in lots]

    # Membres avec épargne = membres ayant des paiements de type EPARGNE
    membres_tontine = db.query(AdhesionLot).filter(
        AdhesionLot.lot_id.in_(lot_ids),
        AdhesionLot.membre_id != emprunteur_id,
    ).all()

    membres_ids = list({a.membre_id for a in membres_tontine})
    epargnants = []

    for mid in membres_ids:
        # Calculer l'épargne approximative (somme des paiements EPARGNE)
        # Pour simplifier, on retourne tous les membres actifs de la tontine
        m = db.query(Membre).filter(
            Membre.id == mid,
            Membre.statut == StatutMembre.ACTIF
        ).first()
        if m:
            epargnants.append(m)

    return epargnants[:3]  # Max 3 épargnants notifiés

def _enregistrer_cotisation(db, tx: dict, deposit_id: str):
    seance_id = tx.get("seance_id")
    lot_id    = tx.get("lot_id")
    if not seance_id or not lot_id:
        return
    lot = db.query(Lot).filter(Lot.id == lot_id).first()
    if not lot:
        return
    deja = db.query(Paiement).filter(
        Paiement.reference_transaction == deposit_id
    ).first()
    if deja:
        return
    db.add(Paiement(
        id=str(uuid.uuid4()),
        membre_id=tx["membre_id"],
        seance_id=seance_id,
        lot_id=lot_id,
        montant_lot=float(lot.montant_cotisation),
        montant_sention=0,
        montant_total=tx["montant"],
        heure_envoi=datetime.now(),
        retard=False,
        mode_paiement="MOBILE_MONEY",
        reference_transaction=deposit_id,
        statut=StatutPaiement.VALIDE,
    ))
    db.commit()

def _enregistrer_epargne(db, tx: dict, deposit_id: str):
    """Enregistre un dépôt d'épargne confirmé."""
    deja = db.query(Paiement).filter(
        Paiement.reference_transaction == deposit_id
    ).first()
    if deja:
        return
    # Trouver tontine_id
    adhesion = db.query(AdhesionLot).filter(
        AdhesionLot.membre_id == tx["membre_id"]
    ).first()
    tontine_id = None
    if adhesion:
        lot = db.query(Lot).filter(Lot.id == adhesion.lot_id).first()
        if lot:
            tontine_id = lot.tontine_id

    # Notifier le fondateur
    notifier_fondateurs(
        db,
        titre="💰 Nouveau dépôt d'épargne",
        message=f"{_get_membre_nom(db, tx['membre_id'])} vient de déposer "
                f"{int(tx['montant']):,} FCFA sur son épargne.",
        type_notif=TypeNotif.PAIEMENT_CONFIRME,
    )
    db.commit()

def _enregistrer_remboursement(db, tx: dict, deposit_id: str):
    pret_id = tx.get("pret_id")
    if not pret_id:
        return
    pret = db.query(Pret).filter(Pret.id == pret_id).first()
    if not pret:
        return
    montant = tx.get("montant", 0)
    pret.montant_rembourse = float(pret.montant_rembourse or 0) + montant
    if pret.montant_rembourse >= float(pret.montant_total_du or pret.montant):
        pret.statut = StatutPret.REMBOURSE
    db.commit()

def _envoyer_notif_succes(db, tx: dict, type_tx: str):
    titres = {
        "COTISATION":  ("✅ Cotisation confirmée", f"Votre cotisation de {int(tx['montant']):,} FCFA a été validée."),
        "EPARGNE":     ("💰 Épargne déposée", f"Votre dépôt de {int(tx['montant']):,} FCFA sur votre épargne est confirmé."),
        "REMBOURSEMENT": ("💸 Remboursement confirmé", f"Votre remboursement de {int(tx['montant']):,} FCFA a été enregistré."),
    }
    titre, msg = titres.get(type_tx, ("✅ Paiement confirmé", f"{int(tx['montant']):,} FCFA confirmés."))
    db.add(Notification(
        id=str(uuid.uuid4()),
        membre_id=tx["membre_id"],
        type_notif=TypeNotif.PAIEMENT_CONFIRME,
        titre=titre, message=msg,
    ))
    db.commit()

def _get_membre_nom(db, membre_id: str) -> str:
    m = db.query(Membre).filter(Membre.id == membre_id).first()
    return f"{m.prenom} {m.nom}" if m else "Un membre"