"""Ensaio da janela real oculta, com serviço local e sem credenciais."""

from __future__ import annotations

import threading
import time
import tkinter as tk
import unittest
from collections import deque
from collections.abc import Callable

from projectia.client import AssistantError
from projectia.gui import ProjectIAApp


class MainThreadTk:
    """Registra qualquer acesso ao interpretador Tk fora do thread da janela."""

    def __init__(self, interpreter: object) -> None:
        self.interpreter = interpreter
        self.owner = threading.get_ident()
        self.violations: list[str] = []

    def __getattr__(self, name: str) -> object:
        target = getattr(self.interpreter, name)
        if not callable(target):
            return target

        def call(*args: object, **kwargs: object) -> object:
            if threading.get_ident() != self.owner:
                self.violations.append(name)
                raise AssertionError("O thread da requisição tentou acessar o Tk.")
            return target(*args, **kwargs)

        return call


class LocalResponder:
    def __init__(self, *outcomes: str | Exception, blocked: bool = False) -> None:
        self.outcomes = deque(outcomes or ("Resposta de teste.",))
        self.calls: list[str] = []
        self.started = threading.Event()
        self.release = threading.Event()
        self.closed = threading.Event()
        self.close_count = 0
        if not blocked:
            self.release.set()

    def respond(self, prompt: str) -> str:
        self.calls.append(prompt)
        self.started.set()
        if not self.release.wait(5):
            raise AssertionError("O teste não liberou o serviço local.")
        outcome = self.outcomes.popleft()
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    def close(self) -> None:
        self.close_count += 1
        self.closed.set()


class ProjectIAGUITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        try:
            probe = tk.Tk()
        except tk.TclError as exc:
            raise unittest.SkipTest(f"Tk gráfico indisponível: {exc}") from None
        probe.withdraw()
        probe.update_idletasks()
        probe.destroy()

    def setUp(self) -> None:
        self.root = tk.Tk()
        self.root.withdraw()
        self.tk_guard = MainThreadTk(self.root.tk)
        self.root.tk = self.tk_guard
        self.callback_errors: list[str] = []
        self.root.report_callback_exception = self.record_callback_error
        self.app: ProjectIAApp | None = None
        self.fake: LocalResponder | None = None

    def record_callback_error(self, error_type: type, value: Exception, _trace: object) -> None:
        self.callback_errors.append(f"{error_type.__name__}: {value}")

    def tearDown(self) -> None:
        if self.fake is not None:
            self.fake.release.set()
        if self.app is not None:
            self.app.close()
        else:
            self.root.destroy()
        if self.fake is not None:
            self.assertTrue(self.fake.closed.wait(2))
        self.assertEqual(self.callback_errors, [])
        self.assertEqual(self.tk_guard.violations, [])

    def create_app(self, *outcomes: str | Exception, blocked: bool = False) -> ProjectIAApp:
        self.fake = LocalResponder(*outcomes, blocked=blocked)
        self.app = ProjectIAApp(self.root, self.fake)
        self.root.update()
        return self.app

    def put_prompt(self, text: str) -> None:
        assert self.app is not None
        self.app.prompt.delete("1.0", "end")
        self.app.prompt.insert("1.0", text)
        self.root.update()

    def pump_until(self, condition: Callable[[], bool], *, pump: bool = True) -> None:
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline:
            if pump:
                self.root.update()
            if condition():
                return
            time.sleep(0.005)
        self.fail("A interface não chegou ao estado esperado no tempo do teste.")

    def test_empty_or_whitespace_prompt_does_not_start_request(self) -> None:
        app = self.create_app()
        for text in ("", "  \n\t  "):
            with self.subTest(text=text):
                self.put_prompt(text)
                self.assertTrue(app.send_button.instate(["disabled"]))
                app.submit()
                self.assertIn("Digite uma pergunta", app.status.get())
        self.assertEqual(self.fake.calls, [])

    def test_unicode_and_multiline_counter_uses_python_characters(self) -> None:
        app = self.create_app()
        for text in ("😀" * 200, "á" * 200, "a" * 99 + "\n" + "b" * 100):
            with self.subTest(kind=text[:5]):
                self.put_prompt(text)
                self.assertEqual(app.counter.cget("text"), "200/200 caracteres")
                self.assertFalse(app.send_button.instate(["disabled"]))
                self.put_prompt(text + "x")
                self.assertEqual(app.counter.cget("text"), "201/200 caracteres")
                self.assertTrue(app.send_button.instate(["disabled"]))
                app.submit()
                self.assertIn("no máximo 200", app.status.get())
        self.assertEqual(self.fake.calls, [])

    def test_success_is_async_ignores_duplicate_click_and_clears_input(self) -> None:
        app = self.create_app("Resposta local.", blocked=True)
        self.put_prompt("Pergunta de teste")
        app.submit()
        self.assertTrue(self.fake.started.wait(2))
        self.assertEqual(app.prompt.cget("state"), "disabled")
        self.assertTrue(app.send_button.instate(["disabled"]))
        self.assertEqual(app.status.get(), "Consultando a IA...")
        app.submit()
        self.root.update()
        self.assertEqual(self.fake.calls, ["Pergunta de teste"])
        self.fake.release.set()
        self.pump_until(lambda: app.status.get() == "Resposta recebida.")
        history = app.history.get("1.0", "end-1c")
        self.assertEqual(history.count("Você:\nPergunta de teste"), 1)
        self.assertEqual(history.count("IA:\nResposta local."), 1)
        self.assertEqual(app.prompt.get("1.0", "end-1c"), "")
        self.assertEqual(app.prompt.cget("state"), "normal")
        self.assertEqual(app.history.cget("state"), "disabled")
        self.assertEqual(app.counter.cget("text"), "0/200 caracteres")

    def test_exactly_200_unicode_or_multiline_characters_reach_responder_intact(self) -> None:
        app = self.create_app("Unicode recebido.", "Multilinha recebida.")
        prompts = ("😀" * 200, "a" * 99 + "\n" + "b" * 100)
        for index, prompt in enumerate(prompts):
            with self.subTest(index=index):
                self.put_prompt(prompt)
                app.submit()
                self.pump_until(lambda: app.status.get() == "Resposta recebida.")
                self.assertEqual(self.fake.calls[index], prompt)
                self.assertEqual(len(self.fake.calls[index]), 200)

    def test_external_whitespace_is_removed_before_request(self) -> None:
        app = self.create_app()
        self.put_prompt("\n  Uma pergunta\t\n")
        self.assertEqual(app.counter.cget("text"), "12/200 caracteres")
        app.submit()
        self.pump_until(lambda: app.status.get() == "Resposta recebida.")
        self.assertEqual(self.fake.calls, ["Uma pergunta"])

    def test_error_preserves_question_and_allows_retry(self) -> None:
        app = self.create_app(AssistantError("Conexão indisponível."), "Resposta recuperada.")
        self.put_prompt("Tentar novamente")
        app.submit()
        self.pump_until(lambda: "Seu texto foi mantido" in app.status.get())
        self.assertEqual(app.prompt.get("1.0", "end-1c"), "Tentar novamente")
        self.assertFalse(app.send_button.instate(["disabled"]))
        self.assertIn("Erro:\nConexão indisponível.", app.history.get("1.0", "end-1c"))
        app.submit()
        self.pump_until(lambda: app.status.get() == "Resposta recebida.")
        self.assertEqual(self.fake.calls, ["Tentar novamente", "Tentar novamente"])
        self.assertIn("Resposta recuperada.", app.history.get("1.0", "end-1c"))

    def test_close_during_request_does_not_wait_or_touch_destroyed_widgets(self) -> None:
        app = self.create_app("Resposta após fechar.", blocked=True)
        self.put_prompt("Pode fechar agora")
        app.submit()
        self.assertTrue(self.fake.started.wait(2))
        started = time.monotonic()
        app.close()
        self.assertLess(time.monotonic() - started, 1)
        self.assertEqual(self.fake.close_count, 0)
        self.fake.release.set()
        self.assertTrue(self.fake.closed.wait(2))
        app.close()
        self.assertEqual(self.fake.close_count, 1)

    def test_close_with_unpolled_result_cancels_scheduled_callback(self) -> None:
        app = self.create_app("Resultado já enfileirado.")
        self.put_prompt("Fechar antes de exibir")
        app.submit()
        self.pump_until(lambda: not app._runner.results.empty(), pump=False)
        app.close()
        app.close()
        self.assertEqual(self.fake.close_count, 1)


if __name__ == "__main__":
    unittest.main()
