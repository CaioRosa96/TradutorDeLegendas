"""Tradutor Automático de Legendas (MKV/ASS/SRT) — Ponto de Entrada."""
from __future__ import annotations

import sys

if "--headless" in sys.argv:
    from tradutor.cli import executar_cli
    sys.exit(executar_cli(sys.argv[1:]))

from tradutor.i18n import I18n
from tradutor.logger import setup_logger
from tradutor.orquestrador import OrquestradorTraducoes
from tradutor.controlador import ControladorApp
from tradutor.interface import InterfaceGrafica
from tradutor.ui.tema import inicializar_tema


def main() -> None:
    setup_logger()
    inicializar_tema()
    I18n.inicializar()
    model = OrquestradorTraducoes()
    view = InterfaceGrafica()
    ControladorApp(view, model)
    view.mainloop()


if __name__ == "__main__":
    main()
