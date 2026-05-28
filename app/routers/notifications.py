from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.routers.auth import get_current_membre, get_current_user
from app.models.notification import Notification

router = APIRouter(prefix="/notifications", tags=["Notifications"])

@router.get("/")
def get_notifications(db: Session = Depends(get_db), membre=Depends(get_current_user)):
    notifs = db.query(Notification).filter(
        Notification.membre_id == membre.id
    ).order_by(Notification.created_at.desc()).limit(50).all()
    return [{
        "id": n.id,
        "type_notif": n.type_notif,
        "titre": n.titre,
        "message": n.message,
        "lu": n.lu,
        "created_at": n.created_at.isoformat() if n.created_at else None,
    } for n in notifs]

@router.get("/non-lues/count")
def count_non_lues(db: Session = Depends(get_db), membre=Depends(get_current_user)):
    count = db.query(Notification).filter(
        Notification.membre_id == membre.id,
        Notification.lu == False
    ).count()
    return {"count": count}

@router.put("/{notif_id}/lu")
def marquer_lu(notif_id: str, db: Session = Depends(get_db), membre=Depends(get_current_user)):
    notif = db.query(Notification).filter(
        Notification.id == notif_id,
        Notification.membre_id == membre.id
    ).first()
    if notif:
        notif.lu = True
        db.commit()
    return {"message": "Marquée comme lue"}

@router.put("/tout-lire")
def tout_marquer_lu(db: Session = Depends(get_db), membre=Depends(get_current_user)):
    db.query(Notification).filter(
        Notification.membre_id == membre.id,
        Notification.lu == False
    ).update({"lu": True})
    db.commit()
    return {"message": "Toutes les notifications marquées comme lues"}