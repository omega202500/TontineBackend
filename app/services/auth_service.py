from sqlalchemy.orm import Session
import bcrypt
from jose import jwt, JWTError
from datetime import datetime, timedelta
from app.models.membre import Membre, StatutMembre
from app.config import settings

# ── Hash mot de passe ──
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode('utf-8'), hashed.encode('utf-8'))

# ── Token JWT ──
def create_token(membre_id: str) -> str:
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode(
        {"sub": membre_id, "exp": expire},
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )

def decode_token(token: str):
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError:
        return None

# ── Fondateur par défaut ──
def creer_fondateur_defaut(db: Session):
    existe = db.query(Membre).filter(Membre.telephone == "690000000").first()
    if not existe:
        fondateur = Membre(
            nom="Admin",
            prenom="Tontine",
            telephone="690000000",
            password=hash_password("admin1234"),
            est_fondateur=True,
            statut=StatutMembre.ACTIF,
        )
        db.add(fondateur)
        db.commit()
        print("✅ Fondateur par défaut créé : 690000000 / admin1234")

# ── Soumettre demande visiteur (avec password hashé dès le départ) ──
def soumettre_demande(db: Session, data: dict):
    existant = db.query(Membre).filter(Membre.telephone == data["telephone"]).first()
    if existant:
        return None, "Ce numéro de téléphone est déjà utilisé"

    # Le mot de passe est hashé immédiatement, il ne sera jamais visible
    password_brut = data.get("password", "")
    if not password_brut or len(password_brut) < 6:
        return None, "Le mot de passe doit contenir au moins 6 caractères"

    membre = Membre(
        nom=data["nom"],
        prenom=data["prenom"],
        age=data.get("age"),
        ville=data.get("ville"),
        telephone=data["telephone"],
        numero_cni=data.get("numero_cni"),
        photo_url=data.get("photo_url"),
        lot_souhaite=data.get("lot_souhaite"),
        password=hash_password(password_brut),  
        statut=StatutMembre.ACTIF,         
    )
    db.add(membre)
    db.commit()
    db.refresh(membre)
    return membre, None

# ── Connexion ──
# Vérifie téléphone + mot de passe ET que le statut est ACTIF
def login_membre(db, telephone, password):
    membre = db.query(Membre).filter(Membre.telephone == telephone).first()
    if not membre:
        return None, "Numéro introuvable"
    if membre.statut != StatutMembre.ACTIF:
        return None, "Compte non activé ou en attente"
    if not verify_password(password, membre.password):
        return None, "Mot de passe incorrect"
    return membre, None

# ── Mise à jour profil ──
def update_profil(db: Session, membre_id: str, data: dict):
    membre = db.query(Membre).filter(Membre.id == membre_id).first()
    if not membre:
        return None, "Membre introuvable"
    if data.get("nom"):      membre.nom    = data["nom"]
    if data.get("prenom"):   membre.prenom = data["prenom"]
    if data.get("age"):      membre.age    = data["age"]
    if data.get("password"): membre.password = hash_password(data["password"])
    db.commit()
    db.refresh(membre)
    return membre, None

# ── Lister demandes en attente ──
def lister_demandes(db: Session):
    return db.query(Membre).filter(Membre.statut == StatutMembre.EN_ATTENTE).all()

# ── Lister membres actifs ──
def lister_membres(db: Session):
    return db.query(Membre).filter(
        Membre.statut == StatutMembre.ACTIF,
        Membre.est_fondateur == False
    ).all()

# ── Accepter un membre (change statut EN_ATTENTE → ACTIF) ──
def accepter_membre(db: Session, membre_id: str):
    membre = db.query(Membre).filter(Membre.id == membre_id).first()
    if not membre:
        return None, "Membre introuvable"
    membre.statut = StatutMembre.ACTIF
    db.commit()
    db.refresh(membre)
    return membre, None

# ── Refuser ──
def refuser_membre(db: Session, membre_id: str):
    membre = db.query(Membre).filter(Membre.id == membre_id).first()
    if not membre:
        return None, "Membre introuvable"
    membre.statut = StatutMembre.REFUSE
    db.commit()
    return True, None

# ── Archiver (décès / exclusion) ──
def archiver_membre(db: Session, membre_id: str):
    membre = db.query(Membre).filter(Membre.id == membre_id).first()
    if not membre:
        return None, "Membre introuvable"
    membre.statut = StatutMembre.ARCHIVE
    db.commit()
    return True, None

# ── Promouvoir en fondateur ──
def promouvoir_fondateur(db: Session, membre_id: str):
    membre = db.query(Membre).filter(Membre.id == membre_id).first()
    if not membre:
        return None, "Membre introuvable"
    membre.est_fondateur = True
    db.commit()
    db.refresh(membre)
    return membre, None