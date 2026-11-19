"""Comportamento concorrente do executor, sem Tk nem chamadas de rede."""

from __future__ import annotations

import queue
import threading
import time
import unittest
from collections import deque
from unittest.mock import patch

from projectia.client import AssistantError
from projectia.gui import ResponseRunner


class ControlledResponder:
    def __init__(self, *outcomes: str | Exception, blocked: bool = False) -> None:
        self.outcomes = deque(outcomes or ("Resposta local.",))
        self.calls: list[str] = []
        self.started = threading.Event()
        self.release = threading.Event()
        self.closed = threading.Event()
        self.close_count = 0
        self.worker_daemon = False
        if not blocked:
            self.release.set()

    def respond(self, prompt: str) -> str:
        self.calls.append(prompt)
        self.worker_daemon = threading.current_thread().daemon
        self.started.set()
        if not self.release.wait(5):
            raise AssertionError("O teste não liberou a resposta simulada.")
        outcome = self.outcomes.popleft()
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    def close(self) -> None:
        self.close_count += 1
        self.closed.set()


class ResponseRunnerTests(unittest.TestCase):
    def make_runner(self, fake: ControlledResponder) -> ResponseRunner:
        runner = ResponseRunner(fake)
        self.addCleanup(runner.shutdown)
        self.addCleanup(fake.release.set)
        return runner

    def test_blocks_duplicate_submissions_while_request_is_running(self) -> None:
        fake = ControlledResponder("Primeira resposta.", blocked=True)
        runner = self.make_runner(fake)
        self.assertTrue(runner.submit("Primeira pergunta"))
        self.assertTrue(fake.started.wait(2))
        self.assertFalse(runner.submit("Clique repetido"))
        fake.release.set()
        result = runner.results.get(timeout=2)
        self.assertEqual(result.text, "Primeira resposta.")
        self.assertIsNone(result.error)
        self.assertEqual(fake.calls, ["Primeira pergunta"])
        self.assertTrue(fake.worker_daemon)

    def test_only_one_of_simultaneous_submissions_starts_a_request(self) -> None:
        fake = ControlledResponder(blocked=True)
        runner = self.make_runner(fake)
        barrier = threading.Barrier(9)
        accepted: list[bool] = []

        def submit() -> None:
            barrier.wait(timeout=2)
            accepted.append(runner.submit("Pergunta concorrente"))

        threads = [threading.Thread(target=submit) for _ in range(8)]
        for thread in threads:
            thread.start()
        barrier.wait(timeout=2)
        for thread in threads:
            thread.join(timeout=2)
            self.assertFalse(thread.is_alive())
        self.assertEqual(accepted.count(True), 1)
        self.assertTrue(fake.started.wait(2))
        self.assertEqual(fake.calls, ["Pergunta concorrente"])
        fake.release.set()
        self.assertEqual(runner.results.get(timeout=2).text, "Resposta local.")

    def test_controlled_failure_allows_retry(self) -> None:
        fake = ControlledResponder(AssistantError("Conexão indisponível."), "Funcionou.")
        runner = self.make_runner(fake)
        self.assertTrue(runner.submit("Tente responder"))
        result = runner.results.get(timeout=2)
        self.assertEqual(result.error, "Conexão indisponível.")
        self.assertIsNone(result.text)
        self.assertTrue(runner.submit("Tente novamente"))
        self.assertEqual(runner.results.get(timeout=2).text, "Funcionou.")
        self.assertEqual(len(fake.calls), 2)

    def test_unexpected_exception_does_not_expose_its_contents(self) -> None:
        fake = ControlledResponder(RuntimeError("sk-secret-in-error-body"))
        runner = self.make_runner(fake)
        runner.submit("Pergunta fictícia")
        result = runner.results.get(timeout=2)
        self.assertIsNone(result.text)
        self.assertIn("Tente novamente", result.error or "")
        self.assertNotIn("sk-secret", result.error or "")

    def test_shutdown_does_not_wait_for_network_and_closes_after_request(self) -> None:
        fake = ControlledResponder("Resposta atrasada.", blocked=True)
        runner = self.make_runner(fake)
        runner.submit("Ainda aguardando")
        self.assertTrue(fake.started.wait(2))
        started = time.monotonic()
        runner.shutdown()
        self.assertLess(time.monotonic() - started, 1)
        self.assertFalse(runner.submit("Depois de encerrar"))
        self.assertEqual(fake.close_count, 0)
        fake.release.set()
        self.assertTrue(fake.closed.wait(2))
        self.assertEqual(runner.results.get(timeout=2).text, "Resposta atrasada.")
        runner.shutdown()
        self.assertEqual(fake.close_count, 1)

    def test_shutdown_is_idempotent_without_an_active_request(self) -> None:
        fake = ControlledResponder()
        runner = self.make_runner(fake)
        runner.shutdown()
        runner.shutdown()
        self.assertEqual(fake.close_count, 1)
        self.assertFalse(runner.submit("Encerrado"))
        with self.assertRaises(queue.Empty):
            runner.results.get_nowait()

    def test_thread_start_failure_does_not_leave_runner_busy(self) -> None:
        fake = ControlledResponder("Nova tentativa concluída.")
        runner = self.make_runner(fake)
        with patch("projectia.gui.threading.Thread.start", side_effect=RuntimeError):
            with self.assertRaisesRegex(AssistantError, "iniciar a consulta"):
                runner.submit("Falha simulada")
        self.assertTrue(runner.submit("Tentar outra vez"))
        self.assertEqual(runner.results.get(timeout=2).text, "Nova tentativa concluída.")


if __name__ == "__main__":
    unittest.main()
