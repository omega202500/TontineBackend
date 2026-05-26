import uuid
import requests
import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("PAWAPAY_API_KEY")
BASE_URL = os.getenv("PAWAPAY_BASE_URL")

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

def lancer_paiement(numero, montant):

    deposit_id = str(uuid.uuid4())

    payload = {
        "depositId": deposit_id,
        "amount": str(montant),
        "currency": "XAF",
        "country": "CMR",
        "correspondent": "MTN_MOMO_CMR",
        "payer": {
            "type": "MSISDN",
            "address": {
                "value": numero
            }
        },
        "customerTimestamp": "2026-05-25T12:00:00Z",
        "statementDescription": "Cotisation tontine"
    }

    response = requests.post(
        f"{BASE_URL}/deposits",
        json=payload,
        headers=headers
    )

    return response.json()