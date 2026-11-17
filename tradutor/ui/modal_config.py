"""Janela modal de Configurações Gerais, IA Local, Armazenamento e Informações do Sistema."""

import threading
import webbrowser
from tkinter import filedialog, messagebox
import customtkinter as ctk

from ..atualizador import VerificadorAtualizacao
from ..cache import CacheTraducoes
from ..config import GerenciadorConfig
from ..config_usuario import PreferenciasUsuario
from ..i18n import I18n
from ..instalador_dependencias import InstaladorDependencias
from .modal_dependencias import ModalDependencias
from .modal_whisper import PainelSeletorWhisper
from .tema import CORES


class ModalConfiguracoes(ctk.CTkToplevel):
    """Modal em abas para configurações de idioma, IA local Whisper, sistema, cache e sobre o projeto."""

    def __init__(self, master, ao_alterar_idioma_cb=None):
        super().__init__(master)
        self.title(I18n.t("modal_config_titulo"))
        self.geometry("650x570")
        self.minsize(590, 520)
        self.configure(fg_color=CORES["bg_janela"])
        self.transient(master)
        self.after(50, self.focus)

        self._ao_alterar_idioma_cb = ao_alterar_idioma_cb
        self._cache = CacheTraducoes()

        self._fonte_ui = CORES.get("fonte_ui", "Segoe UI")
        self._largura_borda = CORES.get("borda_largura", 1)
        self._raio_card = CORES.get("raio_card", 2)

        self._nome_aba_geral = I18n.t("aba_geral")
        self._nome_aba_sistema = I18n.t("aba_sistema")
        self._nome_aba_sobre = I18n.t("aba_sobre")

        self._construir_interface()

    def _criar_frame_card(self, master: ctk.CTkBaseClass) -> ctk.CTkFrame:
        """Cria container padronizado para agrupamento visual de controles."""
        frame = ctk.CTkFrame(
            master,
            fg_color=CORES["bg_card"],
            border_color=CORES["borda_card"],
            border_width=self._largura_borda,
            corner_radius=self._raio_card,
        )
        frame.pack(fill="x", padx=14, pady=6)
        return frame

    def _criar_dropdown(self, master: ctk.CTkBaseClass, opcoes: list[str], comando, valor_inicial: str) -> ctk.CTkOptionMenu:
        """Cria menu suspenso com estilização padronizada do tema utilitário."""
        cmb = ctk.CTkOptionMenu(
            master,
            values=opcoes,
            command=comando,
            fg_color=CORES["combo_bg"],
            button_color=CORES["combo_btn"],
            button_hover_color=CORES["bg_card_hover"],
            dropdown_fg_color=CORES["combo_bg"],
            dropdown_text_color=CORES["texto_principal"],
            dropdown_hover_color=CORES["bg_card_hover"],
            text_color=CORES["texto_principal"],
            font=(self._fonte_ui, 11),
            dropdown_font=(self._fonte_ui, 11),
            corner_radius=self._raio_card,
            height=28,
        )
        cmb.set(valor_inicial)
        return cmb

    def _criar_botao(
        self,
        master: ctk.CTkBaseClass,
        texto_i18n: str,
        comando,
        estilo: str = "primario",
        width: int | None = None,
    ) -> ctk.CTkButton:
        """Cria botão tipado segundo semântica utilitária."""
        configs = {
            "font": (self._fonte_ui, 10, "bold"),
            "corner_radius": self._raio_card,
            "height": 28,
            "command": comando,
        }
        if width:
            configs["width"] = width

        if estilo == "primario":
            configs.update({
                "fg_color": CORES["destaque_azul"],
                "hover_color": CORES["destaque_azul_hover"],
                "text_color": CORES.get("btn_destaque_txt", "#ffffff"),
            })
        elif estilo == "secundario":
            configs.update({
                "fg_color": CORES["bg_sidebar"],
                "hover_color": CORES["bg_card_hover"],
                "border_color": CORES["borda_card"],
                "border_width": self._largura_borda,
                "text_color": CORES["texto_principal"],
            })
        elif estilo == "perigo":
            configs.update({
                "fg_color": CORES["destaque_vermelho"],
                "hover_color": CORES["destaque_vermelho_hover"],
                "text_color": "white",
                "font": (self._fonte_ui, 11, "bold"),
            })

        return ctk.CTkButton(master, text=I18n.t(texto_i18n), **configs)

    def _criar_label_secao(self, master: ctk.CTkBaseClass, chave_i18n: str, pady: tuple[int, int] = (12, 4)) -> ctk.CTkLabel:
        """Cria rótulo de cabeçalho de seção padronizado."""
        lbl = ctk.CTkLabel(
            master,
            text=I18n.t(chave_i18n),
            font=(self._fonte_ui, 12, "bold"),
            text_color=CORES["texto_secundario"],
        )
        lbl.pack(anchor="w", padx=16, pady=pady)
        return lbl

    def _criar_switch(self, master: ctk.CTkBaseClass, chave_i18n: str, chave_pref: str, padrao: bool) -> ctk.CTkSwitch:
        """Cria switch estilizado integrado ao dicionário de preferências."""
        sw = ctk.CTkSwitch(
            master,
            text=I18n.t(chave_i18n),
            font=(self._fonte_ui, 11),
            text_color=CORES["texto_principal"],
            progress_color=CORES["destaque_verde"],
            fg_color=CORES.get("progressbar_bg", CORES["bg_card"]),
            button_color=CORES["texto_principal"],
            button_hover_color=CORES["destaque_azul"],
            command=self._salvar_switches,
        )
        if PreferenciasUsuario.obter(chave_pref, padrao):
            sw.select()
        sw.pack(anchor="w", padx=16, pady=4)
        return sw

    def _construir_interface(self):
        """Monta o container tabview e as 3 abas principais."""
        self.tabview = ctk.CTkTabview(
            self,
            fg_color=CORES["bg_sidebar"],
            border_color=CORES["borda_card"],
            border_width=self._largura_borda,
            corner_radius=self._raio_card,
            segmented_button_fg_color=CORES["bg_card"],
            segmented_button_selected_color=CORES["destaque_azul"],
            segmented_button_selected_hover_color=CORES["destaque_azul_hover"],
            segmented_button_unselected_color=CORES["bg_card"],
            segmented_button_unselected_hover_color=CORES["bg_card_hover"],
            text_color=CORES.get("btn_destaque_txt", "#ffffff"),
        )
        self.tabview.pack(fill="both", expand=True, padx=14, pady=12)

        aba_geral = self.tabview.add(self._nome_aba_geral)
        aba_sistema = self.tabview.add(self._nome_aba_sistema)
        aba_sobre = self.tabview.add(self._nome_aba_sobre)

        self._montar_aba_geral(aba_geral)
        self._montar_aba_sistema(aba_sistema)
        self._montar_aba_sobre(aba_sobre)

    def _montar_aba_geral(self, aba: ctk.CTkBaseClass):
        """Monta opções gerais de preferência, áudio e modelo Whisper."""
        self.lbl_sec_pref = self._criar_label_secao(aba, "sec_preferencias", pady=(8, 4))

        frame_idioma = self._criar_frame_card(aba)
        self.lbl_idioma_tit = ctk.CTkLabel(
            frame_idioma,
            text=I18n.t("lbl_idioma_app"),
            font=(self._fonte_ui, 11),
            text_color=CORES["texto_principal"],
        )
        self.lbl_idioma_tit.pack(side="left", padx=12, pady=8)

        idioma_atual = I18n.IDIOMAS_SUPORTADOS.get(I18n.obter_idioma(), "Português (Brasil)")
        self.cmb_idioma = self._criar_dropdown(
            frame_idioma,
            list(I18n.IDIOMAS_SUPORTADOS.values()),
            self._ao_selecionar_idioma,
            idioma_atual,
        )
        self.cmb_idioma.pack(side="right", padx=12, pady=8)

        self.sw_som = self._criar_switch(aba, "sw_som_notif", "tocar_som", True)
        self.sw_pasta = self._criar_switch(aba, "sw_abrir_pasta", "abrir_pasta_ao_concluir", False)
        self.sw_anilist = self._criar_switch(aba, "sw_auto_anilist", "auto_alimentar_anilist", True)
        self.sw_atualizacoes = self._criar_switch(
            aba, "sw_verificar_atualizacoes", "verificar_atualizacoes_ao_iniciar", True
        )

        self.lbl_sec_ia = self._criar_label_secao(aba, "sec_ia_whisper")
        self.painel_whisper = PainelSeletorWhisper(aba)
        self.painel_whisper.pack(fill="x", padx=14, pady=4)
        self.sw_forcar_whisper = self._criar_switch(aba, "sw_forcar_transcricao", "forcar_transcricao", False)

    def _montar_aba_sistema(self, aba: ctk.CTkBaseClass):
        """Monta controles de dependências de vídeo, política de conflito e cache."""
        self.lbl_sec_sis = self._criar_label_secao(aba, "sec_sistema")

        frame_mkv = self._criar_frame_card(aba)
        self.lbl_mkv_status = ctk.CTkLabel(
            frame_mkv,
            text=self._obter_texto_status_mkv(),
            font=(self._fonte_ui, 11),
            justify="left",
            wraplength=310,
        )
        self._atualizar_visual_status_mkv()
        self.lbl_mkv_status.pack(side="left", padx=12, pady=10)

        self.btn_mkv_config = self._criar_botao(frame_mkv, "btn_mkv_configurar", self._abrir_modal_dependencias, width=115)
        self.btn_mkv_config.pack(side="right", padx=(4, 12), pady=10)

        self.btn_mkv_pasta = self._criar_botao(frame_mkv, "btn_mkv_alterar_pasta", self._selecionar_pasta_mkv_manual, estilo="secundario", width=115)
        self.btn_mkv_pasta.pack(side="right", padx=4, pady=10)

        frame_sob = self._criar_frame_card(aba)
        self.lbl_conflito_tit = ctk.CTkLabel(
            frame_sob,
            text=I18n.t("lbl_conflito"),
            font=(self._fonte_ui, 11),
            text_color=CORES["texto_principal"],
        )
        self.lbl_conflito_tit.pack(side="left", padx=12, pady=10)

        self.politicas_map = {
            "perguntar": "opt_perguntar",
            "sobrescrever": "opt_sobrescrever",
            "pular": "opt_pular",
        }
        chave_atual_pol = PreferenciasUsuario.obter("politica_sobrescrita", "perguntar")
        valor_atual_pol = I18n.t(self.politicas_map.get(chave_atual_pol, "opt_perguntar"))
        self.cmb_politica = self._criar_dropdown(
            frame_sob,
            [I18n.t(v) for v in self.politicas_map.values()],
            self._ao_alterar_politica,
            valor_atual_pol,
        )
        self.cmb_politica.pack(side="right", padx=12, pady=10)

        frame_fmt = self._criar_frame_card(aba)
        self.lbl_formato_tit = ctk.CTkLabel(
            frame_fmt,
            text=I18n.t("lbl_formato_saida_video"),
            font=(self._fonte_ui, 11),
            text_color=CORES["texto_principal"],
        )
        self.lbl_formato_tit.pack(side="left", padx=12, pady=10)

        self.formatos_map = {
            "perguntar": "opt_formato_perguntar",
            "converter_mkv": "opt_formato_mkv",
            "manter_original": "opt_formato_original",
        }
        chave_atual_fmt = PreferenciasUsuario.obter("formato_saida_video", "perguntar")
        valor_atual_fmt = I18n.t(self.formatos_map.get(chave_atual_fmt, "opt_formato_perguntar"))
        self.cmb_formato_saida = self._criar_dropdown(
            frame_fmt,
            [I18n.t(v) for v in self.formatos_map.values()],
            self._ao_alterar_formato_saida,
            valor_atual_fmt,
        )
        self.cmb_formato_saida.pack(side="right", padx=12, pady=10)

        frame_cache = self._criar_frame_card(aba)
        self.lbl_cache_info = ctk.CTkLabel(
            frame_cache,
            text=self._obter_texto_cache(),
            font=(self._fonte_ui, 11),
            text_color=CORES["texto_principal"],
            justify="left",
        )
        self.lbl_cache_info.pack(side="left", padx=12, pady=12)

        self.btn_limpar_cache = self._criar_botao(frame_cache, "btn_limpar_cache", self._confirmar_limpeza_cache, estilo="perigo", width=120)
        self.btn_limpar_cache.pack(side="right", padx=12, pady=12)

    def _montar_aba_sobre(self, aba: ctk.CTkBaseClass):
        """Monta informações de versão, links de repositório e verificador de atualização."""
        ctk.CTkLabel(aba, text="TRADUTOR DE LEGENDAS", font=(self._fonte_ui, 16, "bold"), text_color=CORES["texto_principal"]).pack(pady=(20, 2))
        self.lbl_sobre_versao = ctk.CTkLabel(aba, text=f"{I18n.t('lbl_versao')} (Lossless Modern UI)", font=(self._fonte_ui, 12), text_color=CORES["destaque_azul"])
        self.lbl_sobre_versao.pack(pady=(0, 10))

        self.lbl_sobre_desc = ctk.CTkLabel(aba, text=I18n.t("desc_sobre"), font=(self._fonte_ui, 11), text_color=CORES["texto_secundario"], justify="center")
        self.lbl_sobre_desc.pack(pady=8)

        frame_acoes = ctk.CTkFrame(aba, fg_color="transparent")
        frame_acoes.pack(pady=10)

        self.btn_github = self._criar_botao(frame_acoes, "btn_github", lambda: webbrowser.open_new_tab(VerificadorAtualizacao.URL_REPOSITORIO))
        self.btn_github.pack(side="left", padx=6)

        self.btn_verificar_update = self._criar_botao(frame_acoes, "btn_verificar_atualizacao", self._iniciar_verificacao_atualizacao, estilo="secundario")
        self.btn_verificar_update.pack(side="left", padx=6)

        self.lbl_status_update = ctk.CTkLabel(aba, text="", font=(self._fonte_ui, 11), text_color=CORES["texto_secundario"])
        self.lbl_status_update.pack(pady=(2, 4))

        self.btn_creditos_autor = ctk.CTkButton(
            aba,
            text=I18n.t("lbl_creditos_autor"),
            font=(self._fonte_ui, 11, "underline"),
            fg_color="transparent",
            hover_color=CORES["bg_card_hover"],
            text_color=CORES["destaque_azul"],
            corner_radius=self._raio_card,
            height=26,
            command=lambda: webbrowser.open_new_tab(VerificadorAtualizacao.URL_PERFIL_AUTOR),
        )
        self.btn_creditos_autor.pack(pady=(4, 2))

        self.lbl_licenca = ctk.CTkLabel(aba, text=I18n.t("lbl_licenca"), font=(self._fonte_ui, 10), text_color=CORES["texto_escuro"])
        self.lbl_licenca.pack(side="bottom", pady=12)

    def _iniciar_verificacao_atualizacao(self):
        """Despacha a consulta da API do GitHub em thread de fundo sem bloquear a UI."""
        self.btn_verificar_update.configure(state="disabled")
        self.lbl_status_update.configure(text=I18n.t("lbl_verificando_atualizacao"), text_color=CORES["texto_secundario"])

        def _executar():
            resultado = VerificadorAtualizacao.verificar()
            self.after(0, lambda: self._exibir_resultado_atualizacao(resultado))

        threading.Thread(target=_executar, daemon=True).start()

    def _exibir_resultado_atualizacao(self, resultado):
        """Renderiza a resposta da checagem de versão de forma thread-safe."""
        if not self.winfo_exists():
            return

        if not resultado.sucesso:
            self.btn_verificar_update.configure(
                state="normal",
                text=I18n.t("btn_verificar_atualizacao"),
                command=self._iniciar_verificacao_atualizacao,
            )
            self.lbl_status_update.configure(text=I18n.t("lbl_erro_atualizacao"), text_color=CORES["destaque_vermelho"])
            return

        if resultado.atualizacao_disponivel:
            self.lbl_status_update.configure(
                text=I18n.t("lbl_nova_versao_disponivel").format(resultado.versao_remota, resultado.versao_atual),
                text_color=CORES["destaque_verde"],
            )
            self.btn_verificar_update.configure(
                state="normal",
                text=I18n.t("btn_baixar_atualizacao").format(resultado.versao_remota),
                fg_color=CORES["destaque_verde"],
                hover_color=CORES["destaque_verde_hover"],
                text_color=CORES.get("btn_iniciar_txt", "#ffffff"),
                command=lambda: webbrowser.open_new_tab(resultado.url_download),
            )
        else:
            self.btn_verificar_update.configure(
                state="normal",
                text=I18n.t("btn_verificar_atualizacao"),
                command=self._iniciar_verificacao_atualizacao,
            )
            self.lbl_status_update.configure(
                text=I18n.t("lbl_atualizado").format(resultado.versao_atual),
                text_color=CORES["destaque_verde"],
            )

    def _obter_texto_status_mkv(self) -> str:
        """Formata o texto de status do binário MKVToolNix."""
        if GerenciadorConfig.check_dependencies():
            return I18n.t("lbl_mkv_status_ok").format(GerenciadorConfig.get_mkvtoolnix_path())
        return I18n.t("lbl_mkv_status_ausente")

    def _atualizar_visual_status_mkv(self):
        """Atualiza a cor e o rótulo do status do MKVToolNix."""
        ok = GerenciadorConfig.check_dependencies()
        self.lbl_mkv_status.configure(
            text=self._obter_texto_status_mkv(),
            text_color=CORES["destaque_verde"] if ok else CORES["destaque_vermelho"],
        )

    def _selecionar_pasta_mkv_manual(self):
        """Permite ao usuário localizar manualmente o diretório do MKVToolNix."""
        pasta = filedialog.askdirectory(parent=self, title=I18n.t("btn_dep_outra_pasta"))
        if pasta:
            sucesso, _ = InstaladorDependencias.definir_pasta_existente(pasta)
            if not sucesso:
                messagebox.showwarning(I18n.t("aviso_titulo"), I18n.t("lbl_dep_pasta_invalida"), parent=self)
            self._atualizar_visual_status_mkv()

    def _abrir_modal_dependencias(self):
        """Abre o instalador/configurador assistido de dependências."""
        ModalDependencias(self, ao_decidir_cb=lambda _: self._atualizar_visual_status_mkv())

    def _obter_texto_cache(self) -> str:
        """Retorna resumo de volume do banco de dados de cache SQLite."""
        msg_corpo = I18n.t("lbl_traducoes_salvas").format(
            self._cache.contar_traducoes(),
            self._cache.obter_tamanho_bytes() / 1024,
        )
        return f"{I18n.t('lbl_cache_banco')}\n{msg_corpo}"

    def _salvar_switches(self):
        """Persiste o estado das opções booleanas no arquivo de preferências."""
        PreferenciasUsuario.definir("tocar_som", bool(self.sw_som.get()))
        PreferenciasUsuario.definir("abrir_pasta_ao_concluir", bool(self.sw_pasta.get()))
        PreferenciasUsuario.definir("auto_alimentar_anilist", bool(self.sw_anilist.get()))
        PreferenciasUsuario.definir("forcar_transcricao", bool(self.sw_forcar_whisper.get()))
        PreferenciasUsuario.definir("verificar_atualizacoes_ao_iniciar", bool(self.sw_atualizacoes.get()))

    def _encontrar_chave_mapa(self, mapa: dict[str, str], valor_visivel: str) -> str | None:
        """Resolve a chave de configuração a partir da string localizada do combobox."""
        return next((k for k, v in mapa.items() if I18n.t(v) == valor_visivel), None)

    def _ao_alterar_politica(self, valor_visivel: str):
        chave = self._encontrar_chave_mapa(self.politicas_map, valor_visivel)
        if chave:
            PreferenciasUsuario.definir("politica_sobrescrita", chave)

    def _ao_alterar_formato_saida(self, valor_visivel: str):
        chave = self._encontrar_chave_mapa(self.formatos_map, valor_visivel)
        if chave:
            PreferenciasUsuario.definir("formato_saida_video", chave)

    def _ao_selecionar_idioma(self, valor_visivel: str):
        codigo = next((k for k, v in I18n.IDIOMAS_SUPORTADOS.items() if v == valor_visivel), "pt-br")
        I18n.definir_idioma(codigo)
        self._redefinir_textos()
        if self._ao_alterar_idioma_cb:
            self._ao_alterar_idioma_cb(codigo)

    def _redefinir_textos(self):
        """Atualiza dinamicamente todos os textos da janela após mudança de idioma."""
        self.title(I18n.t("modal_config_titulo"))
        self.lbl_sec_pref.configure(text=I18n.t("sec_preferencias"))
        self.lbl_idioma_tit.configure(text=I18n.t("lbl_idioma_app"))
        self.sw_som.configure(text=I18n.t("sw_som_notif"))
        self.sw_pasta.configure(text=I18n.t("sw_abrir_pasta"))
        self.sw_anilist.configure(text=I18n.t("sw_auto_anilist"))
        self.sw_atualizacoes.configure(text=I18n.t("sw_verificar_atualizacoes"))
        self.lbl_sec_ia.configure(text=I18n.t("sec_ia_whisper"))
        self.painel_whisper.lbl_titulo.configure(text=I18n.t("lbl_modelo_whisper"))
        self.painel_whisper.atualizar_opcoes()
        self.sw_forcar_whisper.configure(text=I18n.t("sw_forcar_transcricao"))

        self.lbl_sec_sis.configure(text=I18n.t("sec_sistema"))
        self._atualizar_visual_status_mkv()
        self.btn_mkv_pasta.configure(text=I18n.t("btn_mkv_alterar_pasta"))
        self.btn_mkv_config.configure(text=I18n.t("btn_mkv_configurar"))

        self.lbl_conflito_tit.configure(text=I18n.t("lbl_conflito"))
        self.cmb_politica.configure(values=[I18n.t(v) for v in self.politicas_map.values()])
        chave_atual_pol = PreferenciasUsuario.obter("politica_sobrescrita", "perguntar")
        self.cmb_politica.set(I18n.t(self.politicas_map.get(chave_atual_pol, "opt_perguntar")))

        self.lbl_formato_tit.configure(text=I18n.t("lbl_formato_saida_video"))
        self.cmb_formato_saida.configure(values=[I18n.t(v) for v in self.formatos_map.values()])
        chave_atual_fmt = PreferenciasUsuario.obter("formato_saida_video", "perguntar")
        self.cmb_formato_saida.set(I18n.t(self.formatos_map.get(chave_atual_fmt, "opt_formato_perguntar")))

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
        if self.btn_verificar_update.cget("state") == "normal":
            self.btn_verificar_update.configure(text=I18n.t("btn_verificar_atualizacao"))
        self.btn_creditos_autor.configure(text=I18n.t("lbl_creditos_autor"))
        self.lbl_licenca.configure(text=I18n.t("lbl_licenca"))

    def _confirmar_limpeza_cache(self):
        """Solicita confirmação e executa a limpeza total do cache SQLite."""
        if messagebox.askyesno(I18n.t("btn_limpar_cache"), I18n.t("msg_confirmar_limpar_cache")):
            self._cache.limpar_tudo()
            self.lbl_cache_info.configure(text=self._obter_texto_cache())
            messagebox.showinfo("OK", I18n.t("msg_cache_sucesso"))
