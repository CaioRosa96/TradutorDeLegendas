"""Componente da barra lateral de configuracoes e parametros."""

import customtkinter as ctk
from .tema import CORES
from ..idiomas import Idiomas
from ..i18n import I18n


class SidebarView(ctk.CTkFrame):
    """Sidebar de parametros de traducao, idiomas e opcoes de multiplexacao."""

    def __init__(self, master, on_destino_alterado_cb=None):
        largura_borda = CORES.get("borda_largura", 1)
        raio_card = CORES.get("raio_card", 6)
        super().__init__(
            master,
            fg_color=CORES["bg_sidebar"],
            border_color=CORES["borda_card"],
            border_width=largura_borda,
            width=270,
            corner_radius=raio_card
        )
        self.pack_propagate(False)
        self._on_destino_alterado_cb = on_destino_alterado_cb

        self._construir_widgets()

    def _construir_widgets(self):
        largura_borda = CORES.get("borda_largura", 1)
        raio_card = CORES.get("raio_card", 6)
        fonte_ui = CORES.get("fonte_ui", "Segoe UI")

        self.lbl_secao = ctk.CTkLabel(
            self,
            text=I18n.t("sidebar_titulo"),
            font=(fonte_ui, 11, "bold"),
            text_color=CORES["texto_secundario"]
        )
        self.lbl_secao.pack(anchor="w", padx=16, pady=(16, 8))

        # Card de Selecao de Idiomas
        self.frame_idiomas = ctk.CTkFrame(
            self,
            fg_color=CORES["bg_card"],
            border_color=CORES["borda_card"],
            border_width=largura_borda,
            corner_radius=raio_card
        )
        self.frame_idiomas.pack(fill="x", padx=12, pady=6)

        self.lbl_origem = ctk.CTkLabel(
            self.frame_idiomas,
            text=I18n.t("origem_lbl"),
            font=(fonte_ui, 11),
            text_color=CORES["texto_secundario"]
        )
        self.lbl_origem.pack(anchor="w", padx=10, pady=(8, 2))

        idioma_ui = I18n.obter_idioma()
        rotulo_auto = Idiomas.rotular_origem("auto", idioma_ui)
        self.combo_lang = ctk.CTkOptionMenu(
            self.frame_idiomas,
            values=[rotulo_auto],
            fg_color=CORES["combo_bg"],
            button_color=CORES["combo_btn"],
            button_hover_color=CORES["bg_card_hover"],
            dropdown_fg_color=CORES["combo_bg"],
            dropdown_text_color=CORES["texto_principal"],
            dropdown_hover_color=CORES["bg_card_hover"],
            text_color=CORES["texto_principal"],
            font=(fonte_ui, 11),
            dropdown_font=(fonte_ui, 11),
            corner_radius=raio_card,
            height=28
        )
        self.combo_lang.set(rotulo_auto)
        self.combo_lang.pack(fill="x", padx=10, pady=(0, 8))

        self.lbl_destino = ctk.CTkLabel(
            self.frame_idiomas,
            text=I18n.t("destino_lbl"),
            font=(fonte_ui, 11),
            text_color=CORES["texto_secundario"]
        )
        self.lbl_destino.pack(anchor="w", padx=10, pady=(4, 2))

        opcoes_destino = Idiomas.opcoes_destino_exibicao(idioma_ui)
        self.combo_lang_dest = ctk.CTkOptionMenu(
            self.frame_idiomas,
            values=opcoes_destino,
            command=self._disparar_destino_alterado,
            fg_color=CORES["combo_bg"],
            button_color=CORES["combo_btn"],
            button_hover_color=CORES["bg_card_hover"],
            dropdown_fg_color=CORES["combo_bg"],
            dropdown_text_color=CORES["texto_principal"],
            dropdown_hover_color=CORES["bg_card_hover"],
            text_color=CORES["texto_principal"],
            font=(fonte_ui, 11),
            dropdown_font=(fonte_ui, 11),
            corner_radius=raio_card,
            height=28
        )
        self.combo_lang_dest.set(Idiomas.rotular_destino("pt", idioma_ui))
        self.combo_lang_dest.pack(fill="x", padx=10, pady=(0, 10))

        # Card de Multiplexacao e Saida
        self.frame_saida = ctk.CTkFrame(
            self,
            fg_color=CORES["bg_card"],
            border_color=CORES["borda_card"],
            border_width=largura_borda,
            corner_radius=raio_card
        )
        self.frame_saida.pack(fill="x", padx=12, pady=6)

        self.lbl_saida = ctk.CTkLabel(
            self.frame_saida,
            text=I18n.t("saida_lbl"),
            font=(fonte_ui, 11),
            text_color=CORES["texto_secundario"]
        )
        self.lbl_saida.pack(anchor="w", padx=10, pady=(8, 4))

        self.var_manter_legenda = ctk.BooleanVar(value=False)
        self.chk_manter = ctk.CTkCheckBox(
            self.frame_saida,
            text=I18n.t("chk_manter"),
            variable=self.var_manter_legenda,
            font=(fonte_ui, 11),
            text_color=CORES["texto_principal"],
            border_color=CORES["borda_card"],
            border_width=largura_borda,
            fg_color=CORES["destaque_azul"],
            hover_color=CORES["destaque_azul_hover"],
            checkmark_color=CORES.get("btn_destaque_txt", "#ffffff"),
            corner_radius=raio_card
        )
        self.chk_manter.pack(anchor="w", padx=10, pady=(2, 8))

        # Card do Escudo Anti-Alucinacao
        self.frame_modulos = ctk.CTkFrame(
            self,
            fg_color=CORES["bg_card"],
            border_color=CORES["borda_card"],
            border_width=largura_borda,
            corner_radius=raio_card
        )
        self.frame_modulos.pack(fill="x", padx=12, pady=6)

        self.lbl_escudo = ctk.CTkLabel(
            self.frame_modulos,
            text=I18n.t("escudo_lbl"),
            font=(fonte_ui, 11),
            text_color=CORES["texto_secundario"]
        )
        self.lbl_escudo.pack(anchor="w", padx=10, pady=(8, 2))

        self.lbl_glossario_info = ctk.CTkLabel(
            self.frame_modulos,
            text=I18n.t("escudo_ativo"),
            font=(fonte_ui, 11, "bold"),
            text_color=CORES["destaque_verde"]
        )
        self.lbl_glossario_info.pack(anchor="w", padx=10, pady=(0, 8))

    def aplicar_tema(self, cores: dict):
        """Propaga o novo tema com alto contraste, tipografia e sem pontos cegos nos inputs."""
        largura_borda = cores.get("borda_largura", 1)
        raio_card = cores.get("raio_card", 6)
        fonte_ui = cores.get("fonte_ui", "Segoe UI")

        self.configure(
            fg_color=cores["bg_sidebar"],
            border_color=cores["borda_card"],
            border_width=largura_borda,
            corner_radius=raio_card
        )
        self.lbl_secao.configure(text_color=cores["texto_secundario"], font=(fonte_ui, 11, "bold"))

        # Card de Idiomas
        self.frame_idiomas.configure(
            fg_color=cores["bg_card"],
            border_color=cores["borda_card"],
            border_width=largura_borda,
            corner_radius=raio_card
        )
        self.lbl_origem.configure(text_color=cores["texto_secundario"], font=(fonte_ui, 11))
        self.combo_lang.configure(
            fg_color=cores["combo_bg"],
            button_color=cores["combo_btn"],
            button_hover_color=cores["bg_card_hover"],
            dropdown_fg_color=cores["combo_bg"],
            dropdown_text_color=cores["texto_principal"],
            dropdown_hover_color=cores["bg_card_hover"],
            text_color=cores["texto_principal"],
            font=(fonte_ui, 11),
            dropdown_font=(fonte_ui, 11),
            corner_radius=raio_card
        )
        self.lbl_destino.configure(text_color=cores["texto_secundario"], font=(fonte_ui, 11))
        self.combo_lang_dest.configure(
            fg_color=cores["combo_bg"],
            button_color=cores["combo_btn"],
            button_hover_color=cores["bg_card_hover"],
            dropdown_fg_color=cores["combo_bg"],
            dropdown_text_color=cores["texto_principal"],
            dropdown_hover_color=cores["bg_card_hover"],
            text_color=cores["texto_principal"],
            font=(fonte_ui, 11),
            dropdown_font=(fonte_ui, 11),
            corner_radius=raio_card
        )

        # Card de Saida
        self.frame_saida.configure(
            fg_color=cores["bg_card"],
            border_color=cores["borda_card"],
            border_width=largura_borda,
            corner_radius=raio_card
        )
        self.lbl_saida.configure(text_color=cores["texto_secundario"], font=(fonte_ui, 11))
        self.chk_manter.configure(
            text_color=cores["texto_principal"],
            border_color=cores["borda_card"],
            border_width=largura_borda,
            fg_color=cores["destaque_azul"],
            hover_color=cores["destaque_azul_hover"],
            checkmark_color=cores.get("btn_destaque_txt", "#ffffff"),
            font=(fonte_ui, 11),
            corner_radius=raio_card
        )

        # Card do Escudo
        self.frame_modulos.configure(
            fg_color=cores["bg_card"],
            border_color=cores["borda_card"],
            border_width=largura_borda,
            corner_radius=raio_card
        )
        self.lbl_escudo.configure(text_color=cores["texto_secundario"], font=(fonte_ui, 11))
        self.lbl_glossario_info.configure(text_color=cores["destaque_verde"], font=(fonte_ui, 11, "bold"))

    def redefinir_textos(self):
        """Atualiza todos os rotulos da barra lateral apos mudanca de idioma."""
        idioma = I18n.obter_idioma()
        self.lbl_secao.configure(text=I18n.t("sidebar_titulo"))
        self.lbl_origem.configure(text=I18n.t("origem_lbl"))
        self.lbl_destino.configure(text=I18n.t("destino_lbl"))
        self.lbl_saida.configure(text=I18n.t("saida_lbl"))
        self.chk_manter.configure(text=I18n.t("chk_manter"))
        self.lbl_escudo.configure(text=I18n.t("escudo_lbl"))
        self.lbl_glossario_info.configure(text=I18n.t("escudo_ativo"))

        # Atualiza o dropdown de idioma de destino preservando o codigo selecionado
        cod_dest = self.idioma_destino
        novas_opcoes_dest = Idiomas.opcoes_destino_exibicao(idioma)
        self.combo_lang_dest.configure(values=novas_opcoes_dest)
        self.combo_lang_dest.set(Idiomas.rotular_destino(cod_dest, idioma))

        # Atualiza o dropdown de idioma de origem preservando faixas detectadas
        cod_orig = self.idioma_origem
        valores_atuais = self.combo_lang.cget("values") or []
        codigos_orig = [Idiomas.nome_para_codigo_origem(v) for v in valores_atuais]
        if not codigos_orig:
            codigos_orig = ["auto"]
        novos_rotulos_orig = [Idiomas.rotular_origem(c, idioma) for c in codigos_orig]
        self.combo_lang.configure(values=novos_rotulos_orig)
        self.combo_lang.set(Idiomas.rotular_origem(cod_orig, idioma))

    def _disparar_destino_alterado(self, valor_exibicao: str):
        if self._on_destino_alterado_cb:
            codigo = Idiomas.nome_para_codigo_destino(valor_exibicao)
            self._on_destino_alterado_cb(codigo)

    @property
    def idioma_origem(self) -> str:
        """Retorna o codigo ISO-639 limpo do idioma de origem."""
        return Idiomas.nome_para_codigo_origem(self.combo_lang.get())

    @property
    def idioma_destino(self) -> str:
        """Retorna o codigo Google limpo do idioma de destino."""
        return Idiomas.nome_para_codigo_destino(self.combo_lang_dest.get())

    @property
    def manter_legenda(self) -> bool:
        return self.var_manter_legenda.get()

    def atualizar_opcoes_origem(self, codigos_origem: list, codigo_padrao: str):
        """Atualiza a lista de opcoes com rotulos amigaveis por extenso."""
        idioma = I18n.obter_idioma()
        rotulos = [Idiomas.rotular_origem(cod, idioma) for cod in codigos_origem]
        rotulo_padrao = Idiomas.rotular_origem(codigo_padrao, idioma)
        self.combo_lang.configure(values=rotulos)
        self.combo_lang.set(rotulo_padrao)
