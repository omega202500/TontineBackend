import requests
import uuid
from app.config import settings

if settings.PAWAPAY_MODE == "production":
    BASE_URL = settings.PAWAPAY_API_PRODUCTION_URL
else:
    BASE_URL = settings.PAWAPAY_API_SANDBOX_URL
    
def _headers() -> dict:
    return {
        "Authorization": f"Bearer {settings.PAWAPAY_API_KEY}",
        "Content-Type": "application/json",
    }

# ── Détection opérateur Cameroun ──
def detecter_operateur(telephone: str) -> str:
    numero = telephone.replace("+237", "").replace(" ", "").lstrip("0")
    if not numero.startswith("237"):
        numero = "237" + numero
    prefix = numero[3:6]
    mtn = ("650","651","652","653","654","670","671","672","673",
           "674","675","676","677","678","679","680","681","682",
           "683","684","685")
    orange = ("690","691","692","693","694","695","696","697",
              "698","699","655","656","657","658","659")
    if prefix in mtn:
        return "MTN_MOMO_CMR"
    elif prefix in orange:
        return "ORANGE_CMR"
    return "MTN_MOMO_CMR"

def formater_numero(telephone: str) -> str:
    """Retourne le numéro au format MSISDN : 237XXXXXXXXX"""
    n = telephone.replace("+237","").replace(" ","").lstrip("0")
    if not n.startswith("237"):
        n = "237" + n
    return n

# ── Valider le numéro via PawaPay ──
def valider_numero(telephone: str) -> dict:
    numero = formater_numero(telephone)
    try:
        resp = requests.post(
            f"{BASE_URL}/predict-provider",
            json={"phoneNumber": numero},
            headers=_headers(), timeout=10
        )
        if resp.status_code == 200:
            data = resp.json()
            return {
                "valide": True,
                "numero": data.get("phoneNumber", numero),
                "provider": data.get("provider", detecter_operateur(telephone)),
                "country": data.get("country", "CMR"),
            }
    except:
        pass
    # Fallback local
    return {
        "valide": True,
        "numero": formater_numero(telephone),
        "provider": detecter_operateur(telephone),
        "country": "CMR",
    }

# ── Récupérer la config active (opérateurs disponibles) ──
def get_config_active() -> dict:
    try:
        resp = requests.get(
            f"{BASE_URL}/active-conf?country=CMR&operationType=DEPOSIT",
            headers=_headers(), timeout=10
        )
        if resp.status_code == 200:
            return resp.json()
    except:
        pass
    # Fallback : retourner les opérateurs connus Cameroun
    return {
        "countries": [{
            "country": "CMR",
            "prefix": "237",
            "providers": [
                {"provider": "MTN_MOMO_CMR", "displayName": "MTN MoMo",
                 "logo": "https://static-content.pawapay.io/company_logos/mtn.png"},
                {"provider": "ORANGE_CMR", "displayName": "Orange Money",
                 "logo": "https://static-content.pawapay.io/company_logos/orange.png"},
            ]
        }]
    }

# ── Initier un dépôt (débit du membre) ──
def initier_depot(telephone: str, montant: float,
                  provider: str = None,
                  type_transaction: str = "COTISATION") -> dict:
    deposit_id = str(uuid.uuid4())
    info       = valider_numero(telephone)
    numero     = info["numero"]
    operateur  = provider or info["provider"]

    payload = {
        "depositId":  deposit_id,
        "amount":     str(int(montant)),
        "currency":   "XAF",
        "country":    "CMR",
        "payer": {
            "type": "MMO",
            "accountDetails": {
                "phoneNumber": numero,
                "provider":    operateur,
            }
        },
        "statementDescription": f"Tontine-{type_transaction[:20]}",
        "callbackUrl": settings.PAWAPAY_CALLBACK_URL,
    }

    # ── Log de diagnostic ──
    print(f"[PAWAPAY] URL      : {BASE_URL}/deposits")
    print(f"[PAWAPAY] Numero   : {numero}")
    print(f"[PAWAPAY] Operateur: {operateur}")
    print(f"[PAWAPAY] Montant  : {montant}")
    print(f"[PAWAPAY] Token    : {settings.PAWAPAY_API_KEY[:30]}...")

    try:
        resp = requests.post(
            f"{BASE_URL}/deposits",
            json=payload, headers=_headers(), timeout=30
        )

        # ── Log réponse brute ──
        print(f"[PAWAPAY] Status HTTP : {resp.status_code}")
        print(f"[PAWAPAY] Réponse     : {resp.text}")

        data   = resp.json()
        statut = data.get("status", "")

        if statut == "ACCEPTED":
            return {
                "success":    True,
                "deposit_id": deposit_id,
                "statut":     "ACCEPTED",
                "operateur":  operateur,
                "message":    f"Demande envoyée sur {operateur}. Confirmez sur votre téléphone.",
            }
        elif statut == "REJECTED":
            raison = data.get("failureReason", {})
            return {
                "success":    False,
                "deposit_id": deposit_id,
                "message":    raison.get("failureMessage", "Paiement rejeté"),
                "code":       raison.get("failureCode", "REJECTED"),
            }
        else:
            return {"success": False, "message": f"Statut inattendu: {statut}", "data": data}

    except requests.Timeout:
        return {"success": False, "deposit_id": deposit_id,
                "message": "Délai dépassé. Vérifiez le statut manuellement."}
    except Exception as e:
        return {"success": False, "message": str(e)}
# ── Vérifier statut dépôt ──
def verifier_statut_depot(deposit_id: str) -> dict:
    try:
        resp = requests.get(
            f"{BASE_URL}/deposits/{deposit_id}",
            headers=_headers(), timeout=15
        )
        data = resp.json()
        if isinstance(data, list):
            data = data[0] if data else {}
        if not data:
            return {"deposit_id": deposit_id, "statut": "NOT_FOUND",
                    "completed": False, "failed": True}

        statut = data.get("status", "UNKNOWN")
        return {
            "deposit_id": deposit_id,
            "statut":     statut,
            "completed":  statut == "COMPLETED",
            "failed":     statut in ["FAILED", "REJECTED"],
            "processing": statut in ["ACCEPTED", "PROCESSING"],
            "data":       data,
        }
    except Exception as e:
        return {"deposit_id": deposit_id, "statut": "ERREUR",
                "completed": False, "failed": False, "processing": True}

# ── Initier un payout (virement vers membre) ──
def initier_payout(telephone: str, montant: float,
                   provider: str = None,
                   description: str = "Bouffement") -> dict:
    payout_id = str(uuid.uuid4())
    info = valider_numero(telephone)
    numero = info["numero"]
    operateur = provider or info["provider"]

    payload = {
        "payoutId":   payout_id,
        "amount":     str(int(montant)),
        "currency":   "XAF",
        "country":    "CMR",
        "correspondent": operateur,
        "recipient": {
            "type": "MMO",
            "accountDetails": {
                "phoneNumber": numero,
                "provider":    operateur,
            }
        },
        "statementDescription": description[:20],
        "callbackUrl": settings.PAWAPAY_CALLBACK_URL,
    }

    try:
        resp = requests.post(
            f"{BASE_URL}/payouts",
            json=payload, headers=_headers(), timeout=30
        )
        data = resp.json()
        statut = data.get("status", "")
        if statut == "ACCEPTED":
            return {
                "success":   True,
                "payout_id": payout_id,
                "statut":    "ACCEPTED",
                "message":   f"{int(montant):,} FCFA envoyés vers {operateur} ({telephone})",
            }
        raison = data.get("failureReason", {})
        return {
            "success": False,
            "message": raison.get("failureMessage", f"Erreur: {statut}"),
        }
    except Exception as e:
        return {"success": False, "message": str(e)}