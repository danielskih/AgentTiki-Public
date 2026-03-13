from agenttiki_client import get_client


def get_contract(api_key, contract_id):
    client = get_client()
    return client.request_json(
        "GET",
        "CONTRACTS_API_BASE",
        f"/contracts/v1/{contract_id}",
        api_key=api_key,
    )


def transition_contract(api_key, contract_id, to_status):
    client = get_client()
    return client.request_json(
        "POST",
        "CONTRACTS_API_BASE",
        "/contracts/v1/transition",
        api_key=api_key,
        json={
            "version": "v1",
            "action": "transition",
            "contract_id": contract_id,
            "to_status": to_status,
        },
    )


def list_provider_active_contracts(api_key):
    client = get_client()
    return client.request_json(
        "GET",
        "CONTRACTS_API_BASE",
        "/contracts/v1/provider?status=ACTIVE",
        api_key=api_key,
    )


def list_active_contracts(api_key, as_provider=True):
    if as_provider:
        return list_provider_active_contracts(api_key)
    return {
        "error": {
            "code": "UNSUPPORTED_HELPER",
            "message": "No public buyer-side active-contract listing helper is included in this starter kit.",
        }
    }
