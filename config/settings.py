"""Central configuration loaded from environment / .env file."""
from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMProvider(str, Enum):
    GITHUB = "github"
    AZURE = "azure"
    OPENAI = "openai"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- LLM ---
    github_token: str = ""
    github_model: str = "gpt-4o"

    azure_openai_api_key: str = ""
    azure_openai_endpoint: str = ""
    azure_openai_deployment: str = "gpt-4o"
    azure_openai_api_version: str = "2024-08-01-preview"

    openai_api_key: str = ""

    llm_temperature: float = 0.4
    llm_max_tokens: int = 4096

    # --- Agent ---
    hitm_mode: bool = True
    max_concurrent_agents: int = 5
    agent_timeout_seconds: int = 180

    # --- Dashboard ---
    dashboard_host: str = "localhost"
    dashboard_port: int = 8000
    debug: bool = False

    # --- Paths ---
    output_dir: Path = Path("./output")
    specs_dir: Path = Path("./specs")

    # --- Derived ---
    llm_provider: LLMProvider = LLMProvider.GITHUB

    @model_validator(mode="after")
    def detect_provider(self) -> "Settings":
        if self.azure_openai_api_key:
            self.llm_provider = LLMProvider.AZURE
        elif self.openai_api_key:
            self.llm_provider = LLMProvider.OPENAI
        else:
            self.llm_provider = LLMProvider.GITHUB
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.specs_dir.mkdir(parents=True, exist_ok=True)
        return self

    @property
    def openai_base_url(self) -> str | None:
        if self.llm_provider == LLMProvider.GITHUB:
            return "https://models.inference.ai.azure.com"
        if self.llm_provider == LLMProvider.AZURE:
            return f"{self.azure_openai_endpoint}openai/deployments/{self.azure_openai_deployment}"
        return None

    @property
    def effective_api_key(self) -> str:
        if self.llm_provider == LLMProvider.GITHUB:
            return self.github_token
        if self.llm_provider == LLMProvider.AZURE:
            return self.azure_openai_api_key
        return self.openai_api_key

    @property
    def effective_model(self) -> str:
        if self.llm_provider == LLMProvider.GITHUB:
            return self.github_model
        if self.llm_provider == LLMProvider.AZURE:
            return self.azure_openai_deployment
        return "gpt-4o"


settings = Settings()
