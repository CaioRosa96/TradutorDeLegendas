"""Componente de cabecalho superior da interface grafica."""

import customtkinter as ctk
from .tema import CORES


class HeaderView(ctk.CTkFrame):
    """Barra superior com logotipo, badge de versao e status do motor."""

    def __init__(self, master):
        super().__init__(master, fg_color=CORES["bg_sidebar"], height=52, corner_radius=0)
        self._construir_widgets()

    def _construir_widgets(self):
        lbl_logo = ctk.CTkLabel(
            self,
            text="TARADUTOR",
            font=("Segoe UI", 16, "bold"),
            text_color=CORES["texto_principal"]
        )
        lbl_logo.pack(side="left", padx=(18, 6), pady=12)

        lbl_sub = ctk.CTkLabel(
            self,
            text="Legendas",
            font=("Segoe UI", 13),
            text_color=CORES["texto_secundario"]
        )
        lbl_sub.pack(side="left", pady=12)

        badge_versao = ctk.CTkLabel(
            self,
            text="v2.7.0",
            font=("Segoe UI", 10, "bold"),
            fg_color=CORES["destaque_azul"],
            text_color="white",
            corner_radius=4,
            width=46,
            height=20
        )
        badge_versao.pack(side="left", padx=8, pady=12)

        self.lbl_status = ctk.CTkLabel(
            self,
            text="● Sistema Pronto",
            font=("Segoe UI", 11),
            text_color=CORES["destaque_verde"]
        )
        self.lbl_status.pack(side="right", padx=20, pady=12)

    def set_status(self, texto: str, cor: str = CORES["destaque_verde"]):
        """Atualiza a mensagem e cor do indicador de status do cabecalho."""
        self.lbl_status.configure(text=texto, text_color=cor)
