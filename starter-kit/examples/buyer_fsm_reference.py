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
    return "MATCHING"


def matching(ctx):
    if ctx.contract_id:
        return "CONTRACT_ACTIVE"
    return "NEGOTIATION_CREATED"


def negotiation_created(ctx):
    return "WAITING_FOR_PROVIDER"


def waiting_for_provider(ctx):
    if ctx.notes.get("insufficient_credits") == "1":
        return "PAYMENT_TOPUP_NEEDED"
    if ctx.contract_id:
        return "CONTRACT_ACTIVE"
    return "WAITING_FOR_PROVIDER"


def payment_topup_needed(ctx):
    return "WAITING_FOR_TOPUP"


def waiting_for_topup(ctx):
    if ctx.notes.get("credits_ready") == "1":
        return "NEGOTIATION_CREATED"
    return "WAITING_FOR_TOPUP"


def contract_active(ctx):
    return "INPUT_UPLOADED"


def input_uploaded(ctx):
    return "WAITING_FOR_OUTPUT"


def waiting_for_output(ctx):
    outcome = ctx.notes.get("review_outcome")
    if outcome == "fulfilled":
        return "DONE"
    if outcome == "disputed":
        return "DISPUTED"
    return "WAITING_FOR_OUTPUT"


def done(ctx):
    return "DONE"


def disputed(ctx):
    return "DISPUTED"


def failed(ctx):
    return "FAILED"


FSM = {
    "IDLE": idle,
    "MATCHING": matching,
    "NEGOTIATION_CREATED": negotiation_created,
    "WAITING_FOR_PROVIDER": waiting_for_provider,
    "PAYMENT_TOPUP_NEEDED": payment_topup_needed,
    "WAITING_FOR_TOPUP": waiting_for_topup,
    "CONTRACT_ACTIVE": contract_active,
    "INPUT_UPLOADED": input_uploaded,
    "WAITING_FOR_OUTPUT": waiting_for_output,
    "DONE": done,
    "DISPUTED": disputed,
    "FAILED": failed,
}
