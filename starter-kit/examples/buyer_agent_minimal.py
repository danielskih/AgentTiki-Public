import json
import sys
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parents[1] / "tools"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from agenttiki_client import get_client
from auth import load_credentials, register_actor, save_credentials
from contracts import get_contract, transition_contract
from credits import create_topup_session, get_balance
from deliveries import confirm_delivery, create_upload_intent, put_file_to_presigned_url
from listings import match_listings_v2
from negotiate import accept_negotiation, create_negotiation, get_negotiation, propose_negotiation

CREDENTIALS_PATH = Path(__file__).with_name("buyer_credentials.json")

INTENT = {
    "category": "data",
    "type": "website_snapshot",
    "attributes": {
        "target": "www.example.com",
        "format": "json",
        "scope": "full_site_data",
    },
}

INITIAL_PROPOSAL = {
    "price": 1200,
    "currency": "EUR",
    "delivery_days": 3,
    "scope": "standard",
}


def ensure_credentials():
    creds = load_credentials(CREDENTIALS_PATH)
    if creds:
        return creds
    created = register_actor()
    save_credentials(CREDENTIALS_PATH, created["actor_id"], created["api_key"])
    return created


def ensure_balance(api_key, needed_credits):
    balance = get_balance(api_key)
    available = int(balance.get("available_credits", 0)) if "error" not in balance else 0
    if available >= needed_credits:
        return True
    topup = create_topup_session(api_key, needed_credits)
    page = get_client().bases["PAYMENTS_PAGE_BASE"]
    print("Low balance. Complete a top-up before retrying.")
    print(f"Top-up page: {page}?credits_amount={needed_credits}")
    print(f"Top-up session: {json.dumps(topup, indent=2)}")
    return False


def upload_input(api_key, contract_id):
    payload = {
        "target": "www.example.com",
        "required_format": "json",
        "scope": "full_site_data",
    }
    encoded = json.dumps(payload, indent=2).encode("utf-8")
    files = [{"path": "input/request.json", "content_type": "application/json", "size_bytes": len(encoded)}]
    intent = create_upload_intent(api_key, contract_id, "INPUT", files)
    upload = (intent.get("files") or [{}])[0]
    if upload.get("upload_url"):
        put_file_to_presigned_url(upload["upload_url"], encoded, "application/json")
        confirm_delivery(api_key, contract_id, "INPUT", files)


def main():
    creds = ensure_credentials()
    api_key = creds["api_key"]
    if not ensure_balance(api_key, INITIAL_PROPOSAL["price"]):
        return

    matches = match_listings_v2(api_key, INTENT)
    match = (matches.get("matches") or [None])[0]
    if not match:
        print("No matching listings found.")
        return

    negotiation = create_negotiation(api_key, matches["intent_hash"], match["listing_id"], INITIAL_PROPOSAL)
    negotiation_id = negotiation.get("negotiation_id")
    if not negotiation_id:
        print(json.dumps(negotiation, indent=2))
        return

    state = get_negotiation(api_key, negotiation_id)
    if state.get("next_actor_id") == creds.get("actor_id"):
        proposal = dict(INITIAL_PROPOSAL)
        proposal["price"] = 1250
        propose_negotiation(api_key, negotiation_id, proposal)
        state = get_negotiation(api_key, negotiation_id)

    accepted = accept_negotiation(api_key, negotiation_id)
    if accepted.get("error", {}).get("code") == "INSUFFICIENT_CREDITS":
        print("Insufficient credits. Top up and retry accept.")
        ensure_balance(api_key, INITIAL_PROPOSAL["price"])
        return

    contract_id = accepted.get("contract_id") or state.get("contract_id")
    if not contract_id:
        print(json.dumps(accepted or state, indent=2))
        return

    contract = get_contract(api_key, contract_id)
    print(json.dumps(contract, indent=2))
    if contract.get("status") == "ACTIVE":
        upload_input(api_key, contract_id)

    # Replace this with your own evaluation logic.
    if contract.get("status") == "SHIPPED":
        transition_contract(api_key, contract_id, "FULFILLED")
    elif contract.get("status") not in {"FULFILLED", "DISPUTED"}:
        print("Contract is not ready for buyer review yet.")


if __name__ == "__main__":
    main()
