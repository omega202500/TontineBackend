from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from app.database import get_db
from app.routers.auth import get_current_membre, get_fondateur
from app.models.lot import Lot, AdhesionLot
from app.models.enums import StatutLot
from app.models.membre import Membre
import uuid
import random

router = APIRouter(prefix="/lots", tags=["Lots"])


# ─────────────────────────────
# SCHEMAS
# ─────────────────────────────

class LotCreate(BaseModel):
    nom: str
    montant_cotisation: float
    nb_max_membres: int = 30
    option_integration: str = "ANTICIPEE"
    tontine_id: Optional[str] = None


class LotResponse(BaseModel):
    id: str
    nom: str
    montant_cotisation: float
    nb_max_membres: int
    cycle_actuel: int
    statut: str
    option_integration: str
    nb_membres: Optional[int] = 0

    class Config:
        from_attributes = True


# ─────────────────────────────
# LISTER TOUS LES LOTS
# ─────────────────────────────

@router.get("/", response_model=List[LotResponse])
def get_lots(
    db: Session = Depends(get_db),
    membre=Depends(get_current_membre)
):
    lots = db.query(Lot).filter(Lot.statut != StatutLot.CLOS).all()

    result = []

    for lot in lots:
        nb = db.query(AdhesionLot).filter(
            AdhesionLot.lot_id == lot.id
        ).count()

        result.append(
            LotResponse(
                id=str(lot.id),  # IMPORTANT UUID -> STRING
                nom=lot.nom,
                montant_cotisation=float(lot.montant_cotisation),
                nb_max_membres=lot.nb_max_membres,
                cycle_actuel=lot.cycle_actuel,
                statut=str(lot.statut),
                option_integration=str(lot.option_integration),
                nb_membres=nb
            )
        )

    return result


# ─────────────────────────────
# CREER UN LOT
# ─────────────────────────────

@router.post("/")
def creer_lot(
    data: LotCreate,
    db: Session = Depends(get_db),
    fondateur=Depends(get_fondateur)
):
    from app.models.tontine import Tontine

    if data.tontine_id:
        tontine = db.query(Tontine).filter(
            Tontine.id == data.tontine_id
        ).first()
    else:
        tontine = db.query(Tontine).filter(
            Tontine.fondateur_id == fondateur.id
        ).first()

    if not tontine:
        raise HTTPException(
            status_code=404,
            detail="Aucune tontine trouvée"
        )

    lot = Lot(
        id=uuid.uuid4(),
        tontine_id=tontine.id,
        nom=data.nom,
        montant_cotisation=data.montant_cotisation,
        nb_max_membres=data.nb_max_membres,
        option_integration=data.option_integration,
    )

    db.add(lot)
    db.commit()
    db.refresh(lot)

    return {
        "message": f"Lot '{lot.nom}' créé avec succès",
        "id": str(lot.id)
    }


# ─────────────────────────────
# ADHERER A UN LOT
# ─────────────────────────────

@router.post("/{lot_id}/adherer")
def adherer_lot(
    lot_id: str,
    db: Session = Depends(get_db),
    membre=Depends(get_current_membre)
):
    lot = db.query(Lot).filter(Lot.id == lot_id).first()

    if not lot:
        raise HTTPException(
            status_code=404,
            detail="Lot introuvable"
        )

    nb = db.query(AdhesionLot).filter(
        AdhesionLot.lot_id == lot_id
    ).count()

    if nb >= lot.nb_max_membres:
        raise HTTPException(
            status_code=400,
            detail="Ce lot est complet"
        )

    existe = db.query(AdhesionLot).filter(
        AdhesionLot.lot_id == lot_id,
        AdhesionLot.membre_id == membre.id
    ).first()

    if existe:
        raise HTTPException(
            status_code=400,
            detail="Vous êtes déjà dans ce lot"
        )

    membres_passes = db.query(AdhesionLot).filter(
        AdhesionLot.lot_id == lot_id,
        AdhesionLot.a_bouffe == True
    ).count()

    adhesion = AdhesionLot(
        id=uuid.uuid4(),
        membre_id=membre.id,
        lot_id=lot.id,
        membres_passes=membres_passes,
    )

    db.add(adhesion)
    db.commit()

    return {
        "message": f"Adhésion au lot '{lot.nom}' effectuée"
    }


# ─────────────────────────────
# TIRAGE AU SORT
# ─────────────────────────────

@router.post("/{lot_id}/tirage")
def tirage_au_sort(
    lot_id: str,
    db: Session = Depends(get_db),
    fondateur=Depends(get_fondateur)
):
    adhesions = db.query(AdhesionLot).filter(
        AdhesionLot.lot_id == lot_id,
        AdhesionLot.numero_tirage == None
    ).all()

    if not adhesions:
        raise HTTPException(
            status_code=400,
            detail="Tirage déjà effectué ou aucun membre"
        )

    random.shuffle(adhesions)

    for i, adhesion in enumerate(adhesions):
        adhesion.numero_tirage = i + 1

    db.commit()

    lot = db.query(Lot).filter(Lot.id == lot_id).first()

    rang1 = db.query(AdhesionLot).filter(
        AdhesionLot.lot_id == lot_id,
        AdhesionLot.numero_tirage == 1
    ).first()

    if rang1:
        lot.prochain_bouffeur_id = rang1.membre_id
        db.commit()

    return {
        "message": f"Tirage effectué — {len(adhesions)} membres numérotés",
        "ordre": [
            {
                "rang": a.numero_tirage,
                "membre_id": str(a.membre_id)
            }
            for a in sorted(
                adhesions,
                key=lambda x: x.numero_tirage
            )
        ]
    }


# ─────────────────────────────
# MEMBRES D'UN LOT
# ─────────────────────────────

@router.get("/{lot_id}/membres")
def membres_lot(
    lot_id: str,
    db: Session = Depends(get_db),
    membre=Depends(get_current_membre)
):
    adhesions = db.query(AdhesionLot).filter(
        AdhesionLot.lot_id == lot_id
    ).all()

    result = []

    for a in sorted(
        adhesions,
        key=lambda x: (x.numero_tirage or 9999)
    ):
        m = db.query(Membre).filter(
            Membre.id == a.membre_id
        ).first()

        if m:
            result.append({
                "membre_id": str(m.id),
                "nom": f"{m.prenom} {m.nom}",
                "telephone": m.telephone,
                "numero_tirage": a.numero_tirage,
                "a_bouffe": a.a_bouffe,
                "date_bouffement": a.date_bouffement,
            })

    return result


# ─────────────────────────────
# CLOTURER UN LOT
# ─────────────────────────────

@router.put("/{lot_id}/cloturer")
def cloturer_lot(
    lot_id: str,
    db: Session = Depends(get_db),
    fondateur=Depends(get_fondateur)
):
    lot = db.query(Lot).filter(
        Lot.id == lot_id
    ).first()

    if not lot:
        raise HTTPException(
            status_code=404,
            detail="Lot introuvable"
        )

    lot.statut = StatutLot.CLOS

    db.commit()

    return {
        "message": f"Lot '{lot.nom}' clôturé"
    }