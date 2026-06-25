"""Unit tests for the manifest parsers (no network)."""

from pathlib import Path

import pytest

from app.intake import manifests
from app.models import Ecosystem

EXAMPLES = Path(__file__).parents[2] / "docs" / "examples"


# --- version pinning -------------------------------------------------------


def test_pin_npm_exact_only():
    assert manifests.pin_npm("4.17.19") == "4.17.19"
    assert manifests.pin_npm("v2.0.0") == "2.0.0"
    assert manifests.pin_npm("^4.17.19") is None
    assert manifests.pin_npm("~1.2.5") is None
    assert manifests.pin_npm("*") is None


def test_pin_pypi_exact_only():
    assert manifests.pin_pypi("==1.2.3") == "1.2.3"
    assert manifests.pin_pypi("===2.0.0b1") == "2.0.0b1"
    assert manifests.pin_pypi(">=1.0") is None
    assert manifests.pin_pypi("~=1.4.2") is None
    assert manifests.pin_pypi("") is None  # no version


def test_pin_nuget_exact_skips_ranges_and_props():
    assert manifests.pin_nuget("12.0.3") == "12.0.3"
    assert manifests.pin_nuget("1.2.3.4") == "1.2.3.4"
    assert manifests.pin_nuget("6.0.0-preview.1") == "6.0.0-preview.1"
    assert manifests.pin_nuget("[1.0,2.0)") is None  # range
    assert manifests.pin_nuget("1.2.*") is None      # floating
    assert manifests.pin_nuget("$(JsonVersion)") is None  # MSBuild property


# --- npm -------------------------------------------------------------------


def test_parse_package_json_example():
    content = (EXAMPLES / "vulnerable-package.json").read_text()
    eco, reqs, skipped = manifests.parse("package.json", content)
    assert eco is Ecosystem.NPM
    assert {r.package: r.version for r in reqs} == {"lodash": "4.17.19", "minimist": "1.2.5"}
    assert skipped == []


def test_parse_package_json_skips_ranges():
    content = '{"dependencies": {"lodash": "4.17.19", "react": "^18.0.0"}}'
    _, reqs, skipped = manifests.parse("package.json", content)
    assert {r.package for r in reqs} == {"lodash"}
    assert {s.package for s in skipped} == {"react"}


# --- PyPI ------------------------------------------------------------------


def test_parse_requirements():
    content = """
# a comment
Django==4.2.0
requests>=2.0          # range -> skipped
Flask                  # no version -> skipped
PyYAML==6.0 ; python_version >= "3.8"
Some_Package[extra]==1.2.3
-r other-requirements.txt
"""
    eco, reqs, skipped = manifests.parse("requirements.txt", content)
    assert eco is Ecosystem.PYPI
    pinned = {r.package: r.version for r in reqs}
    # names PEP 503-normalized (lowercased, _ -> -)
    assert pinned == {"django": "4.2.0", "pyyaml": "6.0", "some-package": "1.2.3"}
    assert {s.package for s in skipped} == {"requests", "Flask"}


# --- NuGet -----------------------------------------------------------------


def test_parse_csproj_attribute_and_child_version():
    content = """<Project Sdk="Microsoft.NET.Sdk">
  <ItemGroup>
    <PackageReference Include="Newtonsoft.Json" Version="12.0.3" />
    <PackageReference Include="Serilog">
      <Version>2.10.0</Version>
    </PackageReference>
    <PackageReference Include="Floating" Version="1.2.*" />
  </ItemGroup>
</Project>"""
    eco, reqs, skipped = manifests.parse("App.csproj", content)
    assert eco is Ecosystem.NUGET
    assert {r.package: r.version for r in reqs} == {
        "Newtonsoft.Json": "12.0.3",
        "Serilog": "2.10.0",
    }
    assert {s.package for s in skipped} == {"Floating"}


def test_parse_packages_config():
    content = """<?xml version="1.0" encoding="utf-8"?>
<packages>
  <package id="Newtonsoft.Json" version="9.0.1" targetFramework="net46" />
  <package id="jQuery" version="3.1.1" />
</packages>"""
    eco, reqs, _ = manifests.parse("packages.config", content)
    assert eco is Ecosystem.NUGET
    assert {r.package: r.version for r in reqs} == {
        "Newtonsoft.Json": "9.0.1",
        "jQuery": "3.1.1",
    }


# --- dispatch --------------------------------------------------------------


def test_descriptive_filenames_dispatch_by_suffix():
    # The demo files aren't named exactly "package.json" etc.
    eco, reqs, _ = manifests.parse("vulnerable-package.json", '{"dependencies":{"lodash":"4.17.19"}}')
    assert eco is Ecosystem.NPM and reqs[0].package == "lodash"
    eco, _, _ = manifests.parse("dev-requirements.txt", "django==4.2.0")
    assert eco is Ecosystem.PYPI


def test_unsupported_manifest_raises():
    with pytest.raises(ValueError):
        manifests.parse("Gemfile.lock", "irrelevant")
