import json
import sys
from datetime import datetime, timezone
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parents[1] / "tools"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from auth import load_credentials, register_actor, save_credentials
from contracts import get_contract, list_provider_active_contracts, transition_contract
from deliveries import confirm_delivery, create_upload_intent, put_file_to_presigned_url
from listings import create_listing_v2
from negotiate import accept_negotiation, discover_provider_open_negotiations, reject_negotiation

CREDENTIALS_PATH = Path(__file__).with_name("provider_credentials.json")

INTENT = {
    "category": "data",
    "type": "website_snapshot",
    "attributes": {
        "target": "www.example.com",
        "format": "json",
        "scope": "full_site_data",
    },
}

OFFER = {"price": 1200, "delivery_days": 3, "scope": "standard"}


def ensure_credentials():
    creds = load_credentials(CREDENTIALS_PATH)
    if creds:
        return creds
    created = register_actor()
    save_credentials(CREDENTIALS_PATH, created["actor_id"], created["api_key"])
    return created


def generated_output():
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
    print("Generated deterministic JSON dataset for www.example.com")
    return json.dumps(payload, indent=2).encode("utf-8")


def publish_listing(api_key):
    created = create_listing_v2(api_key, INTENT, OFFER)
    print(json.dumps(created, indent=2))


def maybe_handle_negotiation(api_key):
    discovery = discover_provider_open_negotiations(api_key)
    negotiation = (discovery.get("negotiations") or [None])[0]
    if not negotiation:
        return
    negotiation_id = negotiation.get("negotiation_id")
    offer = negotiation.get("final_offer") or negotiation.get("offer") or {}
    if int(offer.get("price", 0) or 0) >= OFFER["price"]:
        accepted = accept_negotiation(api_key, negotiation_id)
        print(json.dumps(accepted, indent=2))
    else:
        rejected = reject_negotiation(api_key, negotiation_id)
        print(json.dumps(rejected, indent=2))


def maybe_ship_active_contract(api_key):
    contracts = list_provider_active_contracts(api_key)
    contract = (contracts.get("contracts") or [None])[0]
    if not contract:
        return
    contract_id = contract["contract_id"]
    latest = get_contract(api_key, contract_id)
    if latest.get("status") != "ACTIVE":
        return
    body = generated_output()
    files = [{"path": "output/result.json", "content_type": "application/json", "size_bytes": len(body)}]
    intent = create_upload_intent(api_key, contract_id, "OUTPUT", files)
    upload = (intent.get("files") or [{}])[0]
    if upload.get("upload_url"):
        put_file_to_presigned_url(upload["upload_url"], body, "application/json")
        confirm_delivery(api_key, contract_id, "OUTPUT", files)
        transition_contract(api_key, contract_id, "SHIPPED")


def main():
    creds = ensure_credentials()
    api_key = creds["api_key"]
    publish_listing(api_key)
    maybe_handle_negotiation(api_key)
    maybe_ship_active_contract(api_key)


if __name__ == "__main__":
    main()
