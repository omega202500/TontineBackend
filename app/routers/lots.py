from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from app.database import get_db
from app.routers.auth import get_current_membre, get_fondateur
from app.models.lot import Lot, AdhesionLot
from app.models.enums import StatutLot, OptionIntegration
from app.models.membre import Membre, StatutMembre
import uuid, random
from datetime import datetime

router = APIRouter(prefix="/lots", tags=["Lots"])

# ── Schémas ──
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

# ── Lister tous les lots ──
@router.get("/", response_model=List[LotResponse])
def get_lots(db: Session = Depends(get_db), membre=Depends(get_current_membre)):
    lots = db.query(Lot).filter(Lot.statut != "CLOS").all()
    result = []
    for lot in lots:
        nb = db.query(AdhesionLot).filter(AdhesionLot.lot_id == lot.id).count()
        result.append(LotResponse(
            id=lot.id, nom=lot.nom,
            montant_cotisation=float(lot.montant_cotisation),
            nb_max_membres=lot.nb_max_membres,
            cycle_actuel=lot.cycle_actuel,
            statut=lot.statut,
            option_integration=lot.option_integration,
            nb_membres=nb
        ))
    return result

# ── Créer un lot ──
@router.post("/")
def creer_lot(data: LotCreate, db: Session = Depends(get_db), fondateur=Depends(get_fondateur)):
    # Récupérer la tontine du fondateur si non précisée
    from app.models.tontine import Tontine
    if data.tontine_id:
        tontine = db.query(Tontine).filter(Tontine.id == data.tontine_id).first()
    else:
        tontine = db.query(Tontine).filter(Tontine.fondateur_id == fondateur.id).first()

    if not tontine:
        raise HTTPException(status_code=404, detail="Aucune tontine trouvée. Créez d'abord une tontine.")

    lot = Lot(
        id=str(uuid.uuid4()),
        tontine_id=tontine.id,
        nom=data.nom,
        montant_cotisation=data.montant_cotisation,
        nb_max_membres=data.nb_max_membres,
        option_integration=data.option_integration,
    )
    db.add(lot)
    db.commit()
    db.refresh(lot)
    return {"message": f"Lot '{lot.nom}' créé avec succès", "id": lot.id}

# ── Adhérer à un lot ──
@router.post("/{lot_id}/adherer")
def adherer_lot(lot_id: str, db: Session = Depends(get_db), membre=Depends(get_current_membre)):
    lot = db.query(Lot).filter(Lot.id == lot_id).first()
    if not lot:
        raise HTTPException(status_code=404, detail="Lot introuvable")

    # Vérifier places disponibles
    nb = db.query(AdhesionLot).filter(AdhesionLot.lot_id == lot_id).count()
    if nb >= lot.nb_max_membres:
        raise HTTPException(status_code=400, detail="Ce lot est complet")

    # Vérifier si déjà adhérent
    existe = db.query(AdhesionLot).filter(
        AdhesionLot.lot_id == lot_id,
        AdhesionLot.membre_id == membre.id
    ).first()
    if existe:
        raise HTTPException(status_code=400, detail="Vous êtes déjà dans ce lot")

    # Calculer membres passés (pour option intégration)
    membres_passes = db.query(AdhesionLot).filter(
        AdhesionLot.lot_id == lot_id,
        AdhesionLot.a_bouffe == True
    ).count()

    adhesion = AdhesionLot(
        id=str(uuid.uuid4()),
        membre_id=membre.id,
        lot_id=lot_id,
        membres_passes=membres_passes,
    )
    db.add(adhesion)
    db.commit()
    return {"message": f"Adhésion au lot '{lot.nom}' effectuée"}

# ── Tirage au sort ──
@router.post("/{lot_id}/tirage")
def tirage_au_sort(lot_id: str, db: Session = Depends(get_db), fondateur=Depends(get_fondateur)):
    adhesions = db.query(AdhesionLot).filter(
        AdhesionLot.lot_id == lot_id,
        AdhesionLot.numero_tirage == None
    ).all()

    if not adhesions:
        raise HTTPException(status_code=400, detail="Tirage déjà effectué ou aucun membre")

    # Mélange aléatoire et attribution des numéros
    random.shuffle(adhesions)
    for i, adhesion in enumerate(adhesions):
        adhesion.numero_tirage = i + 1
    db.commit()

    # Mettre à jour prochain bouffeur (rang 1)
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
        "ordre": [{"rang": a.numero_tirage, "membre_id": a.membre_id} for a in sorted(adhesions, key=lambda x: x.numero_tirage)]
    }

# ── Membres d'un lot ──
@router.get("/{lot_id}/membres")
def membres_lot(lot_id: str, db: Session = Depends(get_db), membre=Depends(get_current_membre)):
    adhesions = db.query(AdhesionLot).filter(AdhesionLot.lot_id == lot_id).all()
    result = []
    for a in sorted(adhesions, key=lambda x: (x.numero_tirage or 9999)):
        m = db.query(Membre).filter(Membre.id == a.membre_id).first()
        if m:
            result.append({
                "membre_id": m.id,
                "nom": f"{m.prenom} {m.nom}",
                "telephone": m.telephone,
                "numero_tirage": a.numero_tirage,
                "a_bouffe": a.a_bouffe,
                "date_bouffement": a.date_bouffement,
            })
    return result

# ── Clôturer un lot (fin de cycle) ──
@router.put("/{lot_id}/cloturer")
def cloturer_lot(lot_id: str, db: Session = Depends(get_db), fondateur=Depends(get_fondateur)):
    lot = db.query(Lot).filter(Lot.id == lot_id).first()
    if not lot:
        raise HTTPException(status_code=404, detail="Lot introuvable")
    lot.statut = StatutLot.CLOS
    db.commit()
    return {"message": f"Lot '{lot.nom}' clôturé"}