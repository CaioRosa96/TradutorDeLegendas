"""Subpacote de componentes visuais da interface grafica do Taradutor de Legendas."""

from .tema import CORES
from .header import HeaderView
from .sidebar import SidebarView
from .fila import PainelFilaView, CardArquivo
from .footer import FooterView

__all__ = [
    "CORES",
    "HeaderView",
    "SidebarView",
    "PainelFilaView",
    "CardArquivo",
    "FooterView"
]
