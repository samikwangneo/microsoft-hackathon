"""Service-level tests with OSV mocked via httpx.MockTransport (no network)."""

import json

import httpx

from app.intake import osv, service
from app.models import Ecosystem, ScanRequest, Severity

# A trimmed real-shaped OSV /v1/query response for lodash 4.17.19.
OSV_RESPONSE = {
    "vulns": [
        {
            "id": "GHSA-jf85-cpcp-j695",
            "aliases": ["CVE-2020-8203"],
            "summary": "Prototype Pollution in lodash",
            "details": "Versions of lodash prior to 4.17.19 are vulnerable...",
            "severity": [
                {"type": "CVSS_V3", "score": "CVSS:3.1/AV:N/AC:H/PR:N/UI:N/S:U/C:H/I:H/A:H"}
            ],
            "affected": [
                {
                    "package": {"ecosystem": "npm", "name": "lodash"},
                    "ranges": [
                        {"type": "SEMVER", "events": [{"introduced": "0"}, {"fixed": "4.17.19"}]}
                    ],
                    "ecosystem_specific": {"severity": "HIGH"},
                }
            ],
            "references": [
                {"type": "ADVISORY", "url": "https://github.com/advisories/GHSA-jf85-cpcp-j695"}
            ],
            "database_specific": {"severity": "HIGH"},
        }
    ]
}


def _mock_client(response_json: dict, status: int = 200) -> httpx.AsyncClient:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/query"
        body = request.read().decode()
        assert "lodash" in body
        return httpx.Response(status, json=response_json)

    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


async def test_normalize_vulnerable_package():
    req = ScanRequest(ecosystem=Ecosystem.NPM, package="lodash", version="4.17.19")
    async with _mock_client(OSV_RESPONSE) as client:
        result = await service.normalize(req, alert_id="ALERT-1", client=client)

    assert result.vulnerable is True
    assert result.severity is Severity.HIGH
    assert result.fixed_version == "4.17.19"
    assert result.cve == "CVE-2020-8203"
    assert result.alert_id == "ALERT-1"
    assert len(result.vulnerabilities) == 1
    assert result.vulnerabilities[0].id == "GHSA-jf85-cpcp-j695"


async def test_normalize_clean_package():
    req = ScanRequest(ecosystem=Ecosystem.NPM, package="lodash", version="4.17.21")
    async with _mock_client({"vulns": []}) as client:
        result = await service.normalize(req, client=client)

    assert result.vulnerable is False
    assert result.severity is Severity.UNKNOWN
    assert result.fixed_version is None
    assert result.cve is None
    assert result.vulnerabilities == []


def _per_package_client() -> httpx.AsyncClient:
    """Returns the lodash vuln for lodash, nothing for anything else."""

    def handler(request: httpx.Request) -> httpx.Response:
        name = json.loads(request.read())["package"]["name"]
        return httpx.Response(200, json=OSV_RESPONSE if name == "lodash" else {"vulns": []})

    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


def test_distill_ignores_git_commit_hashes_for_fixed_version():
    # OSV often lists both a GIT range (commit-hash "fixed") and an ECOSYSTEM
    # range (real version). We must pick the version, never the hash.
    vuln = {
        "id": "GHSA-test",
        "affected": [
            {
                "package": {"ecosystem": "PyPI", "name": "django"},
                "ranges": [
                    {"type": "GIT", "events": [{"introduced": "0"}, {"fixed": "eb31d845323618d688ad429479c6dda973056136"}]},
                    {"type": "ECOSYSTEM", "events": [{"introduced": "0"}, {"fixed": "2.2.28"}]},
                ],
            }
        ],
    }
    req = ScanRequest(ecosystem=Ecosystem.PYPI, package="django", version="2.2.0")
    assert osv.distill(vuln, req).fixed_version == "2.2.28"


async def test_scan_many_scans_each_package():
    reqs = [
        ScanRequest(ecosystem=Ecosystem.NPM, package="lodash", version="4.17.19"),
        ScanRequest(ecosystem=Ecosystem.NPM, package="minimist", version="1.2.5"),
    ]
    async with _per_package_client() as client:
        results = await service.scan_many(reqs, client=client)

    assert [r.package for r in results] == ["lodash", "minimist"]
    assert results[0].vulnerable is True
    assert results[1].vulnerable is False
