"""Componente de cabecalho superior da interface grafica."""

import customtkinter as ctk
from .tema import CORES
from ..i18n import I18n


class HeaderView(ctk.CTkFrame):
    """Barra superior com logotipo, badge de versao, acoes rapidas e status."""

    def __init__(self, master, on_grimorio_cb=None, on_tema_cb=None, on_config_cb=None):
        super().__init__(master, fg_color=CORES["bg_sidebar"], height=52, corner_radius=0)
        self._on_grimorio_cb = on_grimorio_cb
        self._on_tema_cb = on_tema_cb
        self._on_config_cb = on_config_cb
        self._construir_widgets()

    def _construir_widgets(self):
        fonte_ui = CORES.get("fonte_ui", "Segoe UI")
        raio_card = CORES.get("raio_card", 4)

        # Lado Esquerdo: Marca do Aplicativo
        self.lbl_logo = ctk.CTkLabel(
            self,
            text="TRADUTOR",
            font=(fonte_ui, 16, "bold"),
            text_color=CORES["texto_principal"]
        )
        self.lbl_logo.pack(side="left", padx=(18, 6), pady=12)

        self.lbl_sub = ctk.CTkLabel(
            self,
            text=I18n.t("app_sub"),
            font=(fonte_ui, 13),
            text_color=CORES["texto_secundario"]
        )
        self.lbl_sub.pack(side="left", pady=12)

        self.badge_versao = ctk.CTkLabel(
            self,
            text="v2.7.0",
            font=(fonte_ui, 10, "bold"),
            fg_color=CORES["destaque_azul"],
            text_color=CORES.get("btn_destaque_txt", "#ffffff"),
            corner_radius=raio_card,
            width=46,
            height=20
        )
        self.badge_versao.pack(side="left", padx=8, pady=12)

        # Lado Direito: Acoes Rapidas (Config, Temas, Grimorio) e Status
        self.btn_config = ctk.CTkButton(
            self,
            text="⚙",
            font=("Segoe UI", 14),
            fg_color=CORES["bg_card"],
            hover_color=CORES["bg_card_hover"],
            border_color=CORES["borda_card"],
            border_width=CORES.get("borda_largura", 1),
            text_color=CORES["texto_principal"],
            width=36,
            height=28,
            command=self._on_config_click
        )
        self.btn_config.pack(side="right", padx=(4, 16), pady=12)

        self.btn_tema = ctk.CTkButton(
            self,
            text=I18n.t("btn_visualizar"),
            font=("Segoe UI", 11),
            fg_color=CORES["bg_card"],
            hover_color=CORES["bg_card_hover"],
            border_color=CORES["borda_card"],
            border_width=CORES.get("borda_largura", 1),
            text_color=CORES["texto_principal"],
            height=28,
            command=self._on_tema_click
        )
        self.btn_tema.pack(side="right", padx=4, pady=12)

        self.btn_grimorio = ctk.CTkButton(
            self,
            text=I18n.t("btn_grimorio"),
            font=("Segoe UI", 11),
            fg_color=CORES["bg_card"],
            hover_color=CORES["bg_card_hover"],
            border_color=CORES["borda_card"],
            border_width=CORES.get("borda_largura", 1),
            text_color=CORES["texto_principal"],
            height=28,
            command=self._on_grimorio_click
        )
        self.btn_grimorio.pack(side="right", padx=4, pady=12)

        self.lbl_status = ctk.CTkLabel(
            self,
            text=I18n.t("status_pronto"),
            font=("Segoe UI", 11),
            text_color=CORES["destaque_verde"]
        )
        self.lbl_status.pack(side="right", padx=(10, 16), pady=12)

    def aplicar_tema(self, cores: dict):
        """Propaga as novas cores, fontes e bordas do tema ativo para os widgets do cabecalho."""
        fonte_ui = cores.get("fonte_ui", "Segoe UI")
        raio_card = cores.get("raio_card", 4)
        largura_borda = cores.get("borda_largura", 1)

        self.configure(fg_color=cores["bg_sidebar"])
        self.lbl_logo.configure(text_color=cores["texto_principal"], font=(fonte_ui, 16, "bold"))
        self.lbl_sub.configure(text_color=cores["texto_secundario"], font=(fonte_ui, 13))

        self.badge_versao.configure(
            fg_color=cores["destaque_azul"],
            text_color=cores.get("btn_destaque_txt", "#ffffff"),
            corner_radius=raio_card,
            font=(fonte_ui, 10, "bold")
        )

        self.btn_config.configure(font=(fonte_ui, 14), corner_radius=raio_card)
        self.btn_tema.configure(font=(fonte_ui, 11), corner_radius=raio_card)
        self.btn_grimorio.configure(font=(fonte_ui, 11), corner_radius=raio_card)

        for btn in (self.btn_config, self.btn_tema, self.btn_grimorio):
            btn.configure(
                fg_color=cores["bg_card"],
                hover_color=cores["bg_card_hover"],
                border_color=cores["borda_card"],
                border_width=largura_borda,
                text_color=cores["texto_principal"]
            )

        self.lbl_status.configure(text_color=cores["destaque_verde"], font=(fonte_ui, 11))

    def set_status(self, texto: str, cor: str = None):
        """Atualiza a mensagem e cor do indicador de status do cabecalho."""
        if cor is None:
            cor = CORES["destaque_verde"]
        self.lbl_status.configure(text=texto, text_color=cor)

    def redefinir_textos(self):
        """Atualiza os textos traduziveis apos troca de idioma."""
        self.lbl_sub.configure(text=I18n.t("app_sub"))
        self.btn_tema.configure(text=I18n.t("btn_visualizar"))
        self.btn_grimorio.configure(text=I18n.t("btn_grimorio"))
        self.lbl_status.configure(text=I18n.t("status_pronto"))

    def _on_grimorio_click(self):
        if self._on_grimorio_cb:
            self._on_grimorio_cb()

    def _on_tema_click(self):
        if self._on_tema_cb:
            self._on_tema_cb()

    def _on_config_click(self):
        if self._on_config_cb:
            self._on_config_cb()
