from fastapi import APIRouter
from pydantic import BaseModel
from app.services.pawapay_service import initier_depot

router = APIRouter(prefix="/pawapay", tags=["PawaPay"])

class PaiementRequest(BaseModel):
    numero: str
    montant: float

@router.post("/initier_depot")
def initier_depot_endpoint(data: PaiementRequest):

    result = initier_depot(
        data.numero,
        data.montant
    )

    return result