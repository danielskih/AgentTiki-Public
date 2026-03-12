from agenttiki_client import get_client


def create_listing_v2(api_key, intent, offer, trust_score=0.9, negotiation_supported=True):
    client = get_client()
    return client.request_json(
        "POST",
        "LISTINGS_API_BASE",
        "/listings/ingest/v2",
        api_key=api_key,
        json={
            "version": "v2",
            "intent": intent,
            "offer": offer,
            "trust_score": trust_score,
            "negotiation_supported": negotiation_supported,
        },
    )


def match_listings_v2(api_key, intent):
    client = get_client()
    return client.request_json(
        "POST",
        "LISTINGS_API_BASE",
        "/listings/match/v2",
        api_key=api_key,
        json={"version": "v2", "intent": intent},
    )
