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

| Method | Path               | Body                                            |
|--------|--------------------|-------------------------------------------------|
| GET    | `/health`          | —                                               |
| POST   | `/intake/scan`     | `{ecosystem, package, version}`                 |
| POST   | `/intake/alert`    | simplified scanner JSON (`docs/examples/sample-alert.json`) |
| POST   | `/intake/github`   | GitHub Dependabot alert + `installed_version`   |
| POST   | `/intake/manifest` | `{filename, content}` — scans every pinned dependency |

The first three return one `NormalizedAlert`. `/intake/manifest` returns a
`ManifestScanResult` (counts + a `NormalizedAlert` per dependency).

The manifest parser is chosen by `filename` (suffix match):

| Manifest                       | Ecosystem |
|--------------------------------|-----------|
| `package.json`                 | npm       |
| `requirements.txt` / `.in`     | PyPI      |
| `*.csproj`, `packages.config`  | NuGet     |

### Examples

```bash
# single package
curl -X POST http://127.0.0.1:8000/intake/scan \
  -H "content-type: application/json" \
  -d '{"ecosystem":"npm","package":"lodash","version":"4.17.19"}'

# whole repo manifest (the demo path) — wrap the file as {filename, content}.
# jq -Rs reads the file as a raw string into `content`:
jq -Rs '{filename:"package.json", content:.}' docs/examples/vulnerable-package.json \
  | curl -X POST http://127.0.0.1:8000/intake/manifest \
      -H "content-type: application/json" -d @-
```

`/intake/scan` returns a `NormalizedAlert` with `vulnerable`, `severity`,
`fixed_version`, `cve`, and the distilled `vulnerabilities`. `/intake/manifest`
wraps one of those per dependency, plus a `skipped` list for any dependency
whose version isn't an exact pin (ranges like `^1.2.3`, tags, git/file sources).

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
