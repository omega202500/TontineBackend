from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from app.database import Base, engine, SessionLocal
from app.routers import auth, epargne, lots, prets, seances, paiements, tontines, notifications, sention
from app.services.auth_service import creer_fondateur_defaut
from app.routers import pawapay

# ── Import de tous les modèles pour que SQLAlchemy les connaisse ──
from app.models import (
    Membre, Tontine, Lot, AdhesionLot, Seance,
    Paiement, Cassation, Pret, Remboursement,
    AideSention, Litige, Notification
)

app = FastAPI(title="Tontine API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth.router)
app.include_router(tontines.router)
app.include_router(lots.router)
app.include_router(seances.router)
app.include_router(paiements.router)
app.include_router(notifications.router)
app.include_router(sention.router)
app.include_router(pawapay.router)
app.include_router(epargne.router)
app.include_router(prets.router)

@app.on_event("startup")
def startup():
    # Sur MySQL : désactiver les FK pour pouvoir drop/create proprement
    with engine.connect() as conn:
        is_mysql = engine.dialect.name == "mysql"
        if is_mysql:
            conn.execute(text("SET FOREIGN_KEY_CHECKS = 0"))

        # Créer toutes les tables (ne recrée pas si elles existent)
        Base.metadata.create_all(bind=engine)

        if is_mysql:
            conn.execute(text("SET FOREIGN_KEY_CHECKS = 1"))
        conn.commit()

    # Créer le fondateur par défaut
    db = SessionLocal()
    try:
        creer_fondateur_defaut(db)
    finally:
        db.close()

@app.get("/")
def root():
    return {"message": "API Tontine v2 🤝"}