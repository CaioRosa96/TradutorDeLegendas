"""Componente de barra de ferramentas superior compacta (estilo utilitario desktop)."""

import customtkinter as ctk
from .tema import CORES
from ..i18n import I18n


class HeaderView(ctk.CTkFrame):
    """Barra superior enxuta com identificacao tecnica, status e acesso rapido aos modais."""

    def __init__(self, master, on_grimorio_cb=None, on_tema_cb=None, on_config_cb=None):
        largura_borda = CORES.get("borda_largura", 1)
        super().__init__(
            master,
            fg_color=CORES["bg_sidebar"],
            border_color=CORES["borda_card"],
            border_width=largura_borda,
            height=38,
            corner_radius=0,
        )
        self.pack_propagate(False)
        self._on_grimorio_cb = on_grimorio_cb
        self._on_tema_cb = on_tema_cb
        self._on_config_cb = on_config_cb
        self._construir_widgets()

    def _construir_widgets(self):
        fonte_ui = CORES.get("fonte_ui", "Segoe UI")
        raio_card = CORES.get("raio_card", 2)
        largura_borda = CORES.get("borda_largura", 1)

        # Lado Esquerdo: Identificacao discreta de utilitario
        self.lbl_logo = ctk.CTkLabel(
            self,
            text="TRADUTOR",
            font=(fonte_ui, 12, "bold"),
            text_color=CORES["texto_principal"],
        )
        self.lbl_logo.pack(side="left", padx=(12, 4), pady=6)

        self.lbl_sub = ctk.CTkLabel(
            self,
            text=I18n.t("app_sub"),
            font=(fonte_ui, 11),
            text_color=CORES["texto_secundario"],
        )
        self.lbl_sub.pack(side="left", padx=(0, 6), pady=6)

        self.badge_versao = ctk.CTkLabel(
            self,
            text="v2.9.1",
            font=("Consolas", 10),
            fg_color=CORES["bg_card"],
            text_color=CORES["texto_secundario"],
            corner_radius=raio_card,
            width=46,
            height=18,
        )
        self.badge_versao.pack(side="left", padx=4, pady=6)

        # Lado Direito: Botoes de barra de ferramentas planos e status
        self.btn_config = ctk.CTkButton(
            self,
            text=I18n.t("btn_config"),
            font=(fonte_ui, 11),
            fg_color=CORES["bg_card"],
            hover_color=CORES["bg_card_hover"],
            border_color=CORES["borda_card"],
            border_width=largura_borda,
            text_color=CORES["texto_principal"],
            corner_radius=raio_card,
            width=96,
            height=24,
            command=self._on_config_click,
        )
        self.btn_config.pack(side="right", padx=(4, 10), pady=6)

        self.btn_tema = ctk.CTkButton(
            self,
            text=I18n.t("btn_visualizar"),
            font=(fonte_ui, 11),
            fg_color=CORES["bg_card"],
            hover_color=CORES["bg_card_hover"],
            border_color=CORES["borda_card"],
            border_width=largura_borda,
            text_color=CORES["texto_principal"],
            corner_radius=raio_card,
            width=84,
            height=24,
            command=self._on_tema_click,
        )
        self.btn_tema.pack(side="right", padx=3, pady=6)

        self.btn_grimorio = ctk.CTkButton(
            self,
            text=I18n.t("btn_grimorio"),
            font=(fonte_ui, 11),
            fg_color=CORES["bg_card"],
            hover_color=CORES["bg_card_hover"],
            border_color=CORES["borda_card"],
            border_width=largura_borda,
            text_color=CORES["texto_principal"],
            corner_radius=raio_card,
            width=84,
            height=24,
            command=self._on_grimorio_click,
        )
        self.btn_grimorio.pack(side="right", padx=3, pady=6)

        self.lbl_status = ctk.CTkLabel(
            self,
            text=I18n.t("status_pronto"),
            font=("Consolas", 10),
            text_color=CORES["texto_secundario"],
        )
        self.lbl_status.pack(side="right", padx=(8, 10), pady=6)

    def aplicar_tema(self, cores: dict):
        """Propaga as novas cores, fontes e bordas do tema ativo para os widgets do cabecalho."""
        fonte_ui = cores.get("fonte_ui", "Segoe UI")
        raio_card = cores.get("raio_card", 2)
        largura_borda = cores.get("borda_largura", 1)

        self.configure(
            fg_color=cores["bg_sidebar"],
            border_color=cores["borda_card"],
            border_width=largura_borda,
        )
        self.lbl_logo.configure(text_color=cores["texto_principal"], font=(fonte_ui, 12, "bold"))
        self.lbl_sub.configure(text_color=cores["texto_secundario"], font=(fonte_ui, 11))

        self.badge_versao.configure(
            fg_color=cores["bg_card"],
            text_color=cores["texto_secundario"],
            corner_radius=raio_card,
            font=("Consolas", 10),
        )

        for btn in (self.btn_config, self.btn_tema, self.btn_grimorio):
            btn.configure(
                font=(fonte_ui, 11),
                corner_radius=raio_card,
                fg_color=cores["bg_card"],
                hover_color=cores["bg_card_hover"],
                border_color=cores["borda_card"],
                border_width=largura_borda,
                text_color=cores["texto_principal"],
            )

        self.lbl_status.configure(text_color=cores["texto_secundario"], font=("Consolas", 10))

    def set_status(self, texto: str, cor: str = None):
        """Atualiza a mensagem e cor do indicador de status do cabecalho."""
        if cor is None:
            cor = CORES["texto_secundario"]
        self.lbl_status.configure(text=texto, text_color=cor)

    def redefinir_textos(self):
        """Atualiza os textos traduziveis apos troca de idioma."""
        self.lbl_sub.configure(text=I18n.t("app_sub"))
        self.btn_config.configure(text=I18n.t("btn_config"))
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
