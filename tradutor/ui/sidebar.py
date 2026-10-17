"""Componente da barra lateral de configuracoes e parametros."""

import customtkinter as ctk
from .tema import CORES


class SidebarView(ctk.CTkFrame):
    """Sidebar de parametros de traducao, idiomas e opcoes de multiplexacao."""

    IDIOMAS_DESTINO = ["pt", "en", "es", "fr", "de", "it", "ru", "ja", "ko", "zh-cn"]

    def __init__(self, master, on_destino_alterado_cb=None):
        super().__init__(master, fg_color=CORES["bg_sidebar"], width=270, corner_radius=8)
        self.pack_propagate(False)
        self._on_destino_alterado_cb = on_destino_alterado_cb

        self._construir_widgets()

    def _construir_widgets(self):
        lbl_secao = ctk.CTkLabel(
            self,
            text="PARAMETROS DE TRADUCAO",
            font=("Segoe UI", 11, "bold"),
            text_color=CORES["texto_secundario"]
        )
        lbl_secao.pack(anchor="w", padx=16, pady=(16, 8))

        # Card de Selecao de Idiomas
        frame_idiomas = ctk.CTkFrame(self, fg_color=CORES["bg_card"], corner_radius=6)
        frame_idiomas.pack(fill="x", padx=12, pady=6)

        ctk.CTkLabel(
            frame_idiomas,
            text="Idioma de Origem (MKV):",
            font=("Segoe UI", 11),
            text_color=CORES["texto_secundario"]
        ).pack(anchor="w", padx=10, pady=(8, 2))

        self.combo_lang = ctk.CTkOptionMenu(
            frame_idiomas,
            values=["auto"],
            fg_color="#1a1b26",
            button_color=CORES["borda_card"],
            text_color="white",
            height=28
        )
        self.combo_lang.pack(fill="x", padx=10, pady=(0, 8))

        ctk.CTkLabel(
            frame_idiomas,
            text="Idioma de Destino:",
            font=("Segoe UI", 11),
            text_color=CORES["texto_secundario"]
        ).pack(anchor="w", padx=10, pady=(4, 2))

        self.combo_lang_dest = ctk.CTkOptionMenu(
            frame_idiomas,
            values=self.IDIOMAS_DESTINO,
            command=self._disparar_destino_alterado,
            fg_color="#1a1b26",
            button_color=CORES["borda_card"],
            text_color="white",
            height=28
        )
        self.combo_lang_dest.pack(fill="x", padx=10, pady=(0, 10))

        # Card de Multiplexacao e Saida
        frame_saida = ctk.CTkFrame(self, fg_color=CORES["bg_card"], corner_radius=6)
        frame_saida.pack(fill="x", padx=12, pady=6)

        ctk.CTkLabel(
            frame_saida,
            text="Multiplexacao & Saida:",
            font=("Segoe UI", 11),
            text_color=CORES["texto_secundario"]
        ).pack(anchor="w", padx=10, pady=(8, 4))

        self.var_manter_legenda = ctk.BooleanVar(value=False)
        self.chk_manter = ctk.CTkCheckBox(
            frame_saida,
            text="Manter legenda (.srt) avulsa",
            variable=self.var_manter_legenda,
            font=("Segoe UI", 11),
            text_color=CORES["texto_principal"],
            border_color=CORES["borda_card"],
            fg_color=CORES["destaque_azul"]
        )
        self.chk_manter.pack(anchor="w", padx=10, pady=(2, 8))

        # Card do Escudo Anti-Alucinacao
        frame_modulos = ctk.CTkFrame(self, fg_color=CORES["bg_card"], corner_radius=6)
        frame_modulos.pack(fill="x", padx=12, pady=6)

        ctk.CTkLabel(
            frame_modulos,
            text="Escudo Anti-Alucinacao:",
            font=("Segoe UI", 11),
            text_color=CORES["texto_secundario"]
        ).pack(anchor="w", padx=10, pady=(8, 2))

        self.lbl_glossario_info = ctk.CTkLabel(
            frame_modulos,
            text="● Glossarios Ativos (AniList)",
            font=("Segoe UI", 11),
            text_color=CORES["destaque_verde"]
        )
        self.lbl_glossario_info.pack(anchor="w", padx=10, pady=(0, 8))

    def _disparar_destino_alterado(self, valor: str):
        if self._on_destino_alterado_cb:
            self._on_destino_alterado_cb(valor)

    @property
    def idioma_origem(self) -> str:
        return self.combo_lang.get().strip()

    @property
    def idioma_destino(self) -> str:
        return self.combo_lang_dest.get().strip()

    @property
    def manter_legenda(self) -> bool:
        return self.var_manter_legenda.get()

    def atualizar_opcoes_origem(self, opcoes: list, valor_padrao: str):
        """Atualiza a lista de opcoes do combo de idioma de origem."""
        self.combo_lang.configure(values=opcoes)
        self.combo_lang.set(valor_padrao)
