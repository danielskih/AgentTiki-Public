import os
import requests
from config import API_BASE, PROVIDER_ID

LISTINGS_API_BASE = os.getenv(
    "LISTINGS_API_BASE",
    "https://6ie3irwugc.execute-api.us-east-1.amazonaws.com/prod",
)
CONTRACTS_API_BASE = os.getenv("CONTRACTS_API_BASE", API_BASE)
NEGOTIATION_API_BASE = os.getenv("NEGOTIATION_API_BASE", LISTINGS_API_BASE)
ACTORS_API_BASE = os.getenv("ACTORS_API_BASE", LISTINGS_API_BASE)

_ACTOR_ID = None
_API_KEY = None


def configure_credentials(actor_id, api_key):
    global _ACTOR_ID, _API_KEY
    _ACTOR_ID = actor_id
    _API_KEY = api_key


def auth_headers():
    if not _API_KEY:
        raise RuntimeError("API key not set")
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {_API_KEY}",
    }


def _json_or_error(response):
    try:
        return response.json()
    except Exception:
        return {
            "error": {
                "code": "HTTP_ERROR",
                "message": f"HTTP {response.status_code}: non-JSON response",
            }
        }


def register_actor():
    r = requests.post(
        f"{ACTORS_API_BASE}/actors/v1",
        headers={"Content-Type": "application/json"},
        json={"action": "register"},
        timeout=30,
    )
    return r.json()


def create_listing(intent, offer, trust_score=0.9):
    payload = {
        "version": "v1",
        "intent": intent,
        "offer": offer,
        "trust_score": trust_score,
        "negotiation_supported": True,
    }
    r = requests.post(
        f"{LISTINGS_API_BASE}/listings/ingest/v1",
        headers=auth_headers(),
        json=payload,
        timeout=30,
    )
    return r.json()


def get_contract(contract_id):
    r = requests.get(
        f"{CONTRACTS_API_BASE}/contracts/v1/{contract_id}",
        headers=auth_headers(),
        timeout=30,
    )
    return r.json()


def discover_contracts(status="ACTIVE"):
    response = requests.get(
        f"{CONTRACTS_API_BASE}/contracts/v1/provider?status={status}",
        headers=auth_headers(),
        timeout=30,
    )
    return _json_or_error(response)


def discover_open_negotiations():
    response = requests.get(
        f"{NEGOTIATION_API_BASE}/negotiate/v2/provider-OPEN",
        headers=auth_headers(),
        timeout=30,
    )
    if response.status_code == 404:
        response = requests.get(
            f"{NEGOTIATION_API_BASE}/negotiations/v2/provider-OPEN",
            headers=auth_headers(),
            timeout=30,
        )
    return _json_or_error(response)


def accept_negotiation(negotiation_id):
    response = requests.post(
        f"{NEGOTIATION_API_BASE}/negotiate/v2/{negotiation_id}/accept",
        headers=auth_headers(),
        json={"version": "v2"},
        timeout=30,
    )
    if response.status_code == 404:
        response = requests.post(
            f"{NEGOTIATION_API_BASE}/negotiations/v2/{negotiation_id}/accept",
            headers=auth_headers(),
            json={"version": "v2"},
            timeout=30,
        )
    return _json_or_error(response)


def propose_negotiation(negotiation_id, proposal):
    response = requests.post(
        f"{NEGOTIATION_API_BASE}/negotiate/v2/{negotiation_id}/propose",
        headers=auth_headers(),
        json={"version": "v2", "proposal": proposal},
        timeout=30,
    )
    if response.status_code == 404:
        response = requests.post(
            f"{NEGOTIATION_API_BASE}/negotiations/v2/{negotiation_id}/propose",
            headers=auth_headers(),
            json={"version": "v2", "proposal": proposal},
            timeout=30,
        )
    return _json_or_error(response)


def get_negotiation(negotiation_id):
    response = requests.get(
        f"{NEGOTIATION_API_BASE}/negotiate/v2/{negotiation_id}",
        headers=auth_headers(),
        timeout=30,
    )
    if response.status_code == 404:
        response = requests.get(
            f"{NEGOTIATION_API_BASE}/negotiations/v2/{negotiation_id}",
            headers=auth_headers(),
            timeout=30,
        )
    return _json_or_error(response)


def reject_negotiation(negotiation_id):
    response = requests.post(
        f"{NEGOTIATION_API_BASE}/negotiate/v2/{negotiation_id}/reject",
        headers=auth_headers(),
        json={"version": "v2"},
        timeout=30,
    )
    if response.status_code == 404:
        response = requests.post(
            f"{NEGOTIATION_API_BASE}/negotiations/v2/{negotiation_id}/reject",
            headers=auth_headers(),
            json={"version": "v2"},
            timeout=30,
        )
    return _json_or_error(response)


def accept(negotiation_id):
    return accept_negotiation(negotiation_id)


def propose(negotiation_id, proposal):
    return propose_negotiation(negotiation_id, proposal)


def reject(negotiation_id):
    return reject_negotiation(negotiation_id)


def get_latest_delivery(contract_id):
    r = requests.get(
        f"{CONTRACTS_API_BASE}/contracts/v1/{contract_id}/delivery/latest",
        headers=auth_headers(),
        timeout=30,
    )
    return r.json()


def request_upload(contract_id, files, delivery_type="OUTPUT"):
    r = requests.post(
        f"{CONTRACTS_API_BASE}/contracts/v1/{contract_id}/delivery/upload-intent",
        headers=auth_headers(),
        json={"files": files, "delivery_type": delivery_type},
        timeout=30,
    )
    return r.json()


def confirm_upload(contract_id, files, delivery_type="OUTPUT"):
    r = requests.post(
        f"{CONTRACTS_API_BASE}/contracts/v1/{contract_id}/delivery/confirm",
        headers=auth_headers(),
        json={"files": files, "delivery_type": delivery_type},
        timeout=30,
    )
    return r.json()


def transition(contract_id, to_status):
    return transition_contract(contract_id, to_status, actor_id=_ACTOR_ID or PROVIDER_ID)


def transition_contract(contract_id, to_status, actor_id=None):
    body = {
        "version": "v1",
        "action": "transition",
        "contract_id": contract_id,
        "to_status": to_status,
    }
    if actor_id:
        body["actor_id"] = actor_id

    r = requests.post(
        f"{CONTRACTS_API_BASE}/contracts/v1/transition",
        headers=auth_headers(),
        json=body,
        timeout=30,
    )
    return r.json()


def upload_output(contract_id, files, actor_id=None):
    del actor_id
    return request_upload(contract_id, files, delivery_type="OUTPUT")


def confirm_output(contract_id, files):
    return confirm_upload(contract_id, files, delivery_type="OUTPUT")
