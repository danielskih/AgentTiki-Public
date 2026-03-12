from agenttiki_client import get_client


def _request_with_fallback(method, api_key, primary_path, fallback_path=None, **kwargs):
    client = get_client()
    response = client.request_json(method, "NEGOTIATION_API_BASE", primary_path, api_key=api_key, **kwargs)
    if fallback_path and response.get("error", {}).get("status_code") == 404:
        return client.request_json(method, "NEGOTIATION_API_BASE", fallback_path, api_key=api_key, **kwargs)
    return response


def create_negotiation(api_key, intent_hash, listing_id, proposal, max_rounds=5, expiry_seconds=900):
    payload = {
        "version": "v2",
        "intent_hash": intent_hash,
        "listing_id": listing_id,
        "proposal": proposal,
        "max_rounds": max_rounds,
        "expiry_seconds": expiry_seconds,
    }
    return _request_with_fallback(
        "POST",
        api_key,
        "/negotiate/v2",
        "/negotiations/v2",
        json=payload,
    )


def get_negotiation(api_key, negotiation_id):
    return _request_with_fallback(
        "GET",
        api_key,
        f"/negotiate/v2/{negotiation_id}",
        f"/negotiations/v2/{negotiation_id}",
    )


def propose_negotiation(api_key, negotiation_id, proposal):
    return _request_with_fallback(
        "POST",
        api_key,
        f"/negotiate/v2/{negotiation_id}/propose",
        f"/negotiations/v2/{negotiation_id}/propose",
        json={"proposal": proposal},
    )


def accept_negotiation(api_key, negotiation_id):
    return _request_with_fallback(
        "POST",
        api_key,
        f"/negotiate/v2/{negotiation_id}/accept",
        f"/negotiations/v2/{negotiation_id}/accept",
    )


def reject_negotiation(api_key, negotiation_id):
    return _request_with_fallback(
        "POST",
        api_key,
        f"/negotiate/v2/{negotiation_id}/reject",
        f"/negotiations/v2/{negotiation_id}/reject",
    )


def discover_provider_open_negotiations(api_key):
    return _request_with_fallback(
        "GET",
        api_key,
        "/negotiate/v2/provider-OPEN",
        "/negotiations/v2/provider-OPEN",
    )
