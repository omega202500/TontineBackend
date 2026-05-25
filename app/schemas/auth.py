from pydantic import BaseModel
from typing import Optional
from app.models.membre import StatutMembre

# ── Demande visiteur (avec mot de passe) ──
class DemandeInscription(BaseModel):
    nom: str
    prenom: str
    age: int
    ville: str
    telephone: str
    numero_cni: str
    password: str           # ✅ hashé en BDD, jamais envoyé au fondateur
    lot_souhaite: Optional[str] = None

# ── Connexion ──
class LoginRequest(BaseModel):
    telephone: str
    password: str

# ── Mise à jour profil ──
class UpdateProfil(BaseModel):
    nom: Optional[str] = None
    prenom: Optional[str] = None
    age: Optional[int] = None
    password: Optional[str] = None

# ── Création de mot de passe post-approbation (plus nécessaire mais gardé) ──
class CreatePassword(BaseModel):
    telephone: str
    password: str

# ── Membre retourné au frontend ──
class MembreResponse(BaseModel):
    id: str
    nom: str
    prenom: str
    age: Optional[int] = None
    ville: Optional[str] = None
    telephone: str
    numero_cni: Optional[str] = None
    photo_url: Optional[str] = None
    est_fondateur: bool
    statut: StatutMembre

    class Config:
        from_attributes = True

# ── Réponse auth ──
class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    membre: MembreResponse