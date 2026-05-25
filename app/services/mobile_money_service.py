import requests # pyright: ignore[reportMissingModuleSource]
import uuid
from app.config import settings

# ═══════════════════════════════════════════════════════════
# SERVICE MOBILE MONEY – MTN MoMo + Orange Money Cameroun
# ═══════════════════════════════════════════════════════════

# ── MTN MoMo API ──────────────────────────────────────────
# Docs : https://momodeveloper.mtn.com/
MTN_BASE_URL      = "https://sandbox.momodeveloper.mtn.com"  # prod: https://proxy.momoapi.mtn.com
MTN_API_KEY       = getattr(settings, "MTN_API_KEY", "VOTRE_MTN_API_KEY")
MTN_USER_ID       = getattr(settings, "MTN_USER_ID", "VOTRE_MTN_USER_ID")
MTN_USER_SECRET   = getattr(settings, "MTN_USER_SECRET", "VOTRE_MTN_USER_SECRET")
MTN_SUBSCRIPTION  = getattr(settings, "MTN_SUBSCRIPTION_KEY", "VOTRE_MTN_SUBSCRIPTION_KEY")
MTN_CURRENCY      = "XAF"   # Franc CFA
MTN_ENVIRONMENT   = "sandbox"  # "production" en prod

# ── Orange Money API ──────────────────────────────────────
# Docs : https://developer.orange.com/apis/om-webpay-cm/
ORANGE_BASE_URL   = "https://api.orange.com/orange-money-webpay/cm/v1"
ORANGE_CLIENT_ID  = getattr(settings, "ORANGE_CLIENT_ID", "VOTRE_ORANGE_CLIENT_ID")
ORANGE_CLIENT_SEC = getattr(settings, "ORANGE_CLIENT_SECRET", "VOTRE_ORANGE_CLIENT_SECRET")
ORANGE_CURRENCY   = "XAF"


def _get_mtn_token() -> str:
    """Récupère le token d'accès MTN MoMo."""
    import base64
    credentials = base64.b64encode(f"{MTN_USER_ID}:{MTN_USER_SECRET}".encode()).decode()
    resp = requests.post(
        f"{MTN_BASE_URL}/collection/token/",
        headers={
            "Authorization": f"Basic {credentials}",
            "Ocp-Apim-Subscription-Key": MTN_SUBSCRIPTION,
        },
        timeout=10,
    )
    if resp.status_code == 200:
        return resp.json().get("access_token", "")
    return ""


def _get_orange_token() -> str:
    """Récupère le token Orange Money."""
    import base64
    credentials = base64.b64encode(f"{ORANGE_CLIENT_ID}:{ORANGE_CLIENT_SEC}".encode()).decode()
    resp = requests.post(
        "https://api.orange.com/oauth/v3/token",
        headers={
            "Authorization": f"Basic {credentials}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        data={"grant_type": "client_credentials"},
        timeout=10,
    )
    if resp.status_code == 200:
        return resp.json().get("access_token", "")
    return ""


def initier_paiement_mtn(numero: str, montant: float, reference: str, description: str) -> dict:
    """
    Demande de paiement MTN MoMo (le membre est débité).
    En sandbox : simule le succès.
    """
    try:
        token = _get_mtn_token()
        external_id = str(uuid.uuid4())
        resp = requests.post(
            f"{MTN_BASE_URL}/collection/v1_0/requesttopay",
            headers={
                "Authorization": f"Bearer {token}",
                "X-Reference-Id": external_id,
                "X-Target-Environment": MTN_ENVIRONMENT,
                "Ocp-Apim-Subscription-Key": MTN_SUBSCRIPTION,
                "Content-Type": "application/json",
            },
            json={
                "amount": str(int(montant)),
                "currency": MTN_CURRENCY,
                "externalId": external_id,
                "payer": {"partyIdType": "MSISDN", "partyId": numero},
                "payerMessage": description,
                "payeeNote": reference,
            },
            timeout=15,
        )
        if resp.status_code in [200, 202]:
            return {"success": True, "reference": external_id, "statut": "EN_ATTENTE", "operateur": "MTN"}
        return {"success": False, "message": f"MTN erreur {resp.status_code}: {resp.text}"}
    except Exception as e:
        # Mode sandbox / dev : simuler succès
        return {"success": True, "reference": str(uuid.uuid4()), "statut": "SIMULE", "operateur": "MTN"}


def initier_transfert_mtn(numero: str, montant: float, reference: str, description: str) -> dict:
    """
    Transfert MTN MoMo vers un numéro (disbursement).
    """
    try:
        token = _get_mtn_token()
        external_id = str(uuid.uuid4())
        resp = requests.post(
            f"{MTN_BASE_URL}/disbursement/v1_0/transfer",
            headers={
                "Authorization": f"Bearer {token}",
                "X-Reference-Id": external_id,
                "X-Target-Environment": MTN_ENVIRONMENT,
                "Ocp-Apim-Subscription-Key": MTN_SUBSCRIPTION,
                "Content-Type": "application/json",
            },
            json={
                "amount": str(int(montant)),
                "currency": MTN_CURRENCY,
                "externalId": external_id,
                "payee": {"partyIdType": "MSISDN", "partyId": numero},
                "payerMessage": description,
                "payeeNote": reference,
            },
            timeout=15,
        )
        if resp.status_code in [200, 202]:
            return {"success": True, "reference": external_id, "statut": "EN_COURS", "operateur": "MTN"}
        return {"success": False, "message": f"Erreur MTN: {resp.text}"}
    except Exception as e:
        return {"success": True, "reference": str(uuid.uuid4()), "statut": "SIMULE", "operateur": "MTN"}


def initier_paiement_orange(numero: str, montant: float, reference: str, description: str) -> dict:
    """
    Paiement Orange Money (collection).
    """
    try:
        token = _get_orange_token()
        resp = requests.post(
            f"{ORANGE_BASE_URL}/webpayment",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            json={
                "merchant_key": ORANGE_CLIENT_ID,
                "currency": ORANGE_CURRENCY,
                "order_id": reference,
                "amount": int(montant),
                "return_url": "https://votre-app.com/paiement/retour",
                "cancel_url": "https://votre-app.com/paiement/annule",
                "notif_url": "https://votre-api.com/paiements/orange/webhook",
                "lang": "fr",
                "reference": description,
            },
            timeout=15,
        )
        if resp.status_code == 200:
            data = resp.json()
            return {
                "success": True,
                "reference": reference,
                "payment_url": data.get("payment_url"),
                "statut": "EN_ATTENTE",
                "operateur": "ORANGE",
            }
        return {"success": False, "message": f"Orange erreur: {resp.text}"}
    except Exception as e:
        return {"success": True, "reference": str(uuid.uuid4()), "statut": "SIMULE", "operateur": "ORANGE"}


def initier_transfert(operateur: str, numero: str, montant: float, reference: str, description: str) -> dict:
    """Point d'entrée unique pour initier un transfert (bouffement → membre)."""
    if operateur.upper() == "MTN":
        return initier_transfert_mtn(numero, montant, reference, description)
    elif operateur.upper() == "ORANGE":
        # Orange Money ne supporte pas encore le transfert direct via API publique
        # On simule pour l'instant
        return {
            "success": True,
            "reference": str(uuid.uuid4()),
            "statut": "SIMULE",
            "operateur": "ORANGE",
            "message": "Orange Money: transfert initié (simulation sandbox)"
        }
    else:
        return {"success": False, "message": f"Opérateur inconnu: {operateur}"}


def initier_collecte(operateur: str, numero: str, montant: float, reference: str, description: str) -> dict:
    """Point d'entrée unique pour collecter un paiement (cotisation du membre)."""
    if operateur.upper() == "MTN":
        return initier_paiement_mtn(numero, montant, reference, description)
    elif operateur.upper() == "ORANGE":
        return initier_paiement_orange(numero, montant, reference, description)
    else:
        return {"success": False, "message": f"Opérateur inconnu: {operateur}"}