from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.auth import (
    LoginRequest, AuthResponse, MembreResponse,
    DemandeInscription, CreatePassword, UpdateProfil
)
from app.services.auth_service import (
    promouvoir_fondateur,
    soumettre_demande,
    accepter_membre,
    refuser_membre,
      login_membre,              
    create_token,         
    decode_token,         
    lister_demandes,      
    promouvoir_fondateur, 
    update_profil, 
)
from app.models.membre import Membre, StatutMembre
from app.models.notification import Notification
from app.models.enums import TypeNotif
import uuid

router = APIRouter(prefix="/auth", tags=["Authentification"])

# ══ Helpers ══
def get_current_membre(authorization: str = Header(...), db: Session = Depends(get_db)):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token manquant")
    token = authorization.split(" ")[1]
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Token invalide ou expiré")
    membre = db.query(Membre).filter(Membre.id == payload["sub"]).first()
    if not membre:
        raise HTTPException(status_code=401, detail="Membre introuvable")
    return membre

def get_fondateur(membre: Membre = Depends(get_current_membre)):
    if not membre.est_fondateur:
        raise HTTPException(status_code=403, detail="Accès réservé au fondateur")
    return membre

def notifier_fondateurs(db: Session, titre: str, message: str, type_notif: TypeNotif):
    fondateurs = db.query(Membre).filter(
        Membre.est_fondateur == True,
        Membre.statut == StatutMembre.ACTIF
    ).all()
    for f in fondateurs:
        notif = Notification(
            id=str(uuid.uuid4()),
            membre_id=f.id,
            type_notif=type_notif,
            titre=titre,
            message=message,
        )
        db.add(notif)
    db.commit()

def _to_response(m: Membre) -> MembreResponse:
    return MembreResponse(
        id=m.id, nom=m.nom, prenom=m.prenom, age=m.age,
        ville=m.ville, telephone=m.telephone,
        numero_cni=m.numero_cni, photo_url=m.photo_url,
        est_fondateur=m.est_fondateur, statut=m.statut,
    )

# ══ VISITEUR ══

@router.post("/demande", response_model=AuthResponse)
def soumettre_demande_route(data: DemandeInscription, db: Session = Depends(get_db)):
    membre, err = soumettre_demande(db, data.model_dump())
    if err:
        raise HTTPException(status_code=400, detail=err)
    notifier_fondateurs(
        db,
        titre="🆕 Nouveau membre inscrit",
        message=f"{data.prenom} {data.nom} ({data.telephone}) vient de rejoindre la tontine. "
                f"CNI: {data.numero_cni} · Ville: {data.ville} · "
                f"Lot: {data.lot_souhaite or 'Non précisé'}",
        type_notif=TypeNotif.DEMANDE_ACCEPTEE,
    )
    token = create_token(membre.id)
    return AuthResponse(access_token=token, membre=_to_response(membre))
@router.post("/creer-password", response_model=AuthResponse)
def creer_password_route(data: CreatePassword, db: Session = Depends(get_db)):
    membre, err = creer_password(db, data.telephone, data.password) # type: ignore
    if err:
        raise HTTPException(status_code=400, detail=err)
    token = create_token(membre.id)
    return AuthResponse(access_token=token, membre=_to_response(membre))

@router.post("/login", response_model=AuthResponse)
def login(data: LoginRequest, db: Session = Depends(get_db)):
    membre, err = login_membre(db, data.telephone, data.password)
    if err:
        raise HTTPException(status_code=401, detail=err)
    token = create_token(membre.id)
    return AuthResponse(access_token=token, membre=_to_response(membre))

@router.get("/me", response_model=MembreResponse)
def get_me(membre: Membre = Depends(get_current_membre)):
    return _to_response(membre)

# ══ FONDATEUR ══

@router.get("/fondateur/demandes")
def get_demandes(fondateur=Depends(get_fondateur), db: Session = Depends(get_db)):
    return [_to_response(m) for m in lister_demandes(db)]

@router.get("/fondateur/membres")
def get_membres(fondateur=Depends(get_fondateur), db: Session = Depends(get_db)):
    membres = db.query(Membre).filter(
        Membre.est_fondateur == False,
        Membre.statut.in_([StatutMembre.ACTIF, StatutMembre.SUSPENDU, StatutMembre.ARCHIVE])
    ).all()
    return [_to_response(m) for m in membres]

@router.put("/fondateur/accepter/{membre_id}")
def accepter(membre_id: str, fondateur=Depends(get_fondateur), db: Session = Depends(get_db)):
    membre = db.query(Membre).filter(Membre.id == membre_id).first()
    if not membre:
        raise HTTPException(status_code=404, detail="Membre introuvable")
    # ✅ Changer le statut vers ACTIF
    membre.statut = StatutMembre.ACTIF
    # Notifier le membre accepté
    notif = Notification(
        id=str(uuid.uuid4()),
        membre_id=membre.id,
        type_notif=TypeNotif.DEMANDE_ACCEPTEE,
        titre="✅ Demande acceptée !",
        message=f"Félicitations {membre.prenom} ! Votre demande a été acceptée. "
                f"Créez votre mot de passe pour accéder à la tontine.",
    )
    db.add(notif)
    db.commit()
    return {"message": f"{membre.prenom} {membre.nom} a été accepté(e)"}

@router.put("/fondateur/refuser/{membre_id}")
def refuser(membre_id: str, fondateur=Depends(get_fondateur), db: Session = Depends(get_db)):
    membre = db.query(Membre).filter(Membre.id == membre_id).first()
    if not membre:
        raise HTTPException(status_code=404, detail="Membre introuvable")
    # ✅ Changer le statut vers REFUSE
    membre.statut = StatutMembre.REFUSE
    notif = Notification(
        id=str(uuid.uuid4()),
        membre_id=membre.id,
        type_notif=TypeNotif.DEMANDE_REFUSEE,
        titre="❌ Demande refusée",
        message="Votre demande d'adhésion a été refusée par le fondateur.",
    )
    db.add(notif)
    db.commit()
    return {"message": "Demande refusée"}

@router.put("/fondateur/archiver/{membre_id}")
def archiver(membre_id: str, fondateur=Depends(get_fondateur), db: Session = Depends(get_db)):
    membre = db.query(Membre).filter(Membre.id == membre_id).first()
    if not membre:
        raise HTTPException(status_code=404, detail="Membre introuvable")
    membre.statut = StatutMembre.ARCHIVE
    db.commit()
    return {"message": "Membre archivé"}

@router.put("/fondateur/suspendre/{membre_id}")
def suspendre(membre_id: str, fondateur=Depends(get_fondateur), db: Session = Depends(get_db)):
    membre = db.query(Membre).filter(Membre.id == membre_id).first()
    if not membre:
        raise HTTPException(status_code=404, detail="Membre introuvable")
    membre.statut = StatutMembre.SUSPENDU
    db.commit()
    return {"message": f"{membre.prenom} marqué inactif"}

@router.put("/fondateur/reactiver/{membre_id}")
def reactiver(membre_id: str, fondateur=Depends(get_fondateur), db: Session = Depends(get_db)):
    membre = db.query(Membre).filter(Membre.id == membre_id).first()
    if not membre:
        raise HTTPException(status_code=404, detail="Membre introuvable")
    membre.statut = StatutMembre.ACTIF
    db.commit()
    return {"message": f"{membre.prenom} réactivé"}

@router.put("/fondateur/promouvoir/{membre_id}")
def promouvoir(membre_id: str, fondateur=Depends(get_fondateur), db: Session = Depends(get_db)):
    membre, err = promouvoir_fondateur(db, membre_id)
    if err:
        raise HTTPException(status_code=404, detail=err)
    return {"message": f"{membre.prenom} est maintenant fondateur"}

@router.put("/fondateur/profil")
def update_profil_route(data: UpdateProfil, fondateur=Depends(get_fondateur), db: Session = Depends(get_db)):
    membre, err = update_profil(db, fondateur.id, data.model_dump(exclude_none=True))
    if err:
        raise HTTPException(status_code=400, detail=err)
    return {"message": "Profil mis à jour"}

@router.get("/fondateur/stats")
def get_stats(fondateur=Depends(get_fondateur), db: Session = Depends(get_db)):
    nb_actifs   = db.query(Membre).filter(Membre.statut == StatutMembre.ACTIF).count()
    nb_attente  = db.query(Membre).filter(Membre.statut == StatutMembre.EN_ATTENTE).count()
    nb_inactifs = db.query(Membre).filter(Membre.statut == StatutMembre.SUSPENDU).count()
    return {
        "membres_actifs": nb_actifs,
        "demandes_en_attente": nb_attente,
        "membres_inactifs": nb_inactifs,
    }