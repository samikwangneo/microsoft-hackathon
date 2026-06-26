# Validation Service — Build Plan (buildable now)

> Owner: Israel Ogwu. This is an execution plan for an agent/teammate to build the
> Validation Service **using only what exists today** (the intake service + the
> defined contracts). No dependency on the not-yet-built Remediation Engine,
> agents, or a demo target repo. Work top-to-bottom; each step ends with a
> **Verify** command and must leave the existing test suite green.

## Scope

In scope (buildable now):
1. Validation **contracts** (Pydantic in/out models), backward-compatible with `contracts/validation_output.json`.
2. **Security re-scan check** — re-query OSV for the upgraded version and confirm it's clean. Reuses the intake `service.normalize` / `OSVClient` directly. Needs no target repo.
3. **Build/test runner** — an ecosystem-aware subprocess runner behind an injectable interface, so it's fully unit-testable today with a fake runner (and runs for real once a target repo exists).
4. **Orchestration service** + **FastAPI route** wired into `app/main.py`.
5. Unit tests for all of the above, following the intake test style (async, mocked, no network).

Deferred (blocked on others — do NOT attempt here): real end-to-end build/test against a live target repo (needs a sample repo from the team), camelCase↔snake_case boundary mapping with the Remediation Engine, and the dashboard wiring (frontend owns that; we just emit the contract).

## Where it lives

```
backend/app/validation/
  __init__.py
  models.py        # ValidationRequest, CheckResult, ValidationReport
  security.py      # security_rescan() — reuses app.intake.service.normalize
  runner.py        # build/test runner + injectable CommandRunner
  service.py       # validate() — orchestrates security + build/test -> ValidationReport
backend/app/routes/validation.py   # POST /validation/run
backend/app/main.py                # + app.include_router(validation.router)
backend/tests/
  test_validation_security.py
  test_validation_runner.py
  test_validation_service.py
```

## Conventions (copy these from intake — don't reinvent)

- `from __future__ import annotations`, full type hints, short docstrings.
- snake_case fields internally (matches `app/models.py`).
- Async orchestration; **dependency injection for I/O** so tests never hit network or shell:
  - OSV: accept an `httpx.AsyncClient` (intake's `normalize(..., client=...)` already supports this).
  - Subprocess: accept a `CommandRunner` callable; the default uses real subprocess, tests pass a fake.
- Tests use `asyncio_mode = auto` (already set in `pytest.ini`) — plain `async def test_*`, no markers. Reference pattern: `tests/test_service.py` (`httpx.MockTransport`).
- Reuse, don't duplicate: `Ecosystem`/`ScanRequest` from `app/models.py`; `normalize`/`OSVClient` from `app/intake`.

---

## Step 0 — Baseline & orient

**Goal:** green starting point and template loaded.

- Read `backend/app/intake/service.py`, `osv.py`, `routes/intake.py`, `tests/test_service.py` — these are the template for everything below.
- Set up env and confirm existing tests pass.

**Verify:**
```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # .venv/Scripts/activate on Windows
pip install -r requirements-dev.txt
python -m pytest -q          # must be green before you change anything
```

---

## Step 1 — Contracts (`app/validation/models.py`)

**Goal:** lock the in/out interface. Output must stay backward-compatible with `contracts/validation_output.json` (keys: `alert_id`, `passed`, `tests_run`, `notes`) and add a `checks` list for the dashboard's per-check view.

```python
from __future__ import annotations
from pydantic import BaseModel, Field
from ..models import Ecosystem   # reuse intake's enum


class ValidationRequest(BaseModel):
    """Input: what the Remediation Engine hands us after bumping a version."""
    alert_id: str | None = None
    ecosystem: Ecosystem = Ecosystem.NPM
    package: str = Field(..., min_length=1)
    updated_version: str = Field(..., min_length=1)   # version we upgraded TO
    previous_version: str | None = None               # for regression context
    repository: str | None = None                     # local checkout path; build/test skipped if absent


class CheckResult(BaseModel):
    name: str            # "security_scan" | "build" | "tests"
    passed: bool
    details: str | None = None


class ValidationReport(BaseModel):
    """Output contract. Superset of contracts/validation_output.json."""
    alert_id: str | None = None
    passed: bool                                       # overall = AND of all checks
    tests_run: int = 0
    checks: list[CheckResult] = Field(default_factory=list)
    notes: str = ""
```

**Acceptance / test (`test_validation_service.py`, add now):** assert a hand-built `ValidationReport(...).model_dump()` contains every key present in `contracts/validation_output.json`. This guards the contract so nobody breaks the demo/dashboard later.

**Verify:** `python -m pytest tests/test_validation_service.py -q`

---

## Step 2 — Security re-scan check (`app/validation/security.py`)

**Goal:** the highest-value, repo-free check. Re-query OSV for `package@updated_version`; pass iff OSV reports it not vulnerable. **Direct reuse of intake** — this is the whole point of doing it now.

```python
from __future__ import annotations
import httpx
from ..config import Settings
from ..intake.service import normalize
from ..models import ScanRequest
from .models import CheckResult, ValidationRequest


async def security_rescan(
    req: ValidationRequest,
    *,
    settings: Settings | None = None,
    client: httpx.AsyncClient | None = None,
) -> CheckResult:
    scan = ScanRequest(
        ecosystem=req.ecosystem, package=req.package, version=req.updated_version
    )
    result = await normalize(scan, settings=settings, client=client)
    passed = not result.vulnerable
    details = (
        f"{req.package}@{req.updated_version} clean per OSV"
        if passed
        else f"{req.package}@{req.updated_version} still vulnerable "
             f"(severity={result.severity.value}, fix={result.fixed_version})"
    )
    return CheckResult(name="security_scan", passed=passed, details=details)
```

**Acceptance / tests (`test_validation_security.py`):** mirror `tests/test_service.py`'s `MockTransport`:
- OSV returns vulns → `passed is False`, details mention "still vulnerable".
- OSV returns `{"vulns": []}` → `passed is True`.
- (Optional) OSV non-2xx surfaces as `httpx.HTTPStatusError` (route layer translates it in Step 5).

**Verify:** `python -m pytest tests/test_validation_security.py -q`

---

## Step 3 — Build/test runner (`app/validation/runner.py`)

**Goal:** ecosystem-aware build+test, behind an injectable interface so it's unit-testable today without any real repo. Real execution lights up later when a target repo exists.

```python
from __future__ import annotations
import asyncio
from collections.abc import Awaitable, Callable
from pathlib import Path
from pydantic import BaseModel
from ..models import Ecosystem
from .models import CheckResult, ValidationRequest


class CommandResult(BaseModel):
    returncode: int
    stdout: str = ""
    stderr: str = ""

# Injectable: tests pass a fake; default runs a real subprocess.
CommandRunner = Callable[[list[str], Path], Awaitable[CommandResult]]

# Minimal per-ecosystem command sets (extend as needed).
_COMMANDS: dict[Ecosystem, list[list[str]]] = {
    Ecosystem.NPM:  [["npm", "ci"], ["npm", "test", "--", "--silent"]],
    Ecosystem.PYPI: [["pip", "install", "-r", "requirements.txt"], ["pytest", "-q"]],
    # Ecosystem.NUGET: [["dotnet", "build"], ["dotnet", "test"]],
}


async def _default_runner(cmd: list[str], cwd: Path) -> CommandResult:
    proc = await asyncio.create_subprocess_exec(
        *cmd, cwd=str(cwd),
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    out, err = await proc.communicate()
    return CommandResult(returncode=proc.returncode or 0,
                         stdout=out.decode(errors="replace"),
                         stderr=err.decode(errors="replace"))


def parse_test_count(output: str) -> int:
    """Best-effort: pull a test count from npm/pytest output. 0 if unknown."""
    import re
    m = re.search(r"(\d+)\s+passed", output)          # pytest: "142 passed"
    return int(m.group(1)) if m else 0


async def run_build_and_tests(
    req: ValidationRequest, *, runner: CommandRunner | None = None
) -> list[CheckResult]:
    """Run build then tests in req.repository. Returns [] if no repo / no commands."""
    if not req.repository:
        return []
    repo = Path(req.repository)
    if not repo.exists():
        return [CheckResult(name="build", passed=False,
                            details=f"repository not found: {req.repository}")]
    commands = _COMMANDS.get(req.ecosystem)
    if not commands:
        return [CheckResult(name="build", passed=False,
                            details=f"no build profile for {req.ecosystem.value}")]
    run = runner or _default_runner
    build_cmd, test_cmd = commands[0], commands[-1]
    checks: list[CheckResult] = []

    b = await run(build_cmd, repo)
    checks.append(CheckResult(name="build", passed=b.returncode == 0,
                              details=" ".join(build_cmd)))
    if not b.passed if hasattr(b, "passed") else b.returncode != 0:
        return checks  # don't run tests on a broken build

    t = await run(test_cmd, repo)
    n = parse_test_count(t.stdout + t.stderr)
    checks.append(CheckResult(name="tests", passed=t.returncode == 0,
                              details=f"{n} tests"))
    return checks
```
> Note: `tests_run` is best-effort (Step 4 pulls it from the `tests` CheckResult); never gate pass/fail on the parsed count.

**Acceptance / tests (`test_validation_runner.py`):** pass a **fake `CommandRunner`** (a small async closure returning canned `CommandResult`s):
- build ok + tests ok → two checks, both passed.
- build fails → only the `build` check, `passed False`, tests not run.
- `repository=None` → returns `[]`.
- `parse_test_count("142 passed")` → `142`; unknown → `0`.

**Verify:** `python -m pytest tests/test_validation_runner.py -q`

---

## Step 4 — Orchestration (`app/validation/service.py`)

**Goal:** combine the checks into one `ValidationReport`. Overall `passed` = all checks passed; `tests_run` from the tests check.

```python
from __future__ import annotations
import httpx
from ..config import Settings
from .models import ValidationReport, ValidationRequest
from .runner import CommandRunner, run_build_and_tests, parse_test_count
from .security import security_rescan


async def validate(
    req: ValidationRequest,
    *,
    settings: Settings | None = None,
    client: httpx.AsyncClient | None = None,
    runner: CommandRunner | None = None,
) -> ValidationReport:
    checks = [await security_rescan(req, settings=settings, client=client)]
    checks += await run_build_and_tests(req, runner=runner)

    tests_check = next((c for c in checks if c.name == "tests"), None)
    tests_run = parse_test_count(tests_check.details or "") if tests_check else 0
    passed = all(c.passed for c in checks)
    notes = "Validation successful" if passed else \
            "; ".join(c.details for c in checks if not c.passed and c.details)

    return ValidationReport(
        alert_id=req.alert_id, passed=passed,
        tests_run=tests_run, checks=checks, notes=notes,
    )
```

**Acceptance / tests (`test_validation_service.py`):** full orchestration with **mocked OSV client + fake runner**:
- clean OSV + passing build/tests → `report.passed is True`, `checks` has security_scan+build+tests, `tests_run` populated.
- vulnerable OSV → `report.passed is False` even if build/tests pass.
- `repository=None` → only the `security_scan` check; still produces a valid report.
- Keep the Step-1 contract-keys test here.

**Verify:** `python -m pytest tests/test_validation_service.py -q`

---

## Step 5 — Route + wiring (`app/routes/validation.py`, `app/main.py`)

**Goal:** expose `POST /validation/run`. Reuse intake's OSV→HTTP error translation.

```python
# app/routes/validation.py
from __future__ import annotations
import httpx
from fastapi import APIRouter, HTTPException
from ..validation import service
from ..validation.models import ValidationReport, ValidationRequest

router = APIRouter(prefix="/validation", tags=["validation"])


@router.post("/run", response_model=ValidationReport)
async def run_validation(req: ValidationRequest) -> ValidationReport:
    try:
        return await service.validate(req)
    except httpx.HTTPStatusError as exc:
        raise HTTPException(502, f"OSV query failed: {exc.response.status_code}") from exc
    except httpx.HTTPError as exc:
        raise HTTPException(504, f"OSV unreachable: {exc}") from exc
```

In `app/main.py`, next to the intake import/include:
```python
from .routes import intake, validation
...
app.include_router(validation.router)
```

**Acceptance / Verify:**
```bash
uvicorn app.main:app --reload
# /validation/run appears in Swagger at http://127.0.0.1:8000/docs
# Repo-free smoke test (real OSV call — a KNOWN-vulnerable version should fail):
curl -s -X POST http://127.0.0.1:8000/validation/run \
  -H 'content-type: application/json' \
  -d '{"alert_id":"OSV-001","ecosystem":"npm","package":"lodash","updated_version":"4.17.19"}'
# expect: passed=false, security_scan check failing.
# A patched version should pass:
#   ...'{"package":"lodash","updated_version":"4.17.21"}' -> passed=true
```
Also run the whole suite: `python -m pytest -q` (still green).

---

## Step 6 — (Stretch, still self-contained) Emit the demo artifact

**Goal:** let validation refresh `contracts/validation_output.json` so the demo and dashboard reflect a real run, without touching the (mock) `demo/pipeline_runner.py` flow.

- Add `app/validation/__main__.py` (or a `cli.py`) that builds a `ValidationRequest` from argv, calls `validate()`, and writes `report.model_dump()` to `contracts/validation_output.json`.
- Because `ValidationReport` is a superset of the contract, the existing `demo/pipeline_runner.py` keeps working unchanged.

**Verify:** `python -m app.validation <args>` writes valid JSON; `python demo/pipeline_runner.py` still runs and `validationPassed` reflects it.

---

## Definition of done (for "now")

- [ ] `app/validation/{models,security,runner,service}.py` + `routes/validation.py` implemented, wired into `main.py`.
- [ ] `POST /validation/run` works against real OSV for the security check; returns the `ValidationReport` contract.
- [ ] Build/test runner unit-tested via a fake `CommandRunner` (real execution deferred to a target repo).
- [ ] New tests pass and **existing intake tests stay green** (`python -m pytest -q`).
- [ ] `ValidationReport` remains a superset of `contracts/validation_output.json`.

## Hand-off notes / decisions for the team (don't decide solo)

- **Field-naming at boundaries:** intake/validation use snake_case; the Remediation Engine contract (`agents/remediation-engine/remedition_contract.json`) and the validation README input use camelCase (`updatedVersion`, `fixedVersion`). Agree on a mapping where remediation calls validation.
- **Target repo:** real build/test (Step 3 execution, Step 6 e2e) needs a small sample app fixture from the team. Until then the security re-scan check is the demoable path.
