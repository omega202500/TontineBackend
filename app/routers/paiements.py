from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from app.database import get_db
from app.routers.auth import get_current_membre, get_fondateur
from app.models.paiement import Paiement
from app.models.seance import Seance
from app.models.lot import Lot, AdhesionLot
from app.models.enums import StatutPaiement, ModePaiement, TypeNotif
from app.models.notification import Notification
from app.models.membre import Membre
import uuid

router = APIRouter(prefix="/paiements", tags=["Paiements"])

MONTANT_SENTION = 500  # FCFA fixe

class PaiementCreate(BaseModel):
    seance_id: str
    lot_id: str
    montant_envoye: float
    mode_paiement: str = "MOBILE_MONEY"
    reference_transaction: Optional[str] = None

class PaiementResponse(BaseModel):
    id: str
    montant_lot: float
    montant_sention: float
    montant_total: float
    retard: bool
    statut: str
    heure_envoi: str
    mode_paiement: str
    message: str

@router.post("/", response_model=PaiementResponse)
def verser_cotisation(
    data: PaiementCreate,
    db: Session = Depends(get_db),
    membre=Depends(get_current_membre)
):
    # 1. Vérifier séance
    seance = db.query(Seance).filter(Seance.id == data.seance_id).first()
    if not seance:
        raise HTTPException(status_code=404, detail="Séance introuvable")
    if seance.statut != "OUVERTE":
        raise HTTPException(status_code=400, detail="La séance n'est pas ouverte")

    # 2. Vérifier lot
    lot = db.query(Lot).filter(Lot.id == data.lot_id).first()
    if not lot:
        raise HTTPException(status_code=404, detail="Lot introuvable")

    # 3. Vérifier adhésion
    adhesion = db.query(AdhesionLot).filter(
        AdhesionLot.lot_id == data.lot_id,
        AdhesionLot.membre_id == membre.id
    ).first()
    if not adhesion:
        raise HTTPException(status_code=403, detail="Vous n'êtes pas membre de ce lot")

    # 4. Vérifier doublon
    deja_paye = db.query(Paiement).filter(
        Paiement.seance_id == data.seance_id,
        Paiement.membre_id == membre.id,
        Paiement.statut == "VALIDE"
    ).first()
    if deja_paye:
        raise HTTPException(status_code=400, detail="Vous avez déjà payé pour cette séance")

    # 5. ── LOGIQUE SENTION CORRIGÉE ──
    # La sention s'applique UNIQUEMENT si le paiement est envoyé APRÈS l'heure de FIN
    heure_actuelle  = datetime.now().time()
    heure_ouverture = datetime.strptime(seance.heure_ouverture, "%H:%M").time()
    heure_cloture   = datetime.strptime(seance.heure_cloture, "%H:%M").time()

    # Paiement avant ouverture → refusé
    if heure_actuelle < heure_ouverture:
        raise HTTPException(
            status_code=400,
            detail=f"La séance n'est pas encore ouverte. Revenez à partir de {seance.heure_ouverture}."
        )

    montant_lot = float(lot.montant_cotisation)

    # Retard = paiement APRÈS l'heure de clôture (ex: après 18h00)
    retard  = heure_actuelle > heure_cloture
    sention = MONTANT_SENTION if retard else 0
    montant_du = montant_lot + sention

    # 6. Vérifier solde suffisant
    if data.montant_envoye < montant_du:
        if retard:
            raise HTTPException(
                status_code=400,
                detail={
                    "code": "SOLDE_INSUFFISANT",
                    "montant_du": montant_du,
                    "montant_lot": montant_lot,
                    "montant_sention": sention,
                    "retard": True,
                    "message": f"Solde insuffisant. Vous payez après {seance.heure_cloture}. "
                               f"Vous devez envoyer {montant_du:,.0f} FCFA "
                               f"(cotisation: {montant_lot:,.0f} + sention: {sention:,.0f} FCFA)."
                }
            )
        else:
            raise HTTPException(
                status_code=400,
                detail={
                    "code": "SOLDE_INSUFFISANT",
                    "montant_du": montant_du,
                    "montant_lot": montant_lot,
                    "montant_sention": 0,
                    "retard": False,
                    "message": f"Montant insuffisant. Envoyez {montant_du:,.0f} FCFA."
                }
            )

    # 7. Enregistrer paiement
    paiement = Paiement(
        id=str(uuid.uuid4()),
        membre_id=membre.id,
        seance_id=data.seance_id,
        lot_id=data.lot_id,
        montant_lot=montant_lot,
        montant_sention=sention,
        montant_total=montant_du,
        heure_envoi=datetime.now(),
        retard=retard,
        mode_paiement=data.mode_paiement,
        reference_transaction=data.reference_transaction,
        statut=StatutPaiement.VALIDE,
    )
    db.add(paiement)

    # 8. Mettre à jour statut membre → ACTIF
    membre.statut = "ACTIF"

    # 9. Notification confirmation
    msg = f"Cotisation de {montant_lot:,.0f} FCFA validée"
    if retard:
        msg += f" + sention {sention:,.0f} FCFA (paiement après {seance.heure_cloture})"
    msg += f" pour la séance du {seance.date_seance}."

    notif = Notification(
        id=str(uuid.uuid4()),
        membre_id=membre.id,
        tontine_id=seance.tontine_id,
        type_notif=TypeNotif.PAIEMENT_CONFIRME,
        titre="✅ Paiement confirmé",
        message=msg,
    )
    db.add(notif)
    db.commit()
    db.refresh(paiement)

    return PaiementResponse(
        id=paiement.id,
        montant_lot=float(paiement.montant_lot),
        montant_sention=float(paiement.montant_sention),
        montant_total=float(paiement.montant_total),
        retard=paiement.retard,
        statut=paiement.statut,
        heure_envoi=paiement.heure_envoi.strftime("%H:%M:%S"),
        mode_paiement=paiement.mode_paiement,
        message=msg,
    )

@router.get("/historique")
def historique(db: Session = Depends(get_db), membre=Depends(get_current_membre)):
    paiements = db.query(Paiement).filter(
        Paiement.membre_id == membre.id
    ).order_by(Paiement.created_at.desc()).all()
    result = []
    for p in paiements:
        seance = db.query(Seance).filter(Seance.id == p.seance_id).first()
        lot    = db.query(Lot).filter(Lot.id == p.lot_id).first()
        result.append({
            "id": p.id,
            "date_seance": seance.date_seance if seance else None,
            "lot_nom": lot.nom if lot else None,
            "montant_lot": float(p.montant_lot),
            "montant_sention": float(p.montant_sention),
            "montant_total": float(p.montant_total),
            "retard": p.retard,
            "statut": p.statut,
            "mode": p.mode_paiement,
            "heure": p.heure_envoi.strftime("%H:%M") if p.heure_envoi else None,
        })
    return result

@router.get("/seance/{seance_id}")
def paiements_seance(seance_id: str, db: Session = Depends(get_db), fondateur=Depends(get_fondateur)):
    paiements = db.query(Paiement).filter(Paiement.seance_id == seance_id).all()
    result = []
    for p in paiements:
        m = db.query(Membre).filter(Membre.id == p.membre_id).first()
        result.append({
            "membre": f"{m.prenom} {m.nom}" if m else "Inconnu",
            "telephone": m.telephone if m else None,
            "montant_total": float(p.montant_total),
            "montant_sention": float(p.montant_sention),
            "retard": p.retard,
            "statut": p.statut,
            "heure": p.heure_envoi.strftime("%H:%M") if p.heure_envoi else None,
        })
    return result

# ── Initier un transfert Mobile Money (bouffement) ──
@router.post("/transfert-bouffement")
def transfert_bouffement(
    data: dict,
    db: Session = Depends(get_db),
    membre=Depends(get_current_membre)
):
    """
    Transfère le montant du bouffement vers le compte Mobile Money du membre.
    """
    montant   = data.get("montant")
    operateur = data.get("operateur")  # "MTN" ou "ORANGE"
    numero    = data.get("numero_mobile_money")

    if not montant or not operateur or not numero:
        raise HTTPException(status_code=400, detail="montant, operateur et numero_mobile_money requis")

    # Appel API Mobile Money (simulé — voir service dédié)
    from app.services.mobile_money_service import initier_transfert
    resultat = initier_transfert(
        operateur=operateur,
        numero=numero,
        montant=montant,
        reference=f"BOUFFEMENT-{membre.id[:8]}",
        description=f"Bouffement tontine – {membre.prenom} {membre.nom}"
    )

    if not resultat["success"]:
        raise HTTPException(status_code=400, detail=resultat["message"])

    return {
        "message": f"Transfert de {montant:,.0f} FCFA vers {operateur} ({numero}) initié.",
        "reference": resultat.get("reference"),
        "statut": resultat.get("statut"),
    }