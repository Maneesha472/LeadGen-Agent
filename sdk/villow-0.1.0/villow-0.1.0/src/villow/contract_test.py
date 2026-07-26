from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx

from villow.signing import sign_request, verify_request_signature
from villow_contract_schemas import validate_contract_message


@dataclass
class ContractTestCheck:
    name: str
    passed: bool
    detail: str
    remediation: str | None = None


@dataclass
class ContractTestReport:
    endpoint: str
    passed: bool
    checks: list[ContractTestCheck] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_test": "villow.publisher.v1",
            "endpoint": self.endpoint,
            "passed": self.passed,
            "checks": [check.__dict__ for check in self.checks],
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, sort_keys=True)


@dataclass(frozen=True)
class ContractTestCredentials:
    publisher_id: str
    agent_id: str
    signing_key_id: str
    secret: str


class ContractTestRunner:
    def __init__(
        self,
        *,
        endpoint: str,
        credentials: ContractTestCredentials,
        timeout_seconds: float = 5.0,
        transport: httpx.BaseTransport | None = None,
        offline: bool = False,
    ) -> None:
        self.endpoint = endpoint.rstrip("/")
        self.credentials = credentials
        self.offline = offline
        self.client = httpx.Client(timeout=timeout_seconds, transport=transport)

    def run(self) -> ContractTestReport:
        checks = [self._check_signature_verification(), self._check_schema_package()]
        if not self.offline:
            checks.extend(
                [
                    self._check_signed_discover(),
                    self._check_idempotent_replay(),
                    self._check_stale_signature_rejected(),
                    self._check_malformed_prepare_rejected(),
                ]
            )
        return ContractTestReport(endpoint=self.endpoint, passed=all(check.passed for check in checks), checks=checks)

    def _check_signature_verification(self) -> ContractTestCheck:
        body = _json_body({"task_id": "contract_test"})
        headers = self._headers("/discover", body, idempotency_key="contract-test-signature", timestamp=int(time.time()))
        try:
            verify_request_signature("POST", "/discover", body, headers, secret=self.credentials.secret)
        except ValueError as exc:
            return ContractTestCheck("signature_verification", False, str(exc), "Verify Villow HMAC canonicalization.")
        return ContractTestCheck("signature_verification", True, "signed request verifies locally")

    def _check_schema_package(self) -> ContractTestCheck:
        result = validate_contract_message("response.discover", {"publisher_id": "publisher", "agent_id": "agent"})
        if not result.valid:
            return ContractTestCheck("schema_package", False, str(result.errors), "Install the matching villow-contract-schemas package.")
        return ContractTestCheck("schema_package", True, "request, response, and callback schemas are available")

    def _check_signed_discover(self) -> ContractTestCheck:
        response = self._post("/discover", {}, "contract-test-discover")
        if response.status_code >= 500:
            return ContractTestCheck("signed_discover", False, f"HTTP {response.status_code}", "Keep /discover lightweight and non-blocking.")
        if response.status_code >= 400:
            return ContractTestCheck("signed_discover", False, f"HTTP {response.status_code}", "Verify signing credentials and endpoint URL.")
        payload = _response_json(response)
        validation = validate_contract_message("response.discover", payload)
        if not validation.valid:
            return ContractTestCheck("signed_discover", False, str(validation.errors), "Return the documented discover response shape.")
        return ContractTestCheck("signed_discover", True, "signed /discover returned a schema-valid response")

    def _check_idempotent_replay(self) -> ContractTestCheck:
        payload: dict[str, Any] = {}
        first = self._post("/discover", payload, "contract-test-idempotency")
        second = self._post("/discover", payload, "contract-test-idempotency")
        if first.status_code != second.status_code:
            return ContractTestCheck("idempotency", False, "duplicate request returned a different status", "Cache by idempotency key and request hash.")
        return ContractTestCheck("idempotency", True, "duplicate signed request returned a stable status")

    def _check_stale_signature_rejected(self) -> ContractTestCheck:
        body = _json_body({})
        path = "/discover"
        url = self._url(path)
        headers = self._headers(self._request_path(url), body, idempotency_key="contract-test-stale", timestamp=1)
        response = self.client.post(url, content=body, headers={**headers, "content-type": "application/json"})
        if response.status_code not in {400, 401, 403}:
            return ContractTestCheck("timestamp_tolerance", False, f"HTTP {response.status_code}", "Reject stale Villow signatures.")
        return ContractTestCheck("timestamp_tolerance", True, "stale signature was rejected")

    def _check_malformed_prepare_rejected(self) -> ContractTestCheck:
        response = self._post("/prepare", {"task_template": "missing_task_id"}, "contract-test-malformed")
        if response.status_code < 400:
            return ContractTestCheck("malformed_request_handling", False, "malformed prepare was accepted", "Reject missing required fields.")
        return ContractTestCheck("malformed_request_handling", True, f"malformed prepare rejected with HTTP {response.status_code}")

    def _post(self, path: str, payload: dict[str, Any], idempotency_key: str) -> httpx.Response:
        body = _json_body(payload)
        url = self._url(path)
        headers = self._headers(self._request_path(url), body, idempotency_key=idempotency_key)
        headers["content-type"] = "application/json"
        return self.client.post(url, content=body, headers=headers)

    def _headers(self, path: str, body: bytes, *, idempotency_key: str, timestamp: int | None = None) -> dict[str, str]:
        return sign_request(
            method="POST",
            path=path,
            body=body,
            key_id=self.credentials.signing_key_id,
            secret=self.credentials.secret,
            publisher_id=self.credentials.publisher_id,
            agent_id=self.credentials.agent_id,
            idempotency_key=idempotency_key,
            timestamp=timestamp,
        )

    def _url(self, path: str) -> str:
        parsed = urlparse(self.endpoint)
        if parsed.path and parsed.path != "/":
            return urljoin(f"{self.endpoint}/", path.lstrip("/"))
        return urljoin(f"{self.endpoint}/", path.lstrip("/"))

    def _request_path(self, url: str) -> str:
        parsed = urlparse(url)
        return parsed.path or "/"


def _json_body(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")


def _response_json(response: httpx.Response) -> dict[str, Any]:
    try:
        payload = response.json()
    except ValueError:
        return {}
    return payload if isinstance(payload, dict) else {"value": payload}
