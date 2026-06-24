# PatchPilot Backend

FastAPI backend hosting the **Vulnerability Intake Service** (Samik's area).

Intake receives a vulnerability alert, looks the package up against
[OSV.dev](https://osv.dev) — the **source of truth** — and emits a single
`NormalizedAlert` for the downstream Summary Agent / Case Identifier.

## Layout

```
app/
  config.py          Settings (OSV base URL, CORS origins, timeout)
  models.py          Pydantic schemas — NormalizedAlert is the output contract
  ecosystems.py      GitHub->OSV ecosystem map + severity/version helpers
  intake/
    osv.py           Async OSV client + vuln distillation
    parsers.py       Scanner alert / GitHub alert -> ScanRequest
    service.py       normalize(): input -> OSV -> NormalizedAlert
  routes/intake.py   POST /intake/{scan,alert,github}
  main.py            FastAPI app + CORS + GET /health
tests/               Parser tests + service tests (OSV mocked, no network)
```

## Run

```bash
cd backend
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt      # Windows
# source .venv/bin/activate && pip install -r requirements.txt   # macOS/Linux

uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000/docs for interactive Swagger.

## Endpoints

| Method | Path             | Body                                            |
|--------|------------------|-------------------------------------------------|
| GET    | `/health`        | —                                               |
| POST   | `/intake/scan`   | `{ecosystem, package, version}`                 |
| POST   | `/intake/alert`  | simplified scanner JSON (`docs/examples/sample-alert.json`) |
| POST   | `/intake/github` | GitHub Dependabot alert + `installed_version`   |

### Example

```bash
curl -X POST http://127.0.0.1:8000/intake/scan \
  -H "content-type: application/json" \
  -d '{"ecosystem":"npm","package":"lodash","version":"4.17.19"}'
```

Returns a `NormalizedAlert` with `vulnerable`, `severity`, `fixed_version`,
`cve`, and the full list of distilled `vulnerabilities`.

## Configuration

Copy `.env.example` to `.env` to override defaults. None are required — OSV.dev
is unauthenticated and alerts are POSTed in.

## Tests

```bash
.venv/Scripts/pip install -r requirements-dev.txt
.venv/Scripts/python -m pytest          # OSV mocked; no network
```

## Notes

- Supported ecosystems (MVP): npm, PyPI, NuGet — behind the `ecosystems.py` map.
- GitHub Dependabot alerts omit the installed version, so `/intake/github`
  requires the caller to supply `installed_version`.
