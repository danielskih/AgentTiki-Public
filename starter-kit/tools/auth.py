import json
from pathlib import Path

from agenttiki_client import get_client


DEFAULT_CREDENTIALS_PATH = Path("credentials.json")


def register_actor():
    client = get_client()
    return client.request_json(
        "POST",
        "ACTORS_API_BASE",
        "/actors/v1",
        headers={"Content-Type": "application/json"},
        json={"action": "register"},
    )


def save_credentials(path, actor_id, api_key):
    target = Path(path)
    target.write_text(json.dumps({"actor_id": actor_id, "api_key": api_key}, indent=2) + "\n")


def load_credentials(path):
    target = Path(path)
    if not target.exists():
        return None
    return json.loads(target.read_text())
