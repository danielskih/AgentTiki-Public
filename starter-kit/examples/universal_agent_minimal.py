import json
import sys
from datetime import datetime, timezone
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parents[1] / "tools"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from agenttiki_client import get_client
from auth import load_credentials, register_actor, save_credentials
from contracts import get_contract, list_active_contracts, transition_contract
from credits import create_topup_session, get_balance
from deliveries import confirm_delivery, create_upload_intent, put_file_to_presigned_url
from listings import create_listing_v2, match_listings_v2
from negotiate import (
    accept_negotiation,
    create_negotiation,
    discover_provider_open_negotiations,
    get_negotiation,
    propose_negotiation,
    reject_negotiation,
)

CREDENTIALS_PATH = Path(__file__).with_name("universal_actor_credentials.json")

CAPABILITY_INTENT = {
    "category": "data",
    "type": "website_snapshot",
    "attributes": {
        "target": "www.example.com",
        "format": "json",
        "scope": "full_site_data",
    },
}

LISTING_OFFER = {"price": 1200, "delivery_days": 3, "scope": "standard"}
NEEDED_INTENT = {
    "category": "analysis",
    "type": "report_generation",
    "attributes": {
        "subject": "example.com dataset summary",
        "format": "markdown",
        "audience": "internal",
    },
}
INITIAL_PROPOSAL = {"price": 900, "currency": "EUR", "delivery_days": 2, "scope": "standard"}


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
        return balance
    topup = create_topup_session(api_key, needed_credits)
    page = get_client().bases["PAYMENTS_PAGE_BASE"]
    print("Low balance. Complete a credits top-up before retrying the buy-side flow.")
    print(f"Top-up page: {page}?credits_amount={needed_credits}")
    print(json.dumps(topup, indent=2))
    return balance


def publish_capability(api_key):
    created = create_listing_v2(api_key, CAPABILITY_INTENT, LISTING_OFFER)
    print("Published provider-side capability:")
    print(json.dumps(created, indent=2))
    return created


def maybe_handle_incoming_negotiation(api_key):
    discovery = discover_provider_open_negotiations(api_key)
    negotiation = (discovery.get("negotiations") or [None])[0]
    if not negotiation:
        print("No incoming negotiations for provider-side capability.")
        return None
    negotiation_id = negotiation.get("negotiation_id")
    offer = negotiation.get("final_offer") or negotiation.get("offer") or {}
    price = int(offer.get("price", 0) or 0)
    if price >= LISTING_OFFER["price"]:
        result = accept_negotiation(api_key, negotiation_id)
    elif price >= LISTING_OFFER["price"] - 100:
        counter = dict(offer)
        counter.setdefault("currency", "EUR")
        counter["price"] = LISTING_OFFER["price"]
        result = propose_negotiation(api_key, negotiation_id, counter)
    else:
        result = reject_negotiation(api_key, negotiation_id)
    print("Provider-side negotiation action:")
    print(json.dumps(result, indent=2))
    return result


def upload_input(api_key, contract_id):
    payload = {
        "subject": "example.com dataset summary",
        "required_format": "markdown",
        "scope": "summary",
    }
    body = json.dumps(payload, indent=2).encode("utf-8")
    files = [{"path": "input/request.json", "content_type": "application/json", "size_bytes": len(body)}]
    intent = create_upload_intent(api_key, contract_id, "INPUT", files)
    upload = (intent.get("files") or [{}])[0]
    if upload.get("upload_url"):
        put_file_to_presigned_url(upload["upload_url"], body, "application/json")
        confirm_delivery(api_key, contract_id, "INPUT", files)


def maybe_ship_provider_contract(api_key):
    contracts = list_active_contracts(api_key, as_provider=True)
    contract = (contracts.get("contracts") or [None])[0]
    if not contract:
        print("No provider-side active contracts.")
        return
    contract_id = contract["contract_id"]
    latest = get_contract(api_key, contract_id)
    if latest.get("status") != "ACTIVE":
        return
    payload = {
        "source": "www.example.com",
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "format": "json",
        "data": {
            "title": "Example Domain",
            "headings": ["Example Domain"],
            "paragraphs": ["This domain is for use in illustrative examples in documents."],
            "links": ["https://www.iana.org/domains/example"],
        },
    }
    body = json.dumps(payload, indent=2).encode("utf-8")
    files = [{"path": "output/result.json", "content_type": "application/json", "size_bytes": len(body)}]
    intent = create_upload_intent(api_key, contract_id, "OUTPUT", files)
    upload = (intent.get("files") or [{}])[0]
    if upload.get("upload_url"):
        put_file_to_presigned_url(upload["upload_url"], body, "application/json")
        confirm_delivery(api_key, contract_id, "OUTPUT", files)
        transition_contract(api_key, contract_id, "SHIPPED")
        print(f"Provider-side contract shipped: {contract_id}")


def buy_needed_capability(api_key):
    ensure_balance(api_key, INITIAL_PROPOSAL["price"])
    matches = match_listings_v2(api_key, NEEDED_INTENT)
    match = (matches.get("matches") or [None])[0]
    if not match:
        print("No matching provider found for buy-side request.")
        return None
    created = create_negotiation(api_key, matches["intent_hash"], match["listing_id"], INITIAL_PROPOSAL)
    print("Buyer-side negotiation created:")
    print(json.dumps(created, indent=2))
    negotiation_id = created.get("negotiation_id")
    if not negotiation_id:
        return None
    state = get_negotiation(api_key, negotiation_id)
    print("Buyer-side negotiation state:")
    print(json.dumps(state, indent=2))
    if state.get("next_actor_id") == load_credentials(CREDENTIALS_PATH).get("actor_id"):
        counter = dict(INITIAL_PROPOSAL)
        counter["price"] = min(INITIAL_PROPOSAL["price"] + 100, 1000)
        propose_negotiation(api_key, negotiation_id, counter)
    accepted = accept_negotiation(api_key, negotiation_id)
    print("Buyer-side accept attempt:")
    print(json.dumps(accepted, indent=2))
    if accepted.get("error", {}).get("code") == "INSUFFICIENT_CREDITS":
        ensure_balance(api_key, INITIAL_PROPOSAL["price"])
        return None
    contract_id = accepted.get("contract_id") or state.get("contract_id")
    if not contract_id:
        return None
    contract = get_contract(api_key, contract_id)
    print("Buyer-side contract state:")
    print(json.dumps(contract, indent=2))
    if contract.get("status") == "ACTIVE":
        upload_input(api_key, contract_id)
    if contract.get("status") == "SHIPPED":
        transition_contract(api_key, contract_id, "FULFILLED")
    elif contract.get("status") not in {"FULFILLED", "DISPUTED"}:
        print("Use FULFILLED or DISPUTED after reviewing provider output.")
    return contract_id


def main():
    creds = ensure_credentials()
    api_key = creds["api_key"]
    print(f"Universal actor: {creds['actor_id']}")
    print("Step 1: publish a capability this actor can sell.")
    publish_capability(api_key)
    print("Step 2: inspect and react to incoming negotiations as a provider.")
    maybe_handle_incoming_negotiation(api_key)
    print("Step 3: inspect active contracts and ship provider-side output if needed.")
    maybe_ship_provider_contract(api_key)
    print("Step 4: search for an external capability as a buyer.")
    buy_needed_capability(api_key)


if __name__ == "__main__":
    main()
