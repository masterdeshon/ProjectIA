"""Verifica o SDK real usando transporte HTTP inteiramente simulado."""

import json
import unittest

import httpx
from openai import OpenAI

from projectia.client import AssistantError, OpenAIResponder, PromptValidationError, validate_prompt
from projectia.config import Settings


def response_body(text="Resposta de teste."):
    return {
        "id": "resp_test",
        "object": "response",
        "created_at": 0,
        "model": "gpt-4.1-mini",
        "status": "completed",
        "output": [
            {
                "id": "msg_test",
                "type": "message",
                "role": "assistant",
                "status": "completed",
                "content": [{"type": "output_text", "text": text, "annotations": []}],
            }
        ],
    }


class PromptTests(unittest.TestCase):
    def test_empty_input_is_rejected(self):
        for prompt in ("", " \n\t "):
            with self.subTest(prompt=prompt), self.assertRaises(PromptValidationError):
                validate_prompt(prompt)

    def test_unicode_limit_and_internal_newlines(self):
        prompt = "😀" * 99 + "\n" + "á" * 100
        self.assertEqual(len(prompt), 200)
        self.assertEqual(validate_prompt("  " + prompt + " \n"), prompt)
        with self.assertRaises(PromptValidationError):
            validate_prompt(prompt + "x")


class ResponsesClientTests(unittest.TestCase):
    def make_responder(self, handler):
        sdk = OpenAI(
            api_key="unit-test-key",
            base_url="https://api.openai.com/v1",
            max_retries=0,
            http_client=httpx.Client(transport=httpx.MockTransport(handler)),
        )
        self.addCleanup(sdk.close)
        return OpenAIResponder(Settings(api_key="unit-test-key"), sdk_client=sdk)

    def test_request_uses_responses_api_without_previous_conversation(self):
        requests = []

        def handle(request):
            requests.append(request)
            return httpx.Response(200, json=response_body("  Olá!  "))

        responder = self.make_responder(handle)
        self.assertEqual(responder.respond("  Primeira pergunta  "), "Olá!")
        responder.respond("Segunda pergunta")
        self.assertEqual(len(requests), 2)
        self.assertEqual(requests[0].method, "POST")
        self.assertEqual(requests[0].url.path, "/v1/responses")
        self.assertEqual(requests[0].headers["Authorization"], "Bearer unit-test-key")
        first, second = (json.loads(request.content) for request in requests)
        self.assertEqual(first["input"], "Primeira pergunta")
        self.assertEqual(second["input"], "Segunda pergunta")
        self.assertNotIn("previous_response_id", second)
        self.assertNotIn("conversation", second)
        self.assertEqual(first["model"], "gpt-4.1-mini")
        self.assertEqual(first["max_output_tokens"], 600)
        self.assertIs(first["store"], False)

    def test_invalid_prompt_never_reaches_transport(self):
        def forbidden_request(_request):
            self.fail("Uma pergunta inválida não pode chamar a API.")

        responder = self.make_responder(forbidden_request)
        for prompt in (" ", "a" * 201):
            with self.subTest(prompt=prompt), self.assertRaises(PromptValidationError):
                responder.respond(prompt)

    def test_http_errors_become_safe_messages(self):
        expected = {
            400: "recusou",
            401: "autenticação",
            403: "permissão",
            404: "modelo",
            429: "cota",
            500: "indisponível",
        }
        for status, text in expected.items():
            with self.subTest(status=status):
                responder = self.make_responder(
                    lambda _request, code=status: httpx.Response(
                        code, json={"error": {"message": "unit-test-private", "type": "test"}}
                    )
                )
                with self.assertRaises(AssistantError) as caught:
                    responder.respond("Pergunta de teste")
                self.assertIn(text, str(caught.exception))
                self.assertNotIn("unit-test-private", str(caught.exception))
                self.assertNotIn("unit-test-key", str(caught.exception))

    def test_timeout_and_connection_errors_have_distinct_messages(self):
        for error, expected in (
            (httpx.ReadTimeout, "tempo limite"),
            (httpx.ConnectError, "conectar"),
        ):
            with self.subTest(error=error):

                def handle(request, error=error):
                    raise error("unit-test-private", request=request)

                responder = self.make_responder(handle)
                with self.assertRaises(AssistantError) as caught:
                    responder.respond("Pergunta de teste")
                self.assertIn(expected, str(caught.exception))
                self.assertNotIn("unit-test-private", str(caught.exception))

    def test_empty_output_is_not_presented_as_success(self):
        responder = self.make_responder(
            lambda _request: httpx.Response(200, json=response_body(" "))
        )
        with self.assertRaisesRegex(AssistantError, "sem texto"):
            responder.respond("Pergunta de teste")

    def test_truncated_response_is_identified(self):
        body = response_body("Texto parcial")
        body["status"] = "incomplete"
        body["incomplete_details"] = {"reason": "max_output_tokens"}
        responder = self.make_responder(lambda _request: httpx.Response(200, json=body))
        response = responder.respond("Pergunta de teste")
        self.assertIn("Texto parcial", response)
        self.assertIn("interrompida", response)
        self.assertIn("600 tokens", response)
