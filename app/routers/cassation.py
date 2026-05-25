from fastapi import APIRouter

router = APIRouter()

@router.get("/")
def get_cassations():
    return {"message": "Cassations OK"}