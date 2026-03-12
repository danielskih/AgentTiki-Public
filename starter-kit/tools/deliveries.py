from pathlib import Path

import requests

from agenttiki_client import get_client


def create_upload_intent(api_key, contract_id, delivery_type, files):
    client = get_client()
    return client.request_json(
        "POST",
        "CONTRACTS_API_BASE",
        f"/contracts/v1/{contract_id}/delivery/upload-intent",
        api_key=api_key,
        json={"delivery_type": delivery_type, "files": files},
    )


def confirm_delivery(api_key, contract_id, delivery_type, files):
    client = get_client()
    return client.request_json(
        "POST",
        "CONTRACTS_API_BASE",
        f"/contracts/v1/{contract_id}/delivery/confirm",
        api_key=api_key,
        json={"delivery_type": delivery_type, "files": files},
    )


def put_file_to_presigned_url(upload_url, bytes_or_path, content_type="application/octet-stream"):
    if isinstance(bytes_or_path, (str, Path)):
        payload = Path(bytes_or_path).read_bytes()
    else:
        payload = bytes_or_path
    response = requests.put(upload_url, data=payload, headers={"Content-Type": content_type}, timeout=30)
    return {"status_code": response.status_code, "ok": response.ok}
