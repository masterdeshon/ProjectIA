"""Uma chamada independente à Responses API para cada pergunta."""

from __future__ import annotations

from typing import Any, Protocol

from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    BadRequestError,
    InternalServerError,
    NotFoundError,
    OpenAI,
    OpenAIError,
    PermissionDeniedError,
    RateLimitError,
)

from .config import MAX_PROMPT_CHARS, Settings

INSTRUCTIONS = (
    "Você é um assistente útil. Responda em português, com clareza e objetividade. "
    "Quando não souber uma informação, explique a limitação sem inventar fatos."
)


class PromptValidationError(ValueError):
    """Pergunta vazia ou acima do limite permitido."""


class AssistantError(RuntimeError):
    """Falha apresentada ao usuário sem conteúdo bruto da resposta HTTP."""


class Responder(Protocol):
    """Contrato mínimo para injetar a API ou um substituto local na interface."""

    def respond(self, prompt: str) -> str: ...

    def close(self) -> None: ...


def validate_prompt(prompt: str) -> str:
    """Remove espaços externos; quebras internas contam no limite de 200."""
    normalized = prompt.strip()
    if not normalized:
        raise PromptValidationError("Digite uma pergunta antes de enviar.")
    if len(normalized) > MAX_PROMPT_CHARS:
        raise PromptValidationError(f"A pergunta deve ter no máximo {MAX_PROMPT_CHARS} caracteres.")
    return normalized


class OpenAIResponder:
    """Cliente com dependência injetável e sem memória de conversação."""

    def __init__(self, settings: Settings, sdk_client: Any | None = None) -> None:
        self.settings = settings
        self._client = (
            sdk_client
            if sdk_client is not None
            else OpenAI(
                api_key=settings.api_key,
                base_url="https://api.openai.com/v1",
                timeout=settings.timeout_seconds,
                max_retries=settings.max_retries,
            )
        )

    def respond(self, prompt: str) -> str:
        user_input = validate_prompt(prompt)
        try:
            response = self._client.responses.create(
                model=self.settings.model,
                instructions=INSTRUCTIONS,
                input=user_input,
                max_output_tokens=self.settings.max_output_tokens,
                store=False,
            )
        except AuthenticationError:
            raise AssistantError(
                "A autenticação falhou. Confira OPENAI_API_KEY na configuração."
            ) from None
        except PermissionDeniedError:
            raise AssistantError(
                "A conta não tem permissão para esta solicitação ou modelo."
            ) from None
        except RateLimitError:
            raise AssistantError(
                "O limite de uso ou a cota da API foi atingido. "
                "Confira a conta e tente novamente depois."
            ) from None
        except APITimeoutError:
            raise AssistantError("A solicitação excedeu o tempo limite. Tente novamente.") from None
        except APIConnectionError:
            raise AssistantError(
                "Não foi possível conectar à API. Confira a conexão com a internet."
            ) from None
        except NotFoundError:
            raise AssistantError(
                "O modelo configurado não foi encontrado ou não está disponível "
                "para esta conta. Confira OPENAI_MODEL."
            ) from None
        except BadRequestError:
            raise AssistantError(
                "A API recusou a solicitação. Confira o modelo configurado e tente outra pergunta."
            ) from None
        except InternalServerError:
            raise AssistantError(
                "O serviço da API está temporariamente indisponível. Tente novamente depois."
            ) from None
        except (APIStatusError, OpenAIError):
            raise AssistantError(
                "Não foi possível obter uma resposta da API. Tente novamente depois."
            ) from None

        text = response.output_text
        if not isinstance(text, str) or not text.strip():
            raise AssistantError("A API retornou uma resposta sem texto. Tente novamente.")
        if getattr(response, "status", None) == "incomplete":
            details = getattr(response, "incomplete_details", None)
            if getattr(details, "reason", None) == "max_output_tokens":
                note = (
                    "Resposta interrompida pelo limite de saída de "
                    f"{self.settings.max_output_tokens} tokens."
                )
            else:
                note = "A resposta foi interrompida antes da conclusão."
            return f"{text.strip()}\n\n[{note}]"
        return text.strip()

    def close(self) -> None:
        """Libera o transporte; chamar somente quando não houver requisição ativa."""
        self._client.close()
