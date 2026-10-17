"""Janela modal de Configuracoes Gerais, Armazenamento e Informacoes do Sistema."""

import webbrowser
from tkinter import messagebox
import customtkinter as ctk

from ..config_usuario import PreferenciasUsuario
from ..cache import CacheTraducoes
from ..i18n import I18n
from .tema import CORES


class ModalConfiguracoes(ctk.CTkToplevel):
    """Modal em abas para configuracoes de idioma, sistema, cache e sobre o projeto."""

    def __init__(self, master, ao_alterar_idioma_cb=None):
        super().__init__(master)
        self.title(I18n.t("modal_config_titulo"))
        self.geometry("640x510")
        self.minsize(580, 460)
        self.configure(fg_color=CORES["bg_janela"])
        self.transient(master)
        self.after(50, self.focus)

        self._ao_alterar_idioma_cb = ao_alterar_idioma_cb
        self._cache = CacheTraducoes()
        self._construir_interface()

    def _construir_interface(self):
        largura_borda = CORES.get("borda_largura", 1)
        raio_card = CORES.get("raio_card", 6)

        self.tabview = ctk.CTkTabview(
            self,
            fg_color=CORES["bg_sidebar"],
            border_color=CORES["borda_card"],
            border_width=largura_borda,
            corner_radius=raio_card,
            segmented_button_fg_color=CORES["bg_card"],
            segmented_button_selected_color=CORES["destaque_azul"],
            segmented_button_selected_hover_color=CORES["destaque_azul_hover"],
            segmented_button_unselected_color=CORES["bg_card"],
            segmented_button_unselected_hover_color=CORES["bg_card_hover"],
            text_color=CORES.get("btn_destaque_txt", "#ffffff")
        )
        self.tabview.pack(fill="both", expand=True, padx=14, pady=12)

        self._nome_aba_geral = I18n.t("aba_geral")
        self._nome_aba_sistema = I18n.t("aba_sistema")
        self._nome_aba_sobre = I18n.t("aba_sobre")

        self.aba_geral = self.tabview.add(self._nome_aba_geral)
        self.aba_sistema = self.tabview.add(self._nome_aba_sistema)
        self.aba_sobre = self.tabview.add(self._nome_aba_sobre)

        self._montar_aba_geral(self.aba_geral)
        self._montar_aba_sistema(self.aba_sistema)
        self._montar_aba_sobre(self.aba_sobre)

    def _montar_aba_geral(self, aba):
        largura_borda = CORES.get("borda_largura", 1)
        raio_card = CORES.get("raio_card", 6)
        fonte_ui = CORES.get("fonte_ui", "Segoe UI")

        self.lbl_sec_pref = ctk.CTkLabel(
            aba,
            text=I18n.t("sec_preferencias"),
            font=(fonte_ui, 12, "bold"),
            text_color=CORES["texto_secundario"]
        )
        self.lbl_sec_pref.pack(anchor="w", padx=16, pady=(12, 6))

        frame_idioma = ctk.CTkFrame(
            aba,
            fg_color=CORES["bg_card"],
            border_color=CORES["borda_card"],
            border_width=largura_borda,
            corner_radius=raio_card
        )
        frame_idioma.pack(fill="x", padx=14, pady=6)

        self.lbl_idioma_tit = ctk.CTkLabel(
            frame_idioma,
            text=I18n.t("lbl_idioma_app"),
            font=(fonte_ui, 11),
            text_color=CORES["texto_principal"]
        )
        self.lbl_idioma_tit.pack(side="left", padx=12, pady=10)

        opcoes_idioma = list(I18n.IDIOMAS_SUPORTADOS.values())
        idioma_atual = I18n.IDIOMAS_SUPORTADOS.get(I18n.obter_idioma(), "Português (Brasil)")

        self.cmb_idioma = ctk.CTkOptionMenu(
            frame_idioma,
            values=opcoes_idioma,
            command=self._ao_selecionar_idioma,
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
        self.cmb_idioma.set(idioma_atual)
        self.cmb_idioma.pack(side="right", padx=12, pady=10)

        # Switches
        self.sw_som = ctk.CTkSwitch(
            aba,
            text=I18n.t("sw_som_notif"),
            font=(fonte_ui, 11),
            text_color=CORES["texto_principal"],
            progress_color=CORES["destaque_verde"],
            fg_color=CORES.get("progressbar_bg", CORES["bg_card"]),
            button_color=CORES["texto_principal"],
            button_hover_color=CORES["destaque_azul"],
            command=self._salvar_switches
        )
        if PreferenciasUsuario.obter("tocar_som", True):
            self.sw_som.select()
        self.sw_som.pack(anchor="w", padx=16, pady=(12, 6))

        self.sw_pasta = ctk.CTkSwitch(
            aba,
            text=I18n.t("sw_abrir_pasta"),
            font=(fonte_ui, 11),
            text_color=CORES["texto_principal"],
            progress_color=CORES["destaque_verde"],
            fg_color=CORES.get("progressbar_bg", CORES["bg_card"]),
            button_color=CORES["texto_principal"],
            button_hover_color=CORES["destaque_azul"],
            command=self._salvar_switches
        )
        if PreferenciasUsuario.obter("abrir_pasta_ao_concluir", False):
            self.sw_pasta.select()
        self.sw_pasta.pack(anchor="w", padx=16, pady=6)

    def _montar_aba_sistema(self, aba):
        largura_borda = CORES.get("borda_largura", 1)
        raio_card = CORES.get("raio_card", 6)
        fonte_ui = CORES.get("fonte_ui", "Segoe UI")

        self.lbl_sec_sis = ctk.CTkLabel(
            aba,
            text=I18n.t("sec_sistema"),
            font=(fonte_ui, 12, "bold"),
            text_color=CORES["texto_secundario"]
        )
        self.lbl_sec_sis.pack(anchor="w", padx=16, pady=(12, 6))

        # Sobrescrita
        frame_sob = ctk.CTkFrame(
            aba,
            fg_color=CORES["bg_card"],
            border_color=CORES["borda_card"],
            border_width=largura_borda,
            corner_radius=raio_card
        )
        frame_sob.pack(fill="x", padx=14, pady=6)

        self.lbl_conflito_tit = ctk.CTkLabel(
            frame_sob,
            text=I18n.t("lbl_conflito"),
            font=(fonte_ui, 11),
            text_color=CORES["texto_principal"]
        )
        self.lbl_conflito_tit.pack(side="left", padx=12, pady=10)

        self.politicas_map = {
            "perguntar": I18n.t("opt_perguntar"),
            "sobrescrever": I18n.t("opt_sobrescrever"),
            "pular": I18n.t("opt_pular")
        }
        self.cmb_politica = ctk.CTkOptionMenu(
            frame_sob,
            values=list(self.politicas_map.values()),
            command=self._ao_alterar_politica,
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
        chave_atual = PreferenciasUsuario.obter("politica_sobrescrita", "perguntar")
        self.cmb_politica.set(self.politicas_map.get(chave_atual, I18n.t("opt_perguntar")))
        self.cmb_politica.pack(side="right", padx=12, pady=10)

        # Cache SQLite
        frame_cache = ctk.CTkFrame(
            aba,
            fg_color=CORES["bg_card"],
            border_color=CORES["borda_card"],
            border_width=largura_borda,
            corner_radius=raio_card
        )
        frame_cache.pack(fill="x", padx=14, pady=10)

        self.lbl_cache_info = ctk.CTkLabel(
            frame_cache,
            text=self._obter_texto_cache(),
            font=(fonte_ui, 11),
            text_color=CORES["texto_principal"],
            justify="left"
        )
        self.lbl_cache_info.pack(side="left", padx=12, pady=12)

        self.btn_limpar_cache = ctk.CTkButton(
            frame_cache,
            text=I18n.t("btn_limpar_cache"),
            font=(fonte_ui, 11, "bold"),
            fg_color=CORES["destaque_vermelho"],
            hover_color=CORES["destaque_vermelho_hover"],
            text_color="white",
            corner_radius=raio_card,
            width=120,
            height=30,
            command=self._confirmar_limpeza_cache
        )
        self.btn_limpar_cache.pack(side="right", padx=12, pady=12)

    def _montar_aba_sobre(self, aba):
        raio_card = CORES.get("raio_card", 6)
        fonte_ui = CORES.get("fonte_ui", "Segoe UI")

        self.lbl_sobre_tit = ctk.CTkLabel(
            aba,
            text="TRADUTOR DE LEGENDAS",
            font=(fonte_ui, 16, "bold"),
            text_color=CORES["texto_principal"]
        )
        self.lbl_sobre_tit.pack(pady=(20, 2))
        self.lbl_sobre_versao = ctk.CTkLabel(
            aba,
            text=f"{I18n.t('lbl_versao')} (Lossless Modern UI)",
            font=(fonte_ui, 12),
            text_color=CORES["destaque_azul"]
        )
        self.lbl_sobre_versao.pack(pady=(0, 10))

        self.lbl_sobre_desc = ctk.CTkLabel(
            aba,
            text=I18n.t("desc_sobre"),
            font=(fonte_ui, 11),
            text_color=CORES["texto_secundario"],
            justify="center"
        )
        self.lbl_sobre_desc.pack(pady=8)

        self.btn_github = ctk.CTkButton(
            aba,
            text=I18n.t("btn_github"),
            font=(fonte_ui, 11, "bold"),
            fg_color=CORES["destaque_azul"],
            hover_color=CORES["destaque_azul_hover"],
            text_color=CORES.get("btn_destaque_txt", "#ffffff"),
            corner_radius=raio_card,
            height=32,
            command=lambda: webbrowser.open_new_tab("https://github.com/Xaxadox/TradutorDeLegendas")
        )
        self.btn_github.pack(pady=16)

        self.lbl_licenca = ctk.CTkLabel(
            aba,
            text=I18n.t("lbl_licenca"),
            font=(fonte_ui, 10),
            text_color=CORES["texto_escuro"]
        )
        self.lbl_licenca.pack(side="bottom", pady=12)

    def _obter_texto_cache(self) -> str:
        total = self._cache.contar_traducoes()
        tamanho_kb = self._cache.obter_tamanho_bytes() / 1024
        msg_corpo = I18n.t("lbl_traducoes_salvas").format(total, tamanho_kb)
        return f"{I18n.t('lbl_cache_banco')}\n{msg_corpo}"

    def _salvar_switches(self):
        PreferenciasUsuario.definir("tocar_som", bool(self.sw_som.get()))
        PreferenciasUsuario.definir("abrir_pasta_ao_concluir", bool(self.sw_pasta.get()))

    def _ao_alterar_politica(self, valor_visivel: str):
        for k, v in self.politicas_map.items():
            if v == valor_visivel:
                PreferenciasUsuario.definir("politica_sobrescrita", k)
                break

    def _ao_selecionar_idioma(self, valor_visivel: str):
        codigo = next((k for k, v in I18n.IDIOMAS_SUPORTADOS.items() if v == valor_visivel), "pt-br")
        I18n.definir_idioma(codigo)
        self._redefinir_textos()
        if self._ao_alterar_idioma_cb:
            self._ao_alterar_idioma_cb(codigo)

    def _redefinir_textos(self):
        self.title(I18n.t("modal_config_titulo"))
        self.lbl_sec_pref.configure(text=I18n.t("sec_preferencias"))
        self.lbl_idioma_tit.configure(text=I18n.t("lbl_idioma_app"))
        self.sw_som.configure(text=I18n.t("sw_som_notif"))
        self.sw_pasta.configure(text=I18n.t("sw_abrir_pasta"))

        self.lbl_sec_sis.configure(text=I18n.t("sec_sistema"))
        self.lbl_conflito_tit.configure(text=I18n.t("lbl_conflito"))
        self.politicas_map = {
            "perguntar": I18n.t("opt_perguntar"),
            "sobrescrever": I18n.t("opt_sobrescrever"),
            "pular": I18n.t("opt_pular")
        }
        self.cmb_politica.configure(values=list(self.politicas_map.values()))
        chave_atual = PreferenciasUsuario.obter("politica_sobrescrita", "perguntar")
        self.cmb_politica.set(self.politicas_map.get(chave_atual, I18n.t("opt_perguntar")))

        self.lbl_cache_info.configure(text=self._obter_texto_cache())
        self.btn_limpar_cache.configure(text=I18n.t("btn_limpar_cache"))

        novo_geral = I18n.t("aba_geral")
        novo_sistema = I18n.t("aba_sistema")
        novo_sobre = I18n.t("aba_sobre")
        if self._nome_aba_geral != novo_geral:
            self.tabview.rename(self._nome_aba_geral, novo_geral)
            self._nome_aba_geral = novo_geral
        if self._nome_aba_sistema != novo_sistema:
            self.tabview.rename(self._nome_aba_sistema, novo_sistema)
            self._nome_aba_sistema = novo_sistema
        if self._nome_aba_sobre != novo_sobre:
            self.tabview.rename(self._nome_aba_sobre, novo_sobre)
            self._nome_aba_sobre = novo_sobre

        self.lbl_sobre_versao.configure(text=f"{I18n.t('lbl_versao')} (Lossless Modern UI)")
        self.lbl_sobre_desc.configure(text=I18n.t("desc_sobre"))
        self.btn_github.configure(text=I18n.t("btn_github"))
        self.lbl_licenca.configure(text=I18n.t("lbl_licenca"))

    def _confirmar_limpeza_cache(self):
        if messagebox.askyesno(I18n.t("btn_limpar_cache"), I18n.t("msg_confirmar_limpar_cache")):
            self._cache.limpar_tudo()
            self.lbl_cache_info.configure(text=self._obter_texto_cache())
            messagebox.showinfo("OK", I18n.t("msg_cache_sucesso"))
