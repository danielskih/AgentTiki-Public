import hashlib
import json
import os
import sys
import time

import api
import llm

_AGENTS_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _AGENTS_ROOT not in sys.path:
    sys.path.append(_AGENTS_ROOT)

from negotiation_core.decision_engine import decision_engine

STATE_FILE = "state.json"


# --- State persistence ---
def load_state():
    if not os.path.exists(STATE_FILE):
        return {}
    with open(STATE_FILE, "r") as file_handle:
        return json.load(file_handle)


def save_state(ctx):
    with open(STATE_FILE, "w") as file_handle:
        json.dump(ctx, file_handle, indent=2)


# --- FSM handlers ---
def idle(ctx):
    if ctx.get("contract_id"):
        return "WAITING_FOR_OUTPUT"
    return "MATCHING"


def matching(ctx):
    if ctx.get("contract_id"):
        return "CONTRACT_CREATED"

    intent = ctx.get("intent") or {
        "service": "translation",
        "from": "en",
        "to": "de",
    }

    match_response = api.match_intent(intent)
    if "error" in match_response:
        print(f"[MATCHING] match error: {match_response}")
        return "MATCHING"

    matches = match_response.get("matches") or []
    if not matches:
        print("[BUYER][MATCHING] no matches")
        return "MATCHING"

    selected_match = matches[0]
    listing_id = selected_match.get("listing_id")
    print(f"[MATCHING] selected listing_id: {listing_id}")
    provider_id = api.derive_provider_id(listing_id)

    if not provider_id:
        print(f"[MATCHING] unable to derive provider_id from listing_id={listing_id}")
        return "FAILED"

    intent_hash = match_response.get("intent_hash")
    if not intent_hash:
        print("[MATCHING] missing intent_hash in match response")
        return "FAILED"

    final_offer = {
        "price": selected_match.get("price", 0),
        "currency": "EUR",
        "delivery_days": 3,
        "scope": "full_document",
    }

    negotiation_response = api.create_negotiation(
        intent_hash=intent_hash,
        provider_id=provider_id,
        offer=final_offer,
        listing_id=listing_id,
    )

    if "error" in negotiation_response:
        print(f"[MATCHING] negotiation create error: {negotiation_response} (listing_id={listing_id})")
        return "FAILED"

    ctx["intent"] = intent
    ctx["intent_hash"] = intent_hash
    ctx["selected_match"] = selected_match
    ctx["listing_id"] = listing_id
    ctx["negotiation_id"] = negotiation_response.get("negotiation_id")
    ctx["provider_id"] = provider_id
    ctx["final_offer"] = final_offer

    print("[MATCHING] negotiation created")
    return "WAITING_FOR_PROVIDER"


def negotiation_created(ctx):
    print(f"[NEGOTIATION_CREATED] waiting for provider acceptance")
    return "WAITING_FOR_PROVIDER"


def handle_negotiation(ctx):
    negotiation_id = ctx.get("negotiation_id")
    if not negotiation_id:
        return "IDLE"

    negotiation = api.get_negotiation(negotiation_id)
    if "error" in negotiation:
        print(f"[BUYER] negotiation fetch error: {negotiation}")
        return "IDLE"

    meta = negotiation.get("meta") or {}
    status = negotiation.get("status")
    if not status:
        status = meta.get("status")
    if status == "ACCEPTED":
        print("[BUYER] negotiation accepted — creating contract flow")
        contract_id = negotiation.get("contract_id") or meta.get("contract_id")
        if not contract_id:
            print("[BUYER] ACCEPTED but missing contract_id")
            return "FAILED"
        ctx["contract_id"] = contract_id
        return "CONTRACT_CREATED"
    if status != "OPEN":
        print(f"[BUYER] negotiation closed ({status})")
        return "IDLE"

    next_actor = negotiation.get("next_actor_id")
    if not next_actor:
        next_actor = meta.get("next_actor_id")

    if next_actor != ctx.get("actor_id"):
        return "WAITING_FOR_PROVIDER"

    rounds = negotiation.get("rounds") or []
    last_offer = negotiation.get("last_offer") or {}
    if not last_offer and rounds:
        last_offer = rounds[-1].get("proposal") or {}
    ctx["negotiation"] = {
        "status": status,
        "round_count": negotiation.get("round_count") or meta.get("round_count", 1),
        "max_rounds": negotiation.get("max_rounds") or meta.get("max_rounds", 5),
        "next_actor_id": next_actor,
        "last_offer": last_offer,
        "anchor_offer": ctx.get("final_offer"),
    }

    decision = decision_engine(ctx, role="BUYER", ask_fn=llm.ask)

    if decision.action == "ACCEPT":
        print("[BUYER] accepting proposal")
        res = api.accept(negotiation_id)
        if "error" in res:
            print(f"[BUYER] accept error: {res}")
            return "WAITING_FOR_PROVIDER"
        contract_id = res.get("contract_id")
        if not contract_id:
            print("[BUYER] ACCEPT response missing contract_id")
            return "WAITING_FOR_PROVIDER"
        ctx["contract_id"] = contract_id
        return "CONTRACT_CREATED"

    if decision.action == "PROPOSE":
        if not decision.proposal:
            return "WAITING_FOR_PROVIDER"
        res = api.propose(negotiation_id, decision.proposal)
        if "error" in res:
            print(f"[BUYER] propose error: {res}")
            return "WAITING_FOR_PROVIDER"
        return "WAITING_FOR_PROVIDER"

    if decision.action == "REJECT":
        res = api.reject(negotiation_id)
        if "error" in res:
            print(f"[BUYER] reject error: {res}")
            return "WAITING_FOR_PROVIDER"
        return "FAILED"

    return "WAITING_FOR_PROVIDER"


def waiting_for_provider(ctx):
    negotiation = api.get_negotiation(ctx["negotiation_id"])
    if "error" in negotiation:
        return "WAITING_FOR_PROVIDER"

    meta = negotiation.get("meta") or {}
    status = negotiation.get("status") or meta.get("status")
    if status == "ACCEPTED":
        print("[BUYER] negotiation accepted — creating contract flow")
        contract_id = negotiation.get("contract_id") or meta.get("contract_id")
        if not contract_id:
            print("[BUYER] ACCEPTED but missing contract_id")
            return "FAILED"

        ctx["contract_id"] = contract_id
        return "CONTRACT_CREATED"

    if status != "OPEN":
        print(f"[BUYER] negotiation closed ({status})")
        return "IDLE"

    if negotiation.get("next_actor_id") == ctx.get("actor_id") or meta.get("next_actor_id") == ctx.get("actor_id"):
        return "HANDLE_NEGOTIATION"

    return "WAITING_FOR_PROVIDER"


def negotiation_accepted(ctx):
    return "WAITING_FOR_PROVIDER"


def contract_created(ctx):
    contract_id = ctx.get("contract_id")
    if not contract_id:
        print("[CONTRACT_CREATED] missing contract_id")
        return "FAILED"

    input_dir = "input"
    os.makedirs(input_dir, exist_ok=True)
    local_input_path = os.path.join(input_dir, "input.txt")

    with open(local_input_path, "w") as file_handle:
        file_handle.write(f"buyer input for contract {contract_id}\n")
        file_handle.write("translate this content from EN to DE\n")

    with open(local_input_path, "rb") as file_handle:
        sha256 = hashlib.sha256(file_handle.read()).hexdigest()

    files = [{"path": "input/input.txt", "sha256": sha256}]

    upload_intent_response = api.upload_input_intent(contract_id, files)
    if "error" in upload_intent_response:
        print(f"[CONTRACT_CREATED] upload-intent error: {upload_intent_response}")
        return "CONTRACT_CREATED"

    presigned_files = upload_intent_response.get("files") or []
    if not presigned_files:
        print("[CONTRACT_CREATED] upload-intent returned no files")
        return "CONTRACT_CREATED"

    for file_meta in presigned_files:
        if not api.upload_to_presigned(file_meta.get("upload_url"), local_input_path):
            print(f"[CONTRACT_CREATED] presigned upload failed: {file_meta}")
            return "CONTRACT_CREATED"

    confirm_response = api.confirm_input(contract_id, presigned_files)
    if "error" in confirm_response:
        print(f"[CONTRACT_CREATED] confirm error: {confirm_response}")
        return "CONTRACT_CREATED"

    ctx["input_snapshot_id"] = presigned_files[0].get("snapshot_id")
    ctx["input_files"] = presigned_files
    print(f"[CONTRACT_CREATED] input uploaded for contract {contract_id}")

    return "INPUT_UPLOADED"


def input_uploaded(ctx):
    return "WAITING_FOR_OUTPUT"


def waiting_for_output(ctx):
    contract_id = ctx.get("contract_id")
    if not contract_id:
        print("[WAITING_FOR_OUTPUT] missing contract_id")
        return "FAILED"

    latest_response = api.get_latest_delivery(contract_id)
    if "error" in latest_response:
        print(f"[WAITING_FOR_OUTPUT] latest error: {latest_response}")
        return "WAITING_FOR_OUTPUT"

    if latest_response.get("delivery_type") != "OUTPUT":
        return "WAITING_FOR_OUTPUT"

    ctx["output_snapshot_id"] = latest_response.get("snapshot_id")
    ctx["output_files"] = latest_response.get("files") or []
    ctx["output_timestamp"] = latest_response.get("timestamp")

    print(f"[WAITING_FOR_OUTPUT] output detected: {ctx.get('output_snapshot_id')}")
    return "REVIEWING"


def reviewing(ctx):
    contract_id = ctx.get("contract_id")
    if not contract_id:
        print("[REVIEWING] missing contract_id")
        return "FAILED"

    download_response = api.download_latest(contract_id)
    if "error" in download_response:
        print(f"[REVIEWING] download metadata error: {download_response}")
        return "FAILED"

    download_url = download_response.get("download_url")
    expected_sha256 = download_response.get("sha256")
    local_output_path = os.path.join("downloads", f"{contract_id}_output.bin")

    if download_url:
        downloaded = api.download_from_presigned(download_url, local_output_path)
        if not downloaded:
            print("[REVIEWING] failed to download presigned output")
            return "FAILED"

        if expected_sha256:
            with open(local_output_path, "rb") as file_handle:
                actual_sha256 = hashlib.sha256(file_handle.read()).hexdigest()
            if actual_sha256 != expected_sha256:
                print("[REVIEWING] output hash mismatch; marking BREACHED")
                transition_response = api.transition_contract(contract_id, "BREACHED")
                print(f"[REVIEWING] transition response: {transition_response}")
                return "FAILED"

    decision = ctx.get("review_decision", "FULFILLED")
    if decision not in ("FULFILLED", "BREACHED"):
        decision = "FULFILLED"

    transition_response = api.transition_contract(contract_id, decision)
    if "error" in transition_response:
        print(f"[REVIEWING] transition error: {transition_response}")
        return "FAILED"

    print(f"[REVIEWING] contract transitioned to {decision}")
    if decision == "FULFILLED":
        return "ACCEPTED"
    return "FAILED"


def accepted(ctx):
    print("[BUYER][ACCEPTED] contract fulfilled")
    return "ACCEPTED"


def failed(ctx):
    return "FAILED"


FSM = {
    "IDLE": idle,
    "MATCHING": matching,
    "NEGOTIATION_CREATED": negotiation_created,
    "HANDLE_NEGOTIATION": handle_negotiation,
    "NEGOTIATION_ACCEPTED": negotiation_accepted,
    "WAITING_FOR_PROVIDER": waiting_for_provider,
    "CONTRACT_CREATED": contract_created,
    "INPUT_UPLOADED": input_uploaded,
    "WAITING_FOR_OUTPUT": waiting_for_output,
    "REVIEWING": reviewing,
    "ACCEPTED": accepted,
    "FAILED": failed,
}
