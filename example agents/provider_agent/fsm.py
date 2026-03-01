import json
import os
import sys

import api

_AGENTS_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _AGENTS_ROOT not in sys.path:
    sys.path.append(_AGENTS_ROOT)

from negotiation_core.decision_engine import decision_engine


def idle(ctx):
    contracts = api.discover_contracts(status="ACTIVE")
    if "error" in contracts:
        print(f"[PROVIDER] contract discovery error: {contracts}")
        return "IDLE"

    contract_items = contracts.get("contracts") or []
    if contract_items:
        contract_id = contract_items[0].get("contract_id")
        if contract_id:
            ctx["contract_id"] = contract_id
            print(f"[PROVIDER] discovered contract {contract_id}")
            return "AWAITING_INPUT"

    discovery = api.discover_open_negotiations()
    if "error" in discovery:
        print(f"[PROVIDER] discovery error: {discovery}")
        return "IDLE"

    negotiations = discovery.get("negotiations") or []
    for negotiation in negotiations:
        status = negotiation.get("status")
        if status and status != "OPEN":
            continue
        ctx["negotiation_id"] = negotiation.get("negotiation_id")
        ctx["offer"] = negotiation.get("offer")
        print(f"[PROVIDER] found negotiation {ctx['negotiation_id']}")
        return "HANDLE_NEGOTIATION"

    if not ctx.get("listing_created"):
        res = api.create_listing(
            intent={
                "service": "translation",
                "from": "en",
                "to": "de",
            },
            offer={
                "price": 1000,
                "currency": "EUR",
                "delivery_days": 3,
            },
            trust_score=0.9,
        )
        if "error" in res:
            print(f"[PROVIDER] listing create error: {res}")
            return "IDLE"

        ctx["listing_created"] = True
        if isinstance(res, dict) and res.get("listing_id"):
            ctx["listing_id"] = res.get("listing_id")
        save_state(ctx)
        print(f"[PROVIDER] listing created: {ctx.get('listing_id')}")
        return "IDLE"

    return "IDLE"


def handle_negotiation(ctx):
    negotiation_id = ctx.get("negotiation_id")
    if not negotiation_id:
        return "IDLE"

    negotiation = api.get_negotiation(negotiation_id)

    if "error" in negotiation:
        print(f"[PROVIDER] negotiation fetch error: {negotiation}")
        return "IDLE"

    status = negotiation.get("status")
    turn = negotiation.get("turn")

    meta = negotiation.get("meta") or {}
    if not status:
        status = meta.get("status")
    if not turn:
        next_actor_id = meta.get("next_actor_id")
        provider_actor_id = meta.get("provider_id") or ctx.get("actor_id") or ctx.get("provider_id")
        if next_actor_id and provider_actor_id:
            turn = "PROVIDER" if next_actor_id == provider_actor_id else "BUYER"

    if status != "OPEN":
        print(f"[PROVIDER] negotiation not open (status={status})")
        return "IDLE"

    if turn != "PROVIDER":
        print("[PROVIDER] waiting for my turn")
        return "IDLE"

    rounds = negotiation.get("rounds") or []
    last_offer = {}
    if rounds:
        last_offer = rounds[-1].get("proposal") or {}

    round_no = meta.get("round_count", len(rounds) or 1)
    ctx["negotiation"] = {
        "status": status,
        "turn": turn,
        "round": round_no,
        "last_offer": last_offer,
    }
    ctx.setdefault("reliability_score", 0.5)

    decision = decision_engine(ctx, role="PROVIDER")

    if decision.action == "ACCEPT":
        response = api.accept(negotiation_id)
        if "error" in response:
            print(f"[PROVIDER] accept error: {response}")
            return "IDLE"

        contract_id = response.get("contract_id")
        if contract_id:
            ctx["contract_id"] = contract_id
            print(f"[PROVIDER] negotiation accepted, contract {contract_id}")
            return "AWAIT_INPUT"
        return "IDLE"

    if decision.action == "PROPOSE":
        proposal = decision.proposal or {
            "price": last_offer.get("price", 1000),
            "delivery_days": last_offer.get("delivery_days", 3),
            "currency": last_offer.get("currency", "EUR"),
            "scope": last_offer.get("scope", "full_document"),
        }
        response = api.propose(negotiation_id, proposal)
        if "error" in response:
            print(f"[PROVIDER] propose error: {response}")
            return "IDLE"
        print(f"[PROVIDER] negotiation proposed {negotiation_id}")
        return "IDLE"

    if decision.action == "REJECT":
        response = api.reject(negotiation_id)
        if "error" in response:
            print(f"[PROVIDER] reject error: {response}")
            return "IDLE"
        print(f"[PROVIDER] negotiation rejected {negotiation_id}")
        return "IDLE"

    return "IDLE"


def awaiting_input(ctx):
    contract_id = ctx.get("contract_id")
    if not contract_id:
        print("[PROVIDER][AWAITING_INPUT] missing contract_id")
        return "IDLE"

    res = api.get_latest_delivery(contract_id)
    if "error" in res:
        print(res)
        return "AWAITING_INPUT"

    if res.get("delivery_type") == "INPUT":
        ctx["input_snapshot_id"] = res.get("snapshot_id")
        ctx["input_files"] = res.get("files")
        return "INPUT_DOWNLOADED"

    return "AWAITING_INPUT"


def await_input(ctx):
    return awaiting_input(ctx)


def input_downloaded(ctx):
    print(f"[PROVIDER][INPUT_DOWNLOADED] snapshot={ctx.get('input_snapshot_id')}")
    return "READY_TO_UPLOAD"


def ready_to_upload(ctx):
    contract_id = ctx.get("contract_id")
    if not contract_id:
        print("[PROVIDER][READY_TO_UPLOAD] missing contract_id")
        return "FAILED"

    result = ready_to_upload_output(ctx)

    if result == "OUTPUT_UPLOADED":
        return "OUTPUT_UPLOADED"

    return "READY_TO_UPLOAD"


def output_uploaded(ctx):
    contract_id = ctx.get("contract_id")

    response = api.transition_contract(contract_id, "SHIPPED")
    if "error" in response:
        print(f"[PROVIDER][OUTPUT_UPLOADED] transition error: {response}")
        return "FAILED"

    print("[PROVIDER][OUTPUT_UPLOADED] marked SHIPPED")
    return "WAITING_CONFIRM"


def waiting_confirm(ctx):
    contract_id = ctx.get("contract_id")

    contract = api.get_contract(contract_id)
    if "error" in contract:
        print(f"[PROVIDER][WAITING_CONFIRM] error: {contract}")
        return "WAITING_CONFIRM"

    status = contract.get("status")

    if status == "FULFILLED":
        return "COMPLETED"

    if status == "BREACHED":
        return "FAILED"

    return "WAITING_CONFIRM"


def completed(ctx):
    print("[PROVIDER][COMPLETED] contract fulfilled")
    return "COMPLETED"


def failed(ctx):
    print("[PROVIDER][FAILED] contract failed")
    return "FAILED"


def ready_to_upload_output(ctx):
    """
    Prepare provider OUTPUT based on buyer INPUT metadata.
    Generate output file(s), upload intent, then PUT to S3.
    """
    import hashlib
    import requests

    contract_id = ctx["contract_id"]

    os.makedirs("output", exist_ok=True)
    output_file_path = "output/result.txt"
    with open(output_file_path, "w") as f:
        f.write(f"Processed input snapshot {ctx.get('input_snapshot_id')}")

    with open(output_file_path, "rb") as f:
        sha256 = hashlib.sha256(f.read()).hexdigest()

    res = api.upload_output(contract_id, [
        {"path": "output/result.txt", "sha256": sha256}
    ])

    if "error" in res:
        print(res)
        return "READY_TO_UPLOAD"

    for file_meta in res.get("files", []):
        with open(output_file_path, "rb") as f:
            upload_res = requests.put(file_meta["upload_url"], data=f)
            if upload_res.status_code not in (200, 201, 204):
                print({"error": "upload_failed", "status_code": upload_res.status_code})
                return "READY_TO_UPLOAD"

    confirm_res = api.confirm_output(contract_id, res.get("files", []))
    if "error" in confirm_res:
        print(confirm_res)
        return "READY_TO_UPLOAD"

    if res.get("files"):
        ctx["output_snapshot_id"] = res["files"][0].get("snapshot_id")
        ctx["output_files"] = res["files"]

    return "OUTPUT_UPLOADED"


FSM = {
    "IDLE": idle,
    "HANDLE_NEGOTIATION": handle_negotiation,
    "AWAIT_INPUT": await_input,
    "AWAITING_INPUT": awaiting_input,
    "INPUT_DOWNLOADED": input_downloaded,
    "READY_TO_UPLOAD": ready_to_upload,
    "OUTPUT_UPLOADED": output_uploaded,
    "WAITING_CONFIRM": waiting_confirm,
    "COMPLETED": completed,
    "FAILED": failed,
}


STATE_FILE = "state.json"


def load_state():
    """
    Load the agent state from state.json
    """
    if not os.path.exists(STATE_FILE):
        return {}
    with open(STATE_FILE, "r") as f:
        return json.load(f)


def save_state(ctx):
    """
    Save the agent state to state.json
    """
    with open(STATE_FILE, "w") as f:
        json.dump(ctx, f, indent=2)
