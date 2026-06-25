"""Configuration: model selection and per-agent request budgets.

Values come from (in order of precedence): environment variables, an optional
config.yaml, then sensible defaults. Models are Anthropic Claude models built
directly through pydantic-ai's Anthropic provider, so the only required secret
is ANTHROPIC_API_KEY.
"""

from __future__ import annotations

import os
from functools import cached_property
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field
from pydantic_ai.models.anthropic import AnthropicModel
from pydantic_ai.providers.anthropic import AnthropicProvider


def _load_config() -> dict:
    candidates = [
        Path(os.environ.get("PATCHPILOT_CONFIG", "")),
        Path.cwd() / "config.yaml",
        Path(__file__).parent.parent.parent / "config.yaml",
    ]
    for p in candidates:
        if p and p.is_file():
            with open(p) as f:
                return yaml.safe_load(f) or {}
    return {}


class _ModelSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")
    # The vulnerability agent does the hard work (code edits), so it defaults to
    # the most capable model. Summary/package coordination uses Sonnet.
    summary: str = "claude-sonnet-4-6"
    package: str = "claude-sonnet-4-6"
    vulnerability: str = "claude-opus-4-8"


class _BudgetSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")
    max_summary_requests: int = 25
    max_package_requests: int = 15
    max_vulnerability_requests: int = 30


class _AppSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")
    models: _ModelSettings = Field(default_factory=_ModelSettings)
    budget: _BudgetSettings = Field(default_factory=_BudgetSettings)


class Settings:
    def __init__(self) -> None:
        raw = _load_config()
        validated = _AppSettings(**raw.get("app_settings", {}))

        self.anthropic_api_key: str = os.environ.get("ANTHROPIC_API_KEY", "")
        self.summary_model: str = os.environ.get(
            "PATCHPILOT_SUMMARY_MODEL", validated.models.summary
        )
        self.package_model: str = os.environ.get(
            "PATCHPILOT_PACKAGE_MODEL", validated.models.package
        )
        self.vulnerability_model: str = os.environ.get(
            "PATCHPILOT_VULN_MODEL", validated.models.vulnerability
        )
        self.max_summary_requests: int = validated.budget.max_summary_requests
        self.max_package_requests: int = validated.budget.max_package_requests
        self.max_vulnerability_requests: int = validated.budget.max_vulnerability_requests

    def _make_model(self, model_name: str) -> AnthropicModel:
        provider = AnthropicProvider(api_key=self.anthropic_api_key)
        return AnthropicModel(model_name, provider=provider)

    @cached_property
    def summary(self) -> AnthropicModel:
        return self._make_model(self.summary_model)

    @cached_property
    def package(self) -> AnthropicModel:
        return self._make_model(self.package_model)

    @cached_property
    def vulnerability(self) -> AnthropicModel:
        return self._make_model(self.vulnerability_model)


settings = Settings()
