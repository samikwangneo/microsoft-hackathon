"""Pluggable manifest parsers: a dependency file -> ScanRequests.

One parser per ecosystem, all returning the same `(list[ScanRequest],
list[SkippedDependency])` shape. `parse()` dispatches on filename.

Per the locked "pinned versions only" rule, each parser accepts only exact
versions and reports anything else (ranges, tags, MSBuild props, non-registry
sources) under `skipped` rather than guessing what's installed.

Supported:
- package.json        (npm)
- requirements.txt    (PyPI)
- *.csproj            (NuGet, <PackageReference>)
- packages.config     (NuGet)
"""

from __future__ import annotations

import json
import re
from xml.etree import ElementTree

from ..models import (
    Ecosystem,
    PackageJson,
    ScanRequest,
    SkippedDependency,
)

ParseResult = tuple[list[ScanRequest], list[SkippedDependency]]

_NOT_PINNED = "not a pinned version (range, tag, or non-registry source)"


def _skip(package: str, spec: str) -> SkippedDependency:
    return SkippedDependency(package=package, version_spec=spec, reason=_NOT_PINNED)


# --------------------------------------------------------------------------
# Per-ecosystem version pinning
# --------------------------------------------------------------------------

# npm: exact semver (an = or v prefix is still exact); ^, ~, ranges -> skip.
_NPM_EXACT = re.compile(r"^[=v]?\s*(\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.\-+]+)?)$")
# PyPI: only `==x` / `===x` is an exact pin.
_PYPI_EXACT = re.compile(r"^===?\s*([0-9][0-9A-Za-z.\-_+!]*)$")
# NuGet: a bare version (2-4 numeric parts, optional prerelease). Bracket/paren
# ranges and floating `1.2.*` are rejected by the explicit char check below.
_NUGET_EXACT = re.compile(r"^\d+(?:\.\d+){0,3}(?:-[0-9A-Za-z.\-]+)?$")


def pin_npm(spec: str) -> str | None:
    m = _NPM_EXACT.match((spec or "").strip())
    return m.group(1) if m else None


def pin_pypi(spec: str) -> str | None:
    m = _PYPI_EXACT.match((spec or "").strip())
    return m.group(1) if m else None


def pin_nuget(spec: str) -> str | None:
    v = (spec or "").strip()
    if not v or v.startswith("$"):  # empty or MSBuild property ref
        return None
    if any(c in v for c in "[](),*"):  # version range or floating
        return None
    return v if _NUGET_EXACT.match(v) else None


def _normalize_pypi(name: str) -> str:
    """PEP 503 normalization — OSV stores PyPI names in this canonical form."""

    return re.sub(r"[-_.]+", "-", name).lower()


# --------------------------------------------------------------------------
# Parsers
# --------------------------------------------------------------------------


def parse_package_json(content: str) -> ParseResult:
    pkg = PackageJson.model_validate(json.loads(content))
    reqs: list[ScanRequest] = []
    skipped: list[SkippedDependency] = []
    for name, spec in {**pkg.dependencies, **pkg.dev_dependencies}.items():
        version = pin_npm(spec)
        if version is None:
            skipped.append(_skip(name, spec))
        else:
            reqs.append(ScanRequest(ecosystem=Ecosystem.NPM, package=name, version=version))
    return reqs, skipped


# name[extras] optionally followed by the version specifier(s)
_REQ_LINE = re.compile(r"^([A-Za-z0-9][A-Za-z0-9._-]*)\s*(?:\[[^\]]*\])?\s*(.*)$")


def parse_requirements(content: str) -> ParseResult:
    reqs: list[ScanRequest] = []
    skipped: list[SkippedDependency] = []
    for raw in content.splitlines():
        line = raw.split("#", 1)[0].strip()  # drop comments
        if not line or line.startswith("-"):  # blank or option/-r/-e directive
            continue
        line = line.split(";", 1)[0].strip()  # drop environment markers
        m = _REQ_LINE.match(line)
        if not m:
            continue
        name, spec = m.group(1), m.group(2).strip()
        version = pin_pypi(spec)
        if version is None:
            skipped.append(_skip(name, spec or "(no version)"))
        else:
            reqs.append(
                ScanRequest(
                    ecosystem=Ecosystem.PYPI,
                    package=_normalize_pypi(name),
                    version=version,
                )
            )
    return reqs, skipped


def _local(tag: str) -> str:
    """Strip an XML namespace, e.g. '{ns}PackageReference' -> 'PackageReference'."""

    return tag.rsplit("}", 1)[-1]


def _nuget_requests(pairs: list[tuple[str, str]]) -> ParseResult:
    reqs: list[ScanRequest] = []
    skipped: list[SkippedDependency] = []
    for name, raw_version in pairs:
        if not name:
            continue
        version = pin_nuget(raw_version)
        if version is None:
            skipped.append(_skip(name, raw_version or "(no version)"))
        else:
            reqs.append(ScanRequest(ecosystem=Ecosystem.NUGET, package=name, version=version))
    return reqs, skipped


def parse_csproj(content: str) -> ParseResult:
    root = ElementTree.fromstring(content)
    pairs: list[tuple[str, str]] = []
    for el in root.iter():
        if _local(el.tag) != "PackageReference":
            continue
        name = el.attrib.get("Include") or el.attrib.get("Update") or ""
        # Version can be an attribute or a child <Version> element.
        version = el.attrib.get("Version", "")
        if not version:
            child = next((c for c in el if _local(c.tag) == "Version"), None)
            version = (child.text or "").strip() if child is not None else ""
        pairs.append((name, version))
    return _nuget_requests(pairs)


def parse_packages_config(content: str) -> ParseResult:
    root = ElementTree.fromstring(content)
    pairs = [
        (el.attrib.get("id", ""), el.attrib.get("version", ""))
        for el in root.iter()
        if _local(el.tag) == "package"
    ]
    return _nuget_requests(pairs)


# --------------------------------------------------------------------------
# Dispatch
# --------------------------------------------------------------------------


def parse(filename: str, content: str) -> tuple[Ecosystem, list[ScanRequest], list[SkippedDependency]]:
    """Pick a parser by filename and return (ecosystem, requests, skipped)."""

    # Suffix match on the basename so descriptive names also work, e.g.
    # "vulnerable-package.json" or "requirements-dev.txt".
    fn = filename.strip().replace("\\", "/").split("/")[-1].lower()
    if fn.endswith(".csproj"):
        return (Ecosystem.NUGET, *parse_csproj(content))
    if fn.endswith("packages.config"):
        return (Ecosystem.NUGET, *parse_packages_config(content))
    if fn.endswith("package.json"):  # not package-lock.json
        return (Ecosystem.NPM, *parse_package_json(content))
    if fn.endswith(("requirements.txt", "requirements.in")):
        return (Ecosystem.PYPI, *parse_requirements(content))
    raise ValueError(
        f"Unsupported manifest {filename!r}; supported: package.json, "
        "requirements.txt, *.csproj, packages.config"
    )
