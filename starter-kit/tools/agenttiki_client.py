import os
from urllib.parse import urljoin

import requests


DEFAULT_BASES = {
    "LISTINGS_API_BASE": "https://6ie3irwugc.execute-api.us-east-1.amazonaws.com/prod",
    "CONTRACTS_API_BASE": "https://hwvxmctc7b.execute-api.us-east-1.amazonaws.com/prod",
    "NEGOTIATION_API_BASE": None,
    "ACTORS_API_BASE": None,
    "CREDITS_API_BASE": None,
    "PAYMENTS_API_BASE": None,
    "PAYMENTS_PAGE_BASE": "https://d1pe03n554sxy3.cloudfront.net",
}


class AgentTikiClient:
    def __init__(self, timeout=30):
        listings = os.getenv("LISTINGS_API_BASE", DEFAULT_BASES["LISTINGS_API_BASE"]).rstrip("/")
        contracts = os.getenv("CONTRACTS_API_BASE", DEFAULT_BASES["CONTRACTS_API_BASE"]).rstrip("/")
        self.bases = {
            "LISTINGS_API_BASE": listings,
            "CONTRACTS_API_BASE": contracts,
            "NEGOTIATION_API_BASE": os.getenv("NEGOTIATION_API_BASE", listings).rstrip("/"),
            "ACTORS_API_BASE": os.getenv("ACTORS_API_BASE", listings).rstrip("/"),
            "CREDITS_API_BASE": os.getenv("CREDITS_API_BASE", listings).rstrip("/"),
            "PAYMENTS_API_BASE": os.getenv("PAYMENTS_API_BASE", contracts).rstrip("/"),
            "PAYMENTS_PAGE_BASE": os.getenv("PAYMENTS_PAGE_BASE", DEFAULT_BASES["PAYMENTS_PAGE_BASE"]).rstrip("/"),
        }
        self.timeout = timeout
        self.session = requests.Session()

    def auth_headers(self, api_key, content_type=True):
        headers = {"Authorization": f"Bearer {api_key}"}
        if content_type:
            headers["Content-Type"] = "application/json"
        return headers

    def url(self, base_name, path):
        return urljoin(self.bases[base_name] + "/", path.lstrip("/"))

    def request_json(self, method, base_name, path, api_key=None, **kwargs):
        headers = kwargs.pop("headers", {})
        if api_key:
            merged = self.auth_headers(api_key, content_type="json" in kwargs)
            merged.update(headers)
            headers = merged
        response = self.session.request(
            method,
            self.url(base_name, path),
            headers=headers,
            timeout=kwargs.pop("timeout", self.timeout),
            **kwargs,
        )
        request_id = (
            response.headers.get("apigw-requestid")
            or response.headers.get("Apigw-Requestid")
            or response.headers.get("x-amzn-requestid")
            or response.headers.get("X-Amzn-Requestid")
        )
        try:
            payload = response.json()
        except Exception:
            payload = {
                "error": {
                    "code": "HTTP_ERROR",
                    "message": f"HTTP {response.status_code}: non-JSON response",
                }
            }
        if response.status_code >= 400:
            if isinstance(payload, dict) and "error" in payload:
                if isinstance(payload["error"], dict):
                    payload["error"].setdefault("status_code", response.status_code)
                    if request_id:
                        payload["error"].setdefault("request_id", request_id)
                return payload
            return {
                "error": {
                    "code": "HTTP_ERROR",
                    "message": f"HTTP {response.status_code}",
                    "status_code": response.status_code,
                    "request_id": request_id,
                }
            }
        return payload


def get_client():
    return AgentTikiClient()
