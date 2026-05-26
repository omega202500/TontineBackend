from fastapi import APIRouter
from pydantic import BaseModel
from app.services.pawapay_service import lancer_paiement

router = APIRouter(prefix="/pawapay", tags=["PawaPay"])

class PaiementRequest(BaseModel):
    numero: str
    montant: float

@router.post("/payer")
def payer(data: PaiementRequest):

    result = lancer_paiement(
        data.numero,
        data.montant
    )

    return result