"""Security re-scan tests — OSV mocked via httpx.MockTransport (no network).

Mirrors tests/test_service.py: the OSV client is injected, so these run offline.
"""

import httpx

from app.validation.models import ValidationRequest
from app.validation.security import security_rescan

# A trimmed real-shaped OSV /v1/query hit (HIGH-severity lodash vuln).
OSV_VULN_RESPONSE = {
    "vulns": [
        {
            "id": "GHSA-jf85-cpcp-j695",
            "aliases": ["CVE-2020-8203"],
            "summary": "Prototype Pollution in lodash",
            "affected": [
                {
                    "package": {"ecosystem": "npm", "name": "lodash"},
                    "ranges": [
                        {"type": "SEMVER", "events": [{"introduced": "0"}, {"fixed": "4.17.21"}]}
                    ],
                    "ecosystem_specific": {"severity": "HIGH"},
                }
            ],
            "database_specific": {"severity": "HIGH"},
        }
    ]
}


def _mock_client(response_json: dict, status: int = 200) -> httpx.AsyncClient:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/query"
        return httpx.Response(status, json=response_json)

    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


async def test_rescan_fails_when_upgraded_version_still_vulnerable():
    req = ValidationRequest(package="lodash", updated_version="4.17.19")
    async with _mock_client(OSV_VULN_RESPONSE) as client:
        check = await security_rescan(req, client=client)

    assert check.name == "security_scan"
    assert check.passed is False
    assert "still vulnerable" in check.details


async def test_rescan_passes_when_upgraded_version_is_clean():
    req = ValidationRequest(package="lodash", updated_version="4.17.21")
    async with _mock_client({"vulns": []}) as client:
        check = await security_rescan(req, client=client)

    assert check.passed is True
    assert "clean per OSV" in check.details


async def test_rescan_propagates_osv_http_error():
    # A non-2xx from OSV surfaces as an httpx error for the route layer to map.
    import pytest

    req = ValidationRequest(package="lodash", updated_version="4.17.21")
    async with _mock_client({"error": "boom"}, status=500) as client:
        with pytest.raises(httpx.HTTPStatusError):
            await security_rescan(req, client=client)
