"""Configuração explícita do aplicativo, sem carregar arquivos ao importar."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

MAX_PROMPT_CHARS = 200
DEFAULT_MODEL = "gpt-4.1-mini"


class ConfigurationError(ValueError):
    """Configuração ausente ou inválida, com mensagem apropriada ao usuário."""


@dataclass(frozen=True, slots=True)
class Settings:
    """Parâmetros da API; a chave é omitida da representação do objeto."""

    api_key: str = field(repr=False)
    model: str = DEFAULT_MODEL
    max_output_tokens: int = 600
    timeout_seconds: float = 30.0
    max_retries: int = 2

    def __post_init__(self) -> None:
        if not isinstance(self.api_key, str) or not self.api_key.strip():
            raise ConfigurationError(
                "Defina OPENAI_API_KEY no ambiente ou no arquivo .env da pasta atual."
            )
        if not isinstance(self.model, str) or not self.model.strip():
            raise ConfigurationError("OPENAI_MODEL deve informar um modelo válido.")
        if self.max_output_tokens <= 0:
            raise ConfigurationError("O limite de saída deve ser maior que zero.")
        if self.timeout_seconds <= 0:
            raise ConfigurationError("O tempo limite deve ser maior que zero.")
        if self.max_retries < 0:
            raise ConfigurationError("O número de novas tentativas não pode ser negativo.")


def load_settings(
    *,
    dotenv_path: Path | None = None,
    environ: Mapping[str, str] | None = None,
) -> Settings:
    """Carrega CWD/.env sem sobrescrever variáveis já definidas no ambiente.

    ``environ`` permite testar sem consultar ou alterar o ambiente do processo.
    Quando fornecido, nenhum arquivo .env é carregado.
    """
    if environ is None:
        explicit_path = Path.cwd() / ".env" if dotenv_path is None else dotenv_path
        load_dotenv(dotenv_path=explicit_path, override=False)
        source: Mapping[str, str] = os.environ
    else:
        source = environ

    api_key = source.get("OPENAI_API_KEY", "").strip()
    model = source.get("OPENAI_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL
    return Settings(api_key=api_key, model=model)
