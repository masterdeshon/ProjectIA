"""Interface Tkinter; apenas o thread principal acessa widgets."""

from __future__ import annotations

import queue
import sys
import threading
import tkinter as tk
from dataclasses import dataclass
from tkinter import messagebox, ttk
from tkinter.scrolledtext import ScrolledText

from .client import (
    AssistantError,
    OpenAIResponder,
    PromptValidationError,
    Responder,
    validate_prompt,
)
from .config import MAX_PROMPT_CHARS, ConfigurationError, load_settings


@dataclass(frozen=True, slots=True)
class ResponseResult:
    text: str | None = None
    error: str | None = None


class ResponseRunner:
    """Executa uma chamada por vez, sem depender de widgets ou callbacks Tk."""

    def __init__(self, responder: Responder) -> None:
        self.results: queue.Queue[ResponseResult] = queue.Queue()
        self._responder = responder
        self._lock = threading.Lock()
        self._running = False
        self._closed = False
        self._client_closed = False

    def submit(self, prompt: str) -> bool:
        with self._lock:
            if self._running or self._closed:
                return False
            self._running = True
        try:
            threading.Thread(
                target=self._work, args=(prompt,), daemon=True, name="projectia-request"
            ).start()
        except RuntimeError:
            with self._lock:
                self._running = False
            raise AssistantError("Não foi possível iniciar a consulta. Tente novamente.") from None
        return True

    def _work(self, prompt: str) -> None:
        try:
            result = ResponseResult(text=self._responder.respond(prompt))
        except (AssistantError, PromptValidationError) as exc:
            result = ResponseResult(error=str(exc))
        except Exception:
            # Não expor exceções arbitrárias, request, cabeçalhos ou chaves.
            result = ResponseResult(error="Ocorreu uma falha ao consultar a IA. Tente novamente.")
        finally:
            with self._lock:
                self._running = False
                should_close = self._closed and not self._client_closed
                if should_close:
                    self._client_closed = True
            if should_close:
                self._close_client()
        self.results.put(result)

    def shutdown(self) -> None:
        """Não espera a rede e só fecha o cliente após a chamada em andamento."""
        with self._lock:
            self._closed = True
            should_close = not self._running and not self._client_closed
            if should_close:
                self._client_closed = True
        if should_close:
            self._close_client()

    def _close_client(self) -> None:
        try:
            self._responder.close()
        except Exception:
            # Encerramento não gera diálogos ou callbacks depois de fechar a janela.
            pass


class ProjectIAApp:
    """Janela de perguntas independentes com histórico apenas visual."""

    POLL_INTERVAL_MS = 75

    def __init__(self, root: tk.Tk, responder: Responder) -> None:
        self.root = root
        self._runner = ResponseRunner(responder)
        self._busy = False
        self._closed = False
        self._poll_id: str | None = None

        root.title("ProjectIA")
        root.geometry("700x620")
        root.minsize(460, 400)
        root.protocol("WM_DELETE_WINDOW", self.close)

        frame = ttk.Frame(root, padding=16)
        frame.grid(row=0, column=0, sticky="nsew")
        root.rowconfigure(0, weight=1)
        root.columnconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(2, weight=1)

        ttk.Label(frame, text="ProjectIA", font=("TkDefaultFont", 18, "bold")).grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(
            frame,
            text="Cada envio é independente. O histórico abaixo serve apenas para leitura.",
            wraplength=620,
        ).grid(row=1, column=0, sticky="w", pady=(4, 12))

        self.history = ScrolledText(frame, wrap="word", state="disabled", height=14)
        self.history.grid(row=2, column=0, sticky="nsew", pady=(0, 12))
        ttk.Label(frame, text="Sua pergunta").grid(row=3, column=0, sticky="w")
        self.prompt = ScrolledText(frame, wrap="word", height=4, undo=True)
        self.prompt.grid(row=4, column=0, sticky="ew", pady=(4, 6))
        self.prompt.bind("<<Modified>>", self._on_prompt_modified)

        controls = ttk.Frame(frame)
        controls.grid(row=5, column=0, sticky="ew")
        controls.columnconfigure(0, weight=1)
        self.counter = ttk.Label(controls, text=f"0/{MAX_PROMPT_CHARS} caracteres")
        self.counter.grid(row=0, column=0, sticky="w")
        self.send_button = ttk.Button(
            controls, text="Enviar", command=self.submit, state="disabled"
        )
        self.send_button.grid(row=0, column=1, sticky="e")
        ttk.Label(
            frame,
            text="Espaços externos são desconsiderados. Quebras de linha internas contam.",
            wraplength=620,
        ).grid(row=6, column=0, sticky="w", pady=(6, 0))
        self.status = tk.StringVar(master=root, value="Pronto para enviar.")
        ttk.Label(frame, textvariable=self.status, wraplength=620).grid(
            row=7, column=0, sticky="w", pady=(12, 0)
        )
        self.prompt.focus_set()
        self._poll_id = root.after(self.POLL_INTERVAL_MS, self._poll_results)

    def _prompt_text(self) -> str:
        # Text adiciona uma quebra de linha final própria; ela não é entrada do usuário.
        return self.prompt.get("1.0", "end-1c")

    def _on_prompt_modified(self, _event: tk.Event | None = None) -> None:
        if self._closed or not self.prompt.edit_modified():
            return
        self.prompt.edit_modified(False)
        self._update_counter()

    def _update_counter(self) -> None:
        count = len(self._prompt_text().strip())
        self.counter.configure(text=f"{count}/{MAX_PROMPT_CHARS} caracteres")
        self.counter.configure(foreground="#b00020" if count > MAX_PROMPT_CHARS else "")
        enabled = not self._busy and not self._closed and 0 < count <= MAX_PROMPT_CHARS
        self.send_button.configure(state="normal" if enabled else "disabled")

    def _append_history(self, label: str, text: str) -> None:
        self.history.configure(state="normal")
        self.history.insert("end", f"{label}:\n{text}\n\n")
        self.history.configure(state="disabled")
        self.history.see("end")

    def submit(self) -> None:
        if self._closed or self._busy:
            return
        try:
            prompt = validate_prompt(self._prompt_text())
        except PromptValidationError as exc:
            self.status.set(str(exc))
            return

        self._busy = True
        self.send_button.configure(state="disabled")
        self.prompt.configure(state="disabled")
        self.status.set("Consultando a IA...")
        try:
            started = self._runner.submit(prompt)
        except AssistantError as exc:
            self._restore_input()
            self.status.set(str(exc))
            return
        if not started:
            self._restore_input()
            self.status.set("Aguarde a consulta em andamento.")
            return
        self._append_history("Você", prompt)

    def _restore_input(self) -> None:
        self._busy = False
        self.prompt.configure(state="normal")
        self._update_counter()

    def _poll_results(self) -> None:
        self._poll_id = None
        if self._closed:
            return
        try:
            result = self._runner.results.get_nowait()
        except queue.Empty:
            pass
        else:
            self._restore_input()
            if result.error is not None:
                self._append_history("Erro", result.error)
                self.status.set("Não foi possível concluir. Seu texto foi mantido.")
            else:
                self._append_history("IA", result.text or "")
                self.prompt.delete("1.0", "end")
                self._update_counter()
                self.status.set("Resposta recebida.")
            self.prompt.focus_set()
        if not self._closed:
            self._poll_id = self.root.after(self.POLL_INTERVAL_MS, self._poll_results)

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        if self._poll_id is not None:
            try:
                self.root.after_cancel(self._poll_id)
            except tk.TclError:
                pass
            self._poll_id = None
        self._runner.shutdown()
        self.root.destroy()


def main() -> int:
    """Inicia a interface somente quando chamado pelo ponto de entrada."""
    try:
        settings = load_settings()
    except ConfigurationError as exc:
        print(f"Configuração do ProjectIA: {exc}", file=sys.stderr)
        return 2

    try:
        root = tk.Tk()
    except tk.TclError:
        print(
            "Não foi possível iniciar a interface. Verifique o Tkinter e o ambiente gráfico.",
            file=sys.stderr,
        )
        return 2

    try:
        responder = OpenAIResponder(settings)
    except Exception:
        messagebox.showerror(
            "ProjectIA",
            "Não foi possível preparar a conexão com a API. Confira a configuração.",
            parent=root,
        )
        root.destroy()
        return 2

    app = ProjectIAApp(root, responder)
    try:
        root.mainloop()
    finally:
        if not app._closed:
            app.close()
    return 0
