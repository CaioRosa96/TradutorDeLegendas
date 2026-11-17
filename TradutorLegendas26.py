"""Tradutor Automático de Legendas (MKV/ASS/SRT) — Ponto de Entrada."""
from __future__ import annotations

import sys

if "--headless" in sys.argv:
    from tradutor.cli import executar_cli
    sys.exit(executar_cli(sys.argv[1:]))

from tradutor.orquestrador import OrquestradorTraducoes
from tradutor.controlador import ControladorApp
from tradutor.interface import InterfaceGrafica
from tradutor.ui.tema import inicializar_tema


def main() -> None:
    inicializar_tema()
    model = OrquestradorTraducoes()
    view = InterfaceGrafica()
    ControladorApp(view, model)
    view.mainloop()


if __name__ == "__main__":
    main()
