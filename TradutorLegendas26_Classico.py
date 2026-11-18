"""Ponto de Entrada da Interface Clássica (Legado).

Inicializa a aplicação com a interface clássica v1.0, delegando os
eventos ao ControladorApp e OrquestradorTraducoes no padrão MVC.
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from tradutor.i18n import I18n
from tradutor.logger import setup_logger
from tradutor.orquestrador import OrquestradorTraducoes
from tradutor.controlador import ControladorApp
from tradutor.interface_classica import InterfaceGrafica
from tradutor.ui.tema import inicializar_tema


def main():
    setup_logger()
    inicializar_tema()
    I18n.inicializar()
    model = OrquestradorTraducoes()
    view = InterfaceGrafica()
    ControladorApp(view, model)
    view.mainloop()


if __name__ == "__main__":
    main()
