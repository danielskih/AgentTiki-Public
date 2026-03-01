import json

from negotiation_core.negotiation_decision import NegotiationDecision
from negotiation_core import llm

MAX_ROUNDS = 5
DEFAULT_DELIVERY_DAYS = 3
COUNTER_FACTOR = 0.05
PROVIDER_MIN_FACTOR = 0.85
BUYER_MAX_FACTOR = 1.15


def decision_engine(ctx: dict, role: str, ask_fn=None) -> NegotiationDecision:
    negotiation = ctx.get("negotiation") or {}
    ask = ask_fn or llm.ask
    try:
        prompt = build_context(ctx, role)
        raw = ask(prompt)
        decision = parse_llm_output(raw)
        return clamp(decision, ctx, role)
    except Exception:
        return deterministic_fallback(ctx, role)


def build_context(ctx, role):
    negotiation = ctx.get("negotiation") or {}
    last_offer = negotiation.get("last_offer") or {}
    round_count = _to_int(negotiation.get("round_count") or negotiation.get("round") or 1)
    max_rounds = _to_int(negotiation.get("max_rounds") or MAX_ROUNDS)
    base_price = _base_price(ctx, negotiation)

    if role == "PROVIDER":
        threshold = max(1.0, base_price * PROVIDER_MIN_FACTOR)
        objective = "maximize provider value while preserving conversion"
    else:
        threshold = max(1.0, base_price * BUYER_MAX_FACTOR)
        objective = "minimize buyer spend while preserving acceptance odds"

    return f"""
You are a negotiation engine.
Role: {role}
Objective: {objective}
Round: {round_count}
Max rounds: {max_rounds}
Reference price: {base_price}
Acceptance threshold: {threshold}

Last offer:
price={last_offer.get("price")}
delivery_days={last_offer.get("delivery_days")}
currency={last_offer.get("currency")}
scope={last_offer.get("scope")}

Return JSON only:
{{
  "action": "ACCEPT|PROPOSE|REJECT",
  "proposal": {{
    "price": number,
    "delivery_days": number,
    "currency": "string",
    "scope": "string"
  }}
}}
"""


def parse_llm_output(text):
    raw = (text or "").strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    data = json.loads(raw)
    action = str(data.get("action", "")).upper()
    if action not in ("ACCEPT", "PROPOSE", "REJECT"):
        raise ValueError("Invalid action")

    proposal = data.get("proposal")
    return NegotiationDecision(action=action, proposal=proposal)


def clamp(decision, ctx, role):
    negotiation = ctx.get("negotiation") or {}
    last_offer = negotiation.get("last_offer") or {}
    round_count = _to_int(negotiation.get("round_count") or negotiation.get("round") or 1)
    max_rounds = _to_int(negotiation.get("max_rounds") or MAX_ROUNDS)
    base_price = _base_price(ctx, negotiation)
    current_price = _to_float(last_offer.get("price"), 0)
    provider_min_price = max(1.0, base_price * PROVIDER_MIN_FACTOR)
    buyer_max_price = max(1.0, base_price * BUYER_MAX_FACTOR)

    if round_count >= max_rounds:
        return NegotiationDecision(action="REJECT", proposal=None)

    if role == "PROVIDER":
        buyer_price = current_price
        if buyer_price >= provider_min_price:
            return NegotiationDecision(action="ACCEPT", proposal=None)

    if role == "BUYER":
        provider_price = current_price
        if provider_price <= buyer_max_price:
            return NegotiationDecision(action="ACCEPT", proposal=None)

    if decision.action != "PROPOSE":
        return decision

    proposal = decision.proposal if isinstance(decision.proposal, dict) else {}
    price_ctx = _price_ctx(ctx, negotiation)
    price = next_price(role, price_ctx)
    if price == "REJECT":
        return NegotiationDecision(action="REJECT", proposal=None)

    delivery_days = _to_int(proposal.get("delivery_days"), _to_int(last_offer.get("delivery_days"), DEFAULT_DELIVERY_DAYS))
    currency = proposal.get("currency") or last_offer.get("currency") or "EUR"
    scope = proposal.get("scope") or last_offer.get("scope") or "standard"

    if price <= 0:
        price = _base_price(ctx, negotiation)
    if delivery_days <= 0:
        delivery_days = DEFAULT_DELIVERY_DAYS
    if not currency:
        currency = "EUR"
    if not scope:
        scope = "standard"

    if role == "PROVIDER":
        floor = max(1.0, base_price * PROVIDER_MIN_FACTOR)
        price = max(price, floor)
    else:
        ceiling = max(1.0, base_price * BUYER_MAX_FACTOR)
        price = min(price, ceiling)

    last_price = _to_float(last_offer.get("price"), 0)
    if last_price > 0 and abs(price - last_price) < 1e-9:
        if role == "PROVIDER":
            price = max(last_price + 1, price)
        else:
            price = max(1.0, last_price - 1)

    return NegotiationDecision(
        action="PROPOSE",
        proposal={
            "price": int(round(price)),
            "delivery_days": int(delivery_days),
            "currency": str(currency),
            "scope": str(scope),
        },
    )


def deterministic_fallback(ctx, role):
    negotiation = ctx.get("negotiation") or {}
    last_offer = negotiation.get("last_offer") or {}
    round_count = _to_int(negotiation.get("round_count") or negotiation.get("round") or 1)
    max_rounds = _to_int(negotiation.get("max_rounds") or MAX_ROUNDS)

    base_price = _base_price(ctx, negotiation)
    last_price = _to_float(last_offer.get("price"), base_price)
    delivery_days = _to_int(last_offer.get("delivery_days"), DEFAULT_DELIVERY_DAYS)
    currency = last_offer.get("currency") or "EUR"
    scope = last_offer.get("scope") or "standard"

    if round_count >= max_rounds:
        return NegotiationDecision(action="REJECT")

    if role == "PROVIDER":
        acceptable = max(1.0, base_price * PROVIDER_MIN_FACTOR)
        if last_price >= acceptable:
            return NegotiationDecision(action="ACCEPT")
    else:
        acceptable = max(1.0, base_price * BUYER_MAX_FACTOR)
        if last_price <= acceptable:
            return NegotiationDecision(action="ACCEPT")

    price_ctx = _price_ctx(ctx, negotiation)
    counter_price = next_price(role, price_ctx)
    if counter_price == "REJECT":
        return NegotiationDecision(action="REJECT")

    return NegotiationDecision(
        action="PROPOSE",
        proposal={
            "price": int(round(counter_price)),
            "delivery_days": int(max(1, delivery_days)),
            "currency": str(currency),
            "scope": str(scope),
        },
    )


def next_price(role, ctx):
    r = _to_float(ctx.get("round"), 1)
    R = _to_float(ctx.get("max_rounds"), MAX_ROUNDS)
    if R <= 0:
        R = MAX_ROUNDS
    progress = r / R
    progress = max(0.0, min(1.0, progress))

    B_max = _to_float(ctx.get("buyer_max"), 0)
    P_min = _to_float(ctx.get("provider_min"), 0)

    gap = B_max - P_min
    if gap < 0:
        return "REJECT"

    alpha = _to_float(ctx.get("alpha", 0.5), 0.5)
    alpha = max(0.0, min(1.0, alpha))
    target = P_min + alpha * gap

    if role == "BUYER":
        return B_max - (1 - progress) * (B_max - target)

    if role == "PROVIDER":
        return P_min + (1 - progress) * (target - P_min)

    return "REJECT"


def _price_ctx(ctx, negotiation):
    base_price = _base_price(ctx, negotiation)
    round_count = _to_int(negotiation.get("round_count") or negotiation.get("round") or 1)
    max_rounds = _to_int(negotiation.get("max_rounds") or MAX_ROUNDS)

    provider_min = _to_float(ctx.get("provider_min"), max(1.0, base_price * PROVIDER_MIN_FACTOR))
    buyer_max = _to_float(ctx.get("buyer_max"), max(1.0, base_price * BUYER_MAX_FACTOR))

    return {
        "round": round_count,
        "max_rounds": max_rounds,
        "buyer_max": buyer_max,
        "provider_min": provider_min,
        "alpha": ctx.get("alpha", 0.5),
    }


def _base_price(ctx, negotiation):
    for container in (
        ctx.get("final_offer"),
        ctx.get("offer"),
        ctx.get("selected_match"),
        negotiation.get("anchor_offer") if isinstance(negotiation, dict) else None,
        negotiation.get("last_offer") if isinstance(negotiation, dict) else None,
    ):
        if isinstance(container, dict):
            price = container.get("price")
            if isinstance(price, (int, float)) and price > 0:
                return float(price)
    return 1000.0


def _to_int(value, default=0):
    try:
        return int(value)
    except Exception:
        return int(default)


def _to_float(value, default=0.0):
    try:
        return float(value)
    except Exception:
        return float(default)
