"""Utilitário de sincronização thread-safe entre worker threads e o loop principal da UI."""

import threading
from typing import Any, Callable


class SincronizadorModalThread:
    """Encapsula a espera síncrona por interações da UI executadas na thread do Tkinter."""

    @staticmethod
    def executar_dialogo(
        widget_pai: Any,
        acao_ui: Callable[[Callable[[Any], None]], None],
        valor_padrao: Any = None,
        timeout: float | None = None,
    ) -> Any:
        """Executa uma ação no loop de eventos do widget pai e aguarda a resposta do usuário."""
        evento = threading.Event()
        resposta = [valor_padrao]

        def _responder(valor: Any):
            resposta[0] = valor
            evento.set()

        def _invocar():
            try:
                acao_ui(_responder)
            except Exception:
                evento.set()
                raise

        widget_pai.after(0, _invocar)
        evento.wait(timeout)
        return resposta[0]
