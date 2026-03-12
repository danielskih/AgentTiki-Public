from dataclasses import dataclass, field
from typing import Dict


@dataclass
class Context:
    contract_id: str = ""
    negotiation_id: str = ""
    state: str = "IDLE"
    notes: Dict[str, str] = field(default_factory=dict)


def idle(ctx):
    if ctx.notes.get("listing_ready") == "1":
        return "HANDLE_NEGOTIATION"
    return "LISTING_READY"


def listing_ready(ctx):
    return "HANDLE_NEGOTIATION"


def handle_negotiation(ctx):
    if ctx.notes.get("negotiation_outcome") == "rejected":
        return "FAILED"
    if ctx.contract_id:
        return "CONTRACT_ACTIVE"
    return "HANDLE_NEGOTIATION"


def contract_active(ctx):
    return "OUTPUT_UPLOADED"


def output_uploaded(ctx):
    return "SHIPPED"


def shipped(ctx):
    outcome = ctx.notes.get("contract_outcome")
    if outcome == "fulfilled":
        return "DONE"
    if outcome == "disputed":
        return "DISPUTED"
    return "SHIPPED"


def done(ctx):
    return "DONE"


def disputed(ctx):
    return "DISPUTED"


def failed(ctx):
    return "FAILED"


FSM = {
    "IDLE": idle,
    "LISTING_READY": listing_ready,
    "HANDLE_NEGOTIATION": handle_negotiation,
    "CONTRACT_ACTIVE": contract_active,
    "OUTPUT_UPLOADED": output_uploaded,
    "SHIPPED": shipped,
    "DONE": done,
    "DISPUTED": disputed,
    "FAILED": failed,
}
