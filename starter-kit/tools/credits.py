from agenttiki_client import get_client


def get_balance(api_key):
    client = get_client()
    return client.request_json("GET", "CREDITS_API_BASE", "/credits/v1/balance", api_key=api_key)


def create_topup_session(api_key, credits_amount):
    client = get_client()
    return client.request_json(
        "POST",
        "PAYMENTS_API_BASE",
        "/payments/v1/create",
        api_key=api_key,
        json={"credits_amount": int(credits_amount)},
    )
