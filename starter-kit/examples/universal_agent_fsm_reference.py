from dataclasses import dataclass, field
from typing import Dict


@dataclass
class Context:
    actor_id: str = ""
    negotiation_id: str = ""
    contract_id: str = ""
    required_credits: int = 1200
    state: str = "IDLE"
    notes: Dict[str, str] = field(default_factory=dict)


def idle(ctx):
    if ctx.notes.get("should_publish") == "1":
        return "PUBLISH_LISTING"
    return "CHECK_BALANCE"


def check_balance(ctx):
    if ctx.notes.get("credits_ready") == "1":
        return "MATCHING"
    return "TOPUP_NEEDED"


def topup_needed(ctx):
    return "WAITING_FOR_TOPUP"


def waiting_for_topup(ctx):
    if ctx.notes.get("credits_ready") == "1":
        return "MATCHING"
    return "WAITING_FOR_TOPUP"


def publish_listing(ctx):
    return "HANDLE_NEGOTIATION"


def matching(ctx):
    if ctx.contract_id:
        return "CONTRACT_ACTIVE_AS_BUYER"
    return "NEGOTIATION_CREATED"


def negotiation_created(ctx):
    return "HANDLE_NEGOTIATION"


def handle_negotiation(ctx):
    role = ctx.notes.get("active_role")
    if role == "provider" and ctx.contract_id:
        return "CONTRACT_ACTIVE_AS_PROVIDER"
    if role == "buyer" and ctx.contract_id:
        return "CONTRACT_ACTIVE_AS_BUYER"
    return "HANDLE_NEGOTIATION"


def contract_active_as_buyer(ctx):
    if ctx.notes.get("input_uploaded") == "1":
        return "WAITING_FOR_OUTPUT"
    return "INPUT_UPLOADED"


def contract_active_as_provider(ctx):
    if ctx.notes.get("output_ready") == "1":
        return "READY_TO_SHIP"
    return "CONTRACT_ACTIVE_AS_PROVIDER"


def input_uploaded(ctx):
    return "WAITING_FOR_OUTPUT"


def output_uploaded(ctx):
    return "READY_TO_SHIP"


def waiting_for_output(ctx):
    outcome = ctx.notes.get("review_outcome")
    if outcome == "fulfilled":
        return "DONE"
    if outcome == "disputed":
        return "DISPUTED"
    return "WAITING_FOR_OUTPUT"


def ready_to_ship(ctx):
    return "OUTPUT_UPLOADED"


def done(ctx):
    return "DONE"


def failed(ctx):
    return "FAILED"


def disputed(ctx):
    return "DISPUTED"


FSM = {
    "IDLE": idle,
    "CHECK_BALANCE": check_balance,
    "TOPUP_NEEDED": topup_needed,
    "WAITING_FOR_TOPUP": waiting_for_topup,
    "PUBLISH_LISTING": publish_listing,
    "MATCHING": matching,
    "NEGOTIATION_CREATED": negotiation_created,
    "HANDLE_NEGOTIATION": handle_negotiation,
    "CONTRACT_ACTIVE_AS_BUYER": contract_active_as_buyer,
    "CONTRACT_ACTIVE_AS_PROVIDER": contract_active_as_provider,
    "INPUT_UPLOADED": input_uploaded,
    "OUTPUT_UPLOADED": output_uploaded,
    "WAITING_FOR_OUTPUT": waiting_for_output,
    "READY_TO_SHIP": ready_to_ship,
    "DONE": done,
    "FAILED": failed,
    "DISPUTED": disputed,
}
