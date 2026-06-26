"""Configuration: model selection and per-agent request budgets.

Values come from (in order of precedence): environment variables, an optional
config.yaml, then sensible defaults. Models run on **Azure OpenAI** through
pydantic-ai's OpenAI model + Azure provider, so the required secrets are
AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY (plus the deployment names).

The per-tier "model" values are Azure **deployment names** (what you named the
model when you deployed it), not raw model ids.
"""

from __future__ import annotations

import os
from functools import cached_property
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.azure import AzureProvider
from pydantic_ai.providers.openai import OpenAIProvider


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
    # Azure **deployment names**. Default every tier to one deployment (gpt-4o)
    # since a typical Azure resource has a single deployment; override per tier
    # via env if you deploy more (see Settings / AZURE_OPENAI_DEPLOYMENT).
    summary: str = "gpt-4o"
    package: str = "gpt-4o"
    vulnerability: str = "gpt-4o"


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

        # Azure OpenAI credentials. AZURE_OPENAI_* are the canonical names;
        # API_KEY / PROJECT_ENDPOINT (from the repo .env.example) are accepted
        # as fallbacks so a single .env works for the whole project.
        self.azure_endpoint: str = (
            os.environ.get("AZURE_OPENAI_ENDPOINT")
            or os.environ.get("PROJECT_ENDPOINT", "")
        )
        self.azure_api_key: str = (
            os.environ.get("AZURE_OPENAI_API_KEY") or os.environ.get("API_KEY", "")
        )
        # "v1" (default) uses the modern Azure OpenAI v1 API (no dated version,
        # required by Foundry resources). A dated value (e.g. 2024-10-21) uses
        # the classic AzureProvider path instead.
        self.azure_api_version: str = os.environ.get("AZURE_OPENAI_API_VERSION", "v1")
        # A single AZURE_OPENAI_DEPLOYMENT sets every tier at once (the common
        # case — one deployment). Per-tier PATCHPILOT_*_MODEL still wins if set.
        default_deployment = os.environ.get("AZURE_OPENAI_DEPLOYMENT", "")
        self.summary_model: str = os.environ.get(
            "PATCHPILOT_SUMMARY_MODEL", default_deployment or validated.models.summary
        )
        self.package_model: str = os.environ.get(
            "PATCHPILOT_PACKAGE_MODEL", default_deployment or validated.models.package
        )
        self.vulnerability_model: str = os.environ.get(
            "PATCHPILOT_VULN_MODEL", default_deployment or validated.models.vulnerability
        )
        self.max_summary_requests: int = validated.budget.max_summary_requests
        self.max_package_requests: int = validated.budget.max_package_requests
        self.max_vulnerability_requests: int = validated.budget.max_vulnerability_requests

        # SMTP delivery (optional). When smtp_host is empty, the email tool only
        # records to the outbox; set PATCHPILOT_SMTP_HOST to actually send.
        # smtp_user/smtp_password are optional — leave them unset to use an
        # IP-allowlisted relay (e.g. smtp-relay.gmail.com) that needs no login.
        self.smtp_host: str = os.environ.get("PATCHPILOT_SMTP_HOST", "")
        self.smtp_port: int = int(os.environ.get("PATCHPILOT_SMTP_PORT", "587"))
        self.smtp_user: str = os.environ.get("PATCHPILOT_SMTP_USER", "")
        self.smtp_password: str = os.environ.get("PATCHPILOT_SMTP_PASSWORD", "")
        self.smtp_from: str = os.environ.get(
            "PATCHPILOT_SMTP_FROM", self.smtp_user or "patchpilot@localhost"
        )
        self.smtp_from_name: str = os.environ.get("PATCHPILOT_SMTP_FROM_NAME", "PatchPilot")
        self.smtp_reply_to: str = os.environ.get("PATCHPILOT_SMTP_REPLY_TO", "")
        self.smtp_starttls: bool = (
            os.environ.get("PATCHPILOT_SMTP_STARTTLS", "true").lower() != "false"
        )

    def _make_model(self, deployment: str) -> OpenAIChatModel:
        """Build an Azure OpenAI model for a given deployment name.

        Uses the modern v1 API by default (base_url `.../openai/v1/`, no dated
        api-version — required by Foundry resources). Set a dated
        AZURE_OPENAI_API_VERSION to use the classic AzureProvider instead.
        """
        if self.azure_api_version and self.azure_api_version != "v1":
            provider: AzureProvider | OpenAIProvider = AzureProvider(
                azure_endpoint=self.azure_endpoint,
                api_version=self.azure_api_version,
                api_key=self.azure_api_key,
            )
        else:
            base_url = self.azure_endpoint.rstrip("/") + "/openai/v1/"
            provider = OpenAIProvider(base_url=base_url, api_key=self.azure_api_key)
        return OpenAIChatModel(deployment, provider=provider)

    @cached_property
    def summary(self) -> OpenAIChatModel:
        return self._make_model(self.summary_model)

    @cached_property
    def package(self) -> OpenAIChatModel:
        return self._make_model(self.package_model)

    @cached_property
    def vulnerability(self) -> OpenAIChatModel:
        return self._make_model(self.vulnerability_model)


settings = Settings()
