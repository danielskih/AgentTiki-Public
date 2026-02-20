import os
import requests


LISTINGS_API_BASE = os.getenv(
    "LISTINGS_API_BASE",
    "https://6ie3irwugc.execute-api.us-east-1.amazonaws.com/prod",
)
CONTRACTS_API_BASE = os.getenv(
    "CONTRACTS_API_BASE",
    "https://hwvxmctc7b.execute-api.us-east-1.amazonaws.com/prod",
)
NEGOTIATION_API_BASE = os.getenv("NEGOTIATION_API_BASE", LISTINGS_API_BASE)
ACTORS_API_BASE = os.getenv("ACTORS_API_BASE", LISTINGS_API_BASE)

_API_KEY = None
_ACTOR_ID = None


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
        payload = response.json()
    except Exception:
        payload = {
            "error": {
                "code": "HTTP_ERROR",
                "message": f"HTTP {response.status_code}: non-JSON response",
            }
        }

    if response.status_code >= 400:
        if isinstance(payload, dict) and "error" in payload:
            return payload
        return {
            "error": {
                "code": "HTTP_ERROR",
                "message": f"HTTP {response.status_code}",
            }
        }

    return payload


def register_actor():
    response = requests.request(
        "POST",
        f"{ACTORS_API_BASE}/actors/v1",
        headers={"Content-Type": "application/json"},
        json={"action": "register"},
        timeout=30,
    )
    return _json_or_error(response)


def match_intent(intent):
    response = requests.post(
        f"{LISTINGS_API_BASE}/listings/match/v1",
        headers=auth_headers(),
        json={"version": "v1", "intent": intent},
        timeout=30,
    )
    return _json_or_error(response)


def match(intent):
    return match_intent(intent)


def create_contract(contract_id, intent_hash, provider_id, final_offer, negotiation_id="manual_v1"):
    payload = {
        "version": "v1",
        "action": "create",
        "contract_id": contract_id,
        "negotiation_id": negotiation_id,
        "intent_hash": intent_hash,
        "provider_id": provider_id,
        "final_offer": final_offer,
    }
    response = requests.post(
        f"{CONTRACTS_API_BASE}/contracts/v1",
        headers=auth_headers(),
        json=payload,
        timeout=30,
    )
    return _json_or_error(response)


def create_negotiation(provider_id, intent_hash, offer, listing_id=None):
    payload = {
        "version": "v2",
        "provider_id": provider_id,
        "intent_hash": intent_hash,
        "listing_id": listing_id,
        "offer": offer,
        "proposal": offer,
    }

    response = requests.post(
        f"{NEGOTIATION_API_BASE}/negotiate/v2",
        headers=auth_headers(),
        json=payload,
        timeout=30,
    )
    if response.status_code == 404:
        response = requests.post(
            f"{NEGOTIATION_API_BASE}/negotiations/v2",
            headers=auth_headers(),
            json=payload,
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


def propose_negotiation(negotiation_id, proposal):
    response = requests.post(
        f"{NEGOTIATION_API_BASE}/negotiate/v2/{negotiation_id}/propose",
        headers=auth_headers(),
        json={
            "proposal": proposal
        },
        timeout=30,
    )
    if response.status_code == 404:
        response = requests.post(
            f"{NEGOTIATION_API_BASE}/negotiations/v2/{negotiation_id}/propose",
            headers=auth_headers(),
            json={
                "proposal": proposal
            },
            timeout=30,
        )
    return _json_or_error(response)


def accept_negotiation(negotiation_id):
    response = requests.post(
        f"{NEGOTIATION_API_BASE}/negotiate/v2/{negotiation_id}/accept",
        headers=auth_headers(),
        timeout=30,
    )
    if response.status_code == 404:
        response = requests.post(
            f"{NEGOTIATION_API_BASE}/negotiations/v2/{negotiation_id}/accept",
            headers=auth_headers(),
            timeout=30,
        )
    return _json_or_error(response)


def reject_negotiation(negotiation_id):
    response = requests.post(
        f"{NEGOTIATION_API_BASE}/negotiate/v2/{negotiation_id}/reject",
        headers=auth_headers(),
        timeout=30,
    )
    if response.status_code == 404:
        response = requests.post(
            f"{NEGOTIATION_API_BASE}/negotiations/v2/{negotiation_id}/reject",
            headers=auth_headers(),
            timeout=30,
        )
    return _json_or_error(response)


def accept(negotiation_id):
    return accept_negotiation(negotiation_id)


def propose(negotiation_id, proposal):
    return propose_negotiation(negotiation_id, proposal)


def reject(negotiation_id):
    return reject_negotiation(negotiation_id)


def get_contract(contract_id):
    response = requests.get(
        f"{CONTRACTS_API_BASE}/contracts/v1/{contract_id}",
        headers=auth_headers(),
        timeout=30,
    )
    return _json_or_error(response)


def get_latest_delivery(contract_id):
    response = requests.get(
        f"{CONTRACTS_API_BASE}/contracts/v1/{contract_id}/delivery/latest",
        headers=auth_headers(),
        timeout=30,
    )
    return _json_or_error(response)


def request_upload(contract_id, files, delivery_type="OUTPUT"):
    print("[DEBUG] request_upload called")
    headers = auth_headers()
    print("[DEBUG] request_upload headers:", headers)

    r = requests.post(
        f"{CONTRACTS_API_BASE}/contracts/v1/{contract_id}/delivery/upload-intent",
        headers=headers,
        json={"files": files, "delivery_type": delivery_type},
        timeout=30,
    )
    return _json_or_error(r)


def upload_input_intent(contract_id, files):
    print("[DEBUG] upload_input_intent URL:",
      f"{CONTRACTS_API_BASE}/contracts/v1/{contract_id}/delivery/upload-intent")
    response = requests.post(
        f"{CONTRACTS_API_BASE}/contracts/v1/{contract_id}/delivery/upload-intent",
        headers=auth_headers(),
        json={"files": files, "delivery_type": "INPUT"},
        timeout=30,
    )
    return _json_or_error(response)


def confirm_upload(contract_id, files, delivery_type="INPUT"):
    response = requests.post(
        f"{CONTRACTS_API_BASE}/contracts/v1/{contract_id}/delivery/confirm",
        headers=auth_headers(),
        json={"delivery_type": delivery_type, "files": files},
        timeout=30,
    )
    return _json_or_error(response)


def confirm_input(contract_id, files):
    return confirm_upload(contract_id, files, delivery_type="INPUT")


def transition_contract(contract_id, to_status):
    payload = {
        "version": "v1",
        "action": "transition",
        "contract_id": contract_id,
        "to_status": to_status,
    }
    response = requests.post(
        f"{CONTRACTS_API_BASE}/contracts/v1",
        headers=auth_headers(),
        json=payload,
        timeout=30,
    )
    return _json_or_error(response)


def download_latest(contract_id):
    response = requests.get(
        f"{CONTRACTS_API_BASE}/contracts/v1/{contract_id}/delivery/download",
        headers=auth_headers(),
        timeout=30,
    )
    return _json_or_error(response)


def download_from_presigned(download_url, local_path):
    response = requests.request("GET", download_url, timeout=60)
    if response.status_code != 200:
        return False

    directory = os.path.dirname(local_path)
    if directory:
        os.makedirs(directory, exist_ok=True)

    with open(local_path, "wb") as output_file:
        output_file.write(response.content)
    return True


def upload_to_presigned(upload_url, local_path):
    with open(local_path, "rb") as input_file:
        response = requests.put(upload_url, data=input_file, timeout=60)
    return response.status_code in (200, 201, 204)


def derive_provider_id(listing_id):
    if not isinstance(listing_id, str) or not listing_id:
        return None
    if "-" in listing_id:
        return listing_id.rsplit("-", 1)[0]
    return listing_id
