"""Componentes visuais para selecao, download, analise e confirmacao de modelos de IA local (Whisperfile)."""

import os
import threading
from tkinter import filedialog
import customtkinter as ctk

from ..config_usuario import PreferenciasUsuario
from ..i18n import I18n
from ..idiomas import Idiomas
from ..transcritores import DiagnosticoAudioWhisper, MotorWhisperfile, RecomendadorModeloWhisper
from .tema import CORES


class PainelSeletorWhisper(ctk.CTkFrame):
    """Card reutilizavel para escolha, analise de video e download sob demanda de modelos Mozilla Whisperfile."""

    def __init__(self, master, ao_mudar_estado_cb=None, caminho_arquivo_padrao: str | None = None):
        largura_borda = CORES.get("borda_largura", 1)
        raio_card = CORES.get("raio_card", 6)
        super().__init__(
            master,
            fg_color=CORES["bg_card"],
            border_color=CORES["borda_card"],
            border_width=largura_borda,
            corner_radius=raio_card,
        )
        self._ao_mudar_estado_cb = ao_mudar_estado_cb
        self._caminho_arquivo_padrao = caminho_arquivo_padrao
        self._baixando = False
        self._analisando = False
        self._cancelado = False
        self._mapa_rotulo_para_id = {}

        self._construir_widgets()
        self.atualizar_opcoes()

    def _construir_widgets(self):
        fonte_ui = CORES.get("fonte_ui", "Segoe UI")
        raio_card = CORES.get("raio_card", 6)

        frame_topo = ctk.CTkFrame(self, fg_color="transparent")
        frame_topo.pack(fill="x", padx=12, pady=(10, 4))

        self.lbl_titulo = ctk.CTkLabel(
            frame_topo,
            text=I18n.t("lbl_modelo_whisper"),
            font=(fonte_ui, 11, "bold"),
            text_color=CORES["texto_principal"],
        )
        self.lbl_titulo.pack(side="left")

        self.btn_analisar = ctk.CTkButton(
            frame_topo,
            text=I18n.t("btn_analisar_video_whisper"),
            font=(fonte_ui, 10, "bold"),
            fg_color=CORES["bg_sidebar"],
            hover_color=CORES["bg_card_hover"],
            border_color=CORES["destaque_azul"],
            border_width=1,
            text_color=CORES["destaque_azul"],
            corner_radius=raio_card,
            height=24,
            command=self._solicitar_analise_video,
        )
        if self._caminho_arquivo_padrao:
            self.btn_analisar.pack(side="right")

        frame_linha = ctk.CTkFrame(self, fg_color="transparent")
        frame_linha.pack(fill="x", padx=12, pady=(2, 6))

        self.cmb_modelo = ctk.CTkOptionMenu(
            frame_linha,
            values=["..."],
            command=self._ao_selecionar_modelo,
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
            height=30,
        )
        self.cmb_modelo.pack(side="left", fill="x", expand=True, padx=(0, 8))

        self.btn_baixar = ctk.CTkButton(
            frame_linha,
            text=I18n.t("btn_baixar_modelo"),
            font=(fonte_ui, 11, "bold"),
            fg_color=CORES["destaque_azul"],
            hover_color=CORES["destaque_azul_hover"],
            text_color=CORES.get("btn_destaque_txt", "#ffffff"),
            corner_radius=raio_card,
            width=135,
            height=30,
            command=lambda: self.iniciar_download(),
        )
        self.btn_baixar.pack(side="right")

        self.barra_progresso = ctk.CTkProgressBar(
            self,
            height=6,
            corner_radius=3,
            fg_color=CORES.get("progressbar_bg", CORES["bg_sidebar"]),
            progress_color=CORES["destaque_azul"],
        )
        self.barra_progresso.set(0)

        self.lbl_diagnostico = ctk.CTkLabel(
            self,
            text="",
            font=(fonte_ui, 10),
            text_color=CORES["texto_principal"],
            justify="left",
            wraplength=500,
        )

        self.lbl_status = ctk.CTkLabel(
            self,
            text="",
            font=(fonte_ui, 10, "bold"),
            text_color=CORES["texto_secundario"],
        )
        self.lbl_status.pack(anchor="w", padx=12, pady=(2, 10))

    @property
    def modelo_selecionado(self) -> str:
        rotulo_atual = self.cmb_modelo.get()
        return self._mapa_rotulo_para_id.get(
            rotulo_atual, PreferenciasUsuario.obter("modelo_whisper", "small")
        )

    @property
    def esta_instalado(self) -> bool:
        return MotorWhisperfile.esta_modelo_instalado(self.modelo_selecionado)

    @property
    def esta_baixando(self) -> bool:
        return self._baixando

    def cancelar_download(self):
        self._cancelado = True

    def atualizar_opcoes(self):
        self._mapa_rotulo_para_id.clear()
        opcoes = []
        id_preferido = PreferenciasUsuario.obter("modelo_whisper", "small")
        rotulo_selecionado = None

        for id_mod, info in MotorWhisperfile.CATALOGO_MODELOS.items():
            instalado = MotorWhisperfile.esta_modelo_instalado(id_mod)
            badge = I18n.t("badge_instalado") if instalado else I18n.t("badge_nao_baixado")
            rotulo = f"[{badge}] {I18n.t(info['chave_nome'])}"
            self._mapa_rotulo_para_id[rotulo] = id_mod
            opcoes.append(rotulo)
            if id_mod == id_preferido:
                rotulo_selecionado = rotulo

        self.cmb_modelo.configure(values=opcoes)
        if rotulo_selecionado:
            self.cmb_modelo.set(rotulo_selecionado)
        elif opcoes:
            self.cmb_modelo.set(opcoes[0])

        self._atualizar_estado_visual()

    def _ao_selecionar_modelo(self, _valor_visivel: str):
        id_mod = self.modelo_selecionado
        PreferenciasUsuario.definir("modelo_whisper", id_mod)
        self._atualizar_estado_visual()
        if self._ao_mudar_estado_cb:
            self._ao_mudar_estado_cb()

    def _atualizar_estado_visual(self):
        if self._baixando:
            return
        id_mod = self.modelo_selecionado
        instalado = MotorWhisperfile.esta_modelo_instalado(id_mod)

        if instalado:
            self.btn_baixar.configure(
                text=I18n.t("btn_modelo_instalado"),
                state="disabled",
                fg_color=CORES["destaque_verde"],
            )
            self.lbl_status.configure(
                text=I18n.t("lbl_download_concluido").format(id_mod.upper()),
                text_color=CORES["destaque_verde"],
            )
        else:
            self.btn_baixar.configure(
                text=I18n.t("btn_baixar_modelo"),
                state="normal",
                fg_color=CORES["destaque_azul"],
            )
            self.lbl_status.configure(
                text=I18n.t("lbl_whisper_ausente"),
                text_color=CORES["texto_secundario"],
            )

    @staticmethod
    def _formatar_duracao(segundos: float) -> str:
        if segundos <= 0:
            return "--:--"
        total = int(round(segundos))
        minutos, segs = divmod(total, 60)
        horas, minutos = divmod(minutos, 60)
        if horas > 0:
            return f"{horas:02d}:{minutos:02d}:{segs:02d}"
        return f"{minutos:02d}:{segs:02d}"

    def _solicitar_analise_video(self):
        caminho = self._caminho_arquivo_padrao
        if not caminho or not os.path.isfile(caminho):
            caminho = filedialog.askopenfilename(
                parent=self.winfo_toplevel(),
                title=I18n.t("dialogo_selecionar_arquivos"),
                filetypes=[(I18n.t("tipo_video_mkv"), "*.mkv *.mp4 *.avi *.mov *.webm")],
            )
        if caminho and os.path.isfile(caminho):
            self.executar_analise(caminho)

    def executar_analise(self, caminho_arquivo: str):
        """Executa o diagnóstico acústico e de hardware em thread separada e aplica o modelo recomendado."""
        if self._analisando or self._baixando:
            return
        self._analisando = True
        self._caminho_arquivo_padrao = caminho_arquivo
        self.btn_analisar.configure(state="disabled")
        self.lbl_diagnostico.configure(
            text=I18n.t("lbl_analisando_video_whisper"),
            text_color=CORES["destaque_azul"],
        )
        self.lbl_diagnostico.pack(anchor="w", padx=12, pady=(2, 4), before=self.lbl_status)

        def _worker():
            diag = RecomendadorModeloWhisper.analisar_arquivo(caminho_arquivo)

            def _aplicar_ui():
                self._analisando = False
                if not self.winfo_exists():
                    return
                self.btn_analisar.configure(state="normal")
                self._exibir_resultado_diagnostico(caminho_arquivo, diag)

            self.after(0, _aplicar_ui)

        threading.Thread(target=_worker, daemon=True).start()

    def _exibir_resultado_diagnostico(self, caminho_arquivo: str, diag: DiagnosticoAudioWhisper):
        nome_curto = os.path.basename(caminho_arquivo)
        if len(nome_curto) > 28:
            nome_curto = nome_curto[:25] + "..."
        duracao_fmt = self._formatar_duracao(diag.duracao_segundos)
        idioma_fmt = Idiomas.formatar_origem_mkv(diag.idioma_audio)
        perfil_txt = (
            I18n.t("diag_perfil_musica")
            if diag.possui_fundo_musical
            else I18n.t("diag_perfil_voz_limpa")
        )
        cabecalho = I18n.t("diag_resumo_cabecalho").format(
            nome_curto, duracao_fmt, idioma_fmt, perfil_txt, diag.ram_livre_gb
        )
        motivo = I18n.t(diag.chave_motivo)
        self.lbl_diagnostico.configure(
            text=f"{cabecalho}\n{motivo}",
            text_color=CORES["texto_principal"],
        )

        PreferenciasUsuario.definir("modelo_whisper", diag.modelo_recomendado)
        self.atualizar_opcoes()
        if self._ao_mudar_estado_cb:
            self._ao_mudar_estado_cb()

    def iniciar_download(self, ao_concluir_cb=None):
        if self._baixando:
            return
        id_mod = self.modelo_selecionado
        self._baixando = True
        self._cancelado = False

        self.cmb_modelo.configure(state="disabled")
        self.btn_baixar.configure(state="disabled")
        self.barra_progresso.set(0)
        self.barra_progresso.pack(fill="x", padx=12, pady=(2, 4), before=self.lbl_status)

        def _progresso(baixados: int, total: int):
            frac = min(max(baixados / total, 0.0), 1.0)
            pct = int(frac * 100)
            mb_b = baixados / (1024 * 1024)
            mb_t = total / (1024 * 1024)
            texto = I18n.t("lbl_baixando_modelo").format(id_mod.upper(), pct, mb_b, mb_t)

            def _ui():
                if self.winfo_exists():
                    self.barra_progresso.set(frac)
                    self.lbl_status.configure(text=texto, text_color=CORES["destaque_azul"])

            self.after(0, _ui)

        def _worker():
            try:
                MotorWhisperfile.baixar_modelo(
                    id_mod,
                    progresso_cb=_progresso,
                    cancelado_cb=lambda: self._cancelado,
                )

                def _sucesso():
                    self._baixando = False
                    if not self.winfo_exists():
                        return
                    self.barra_progresso.pack_forget()
                    self.cmb_modelo.configure(state="normal")
                    PreferenciasUsuario.definir("modelo_whisper", id_mod)
                    self.atualizar_opcoes()
                    if self._ao_mudar_estado_cb:
                        self._ao_mudar_estado_cb()
                    if ao_concluir_cb:
                        ao_concluir_cb(True)

                self.after(0, _sucesso)
            except Exception as e:
                msg_erro = str(e)

                def _falha():
                    self._baixando = False
                    if not self.winfo_exists():
                        return
                    self.barra_progresso.pack_forget()
                    self.cmb_modelo.configure(state="normal")
                    self.btn_baixar.configure(state="normal")
                    self.lbl_status.configure(
                        text=I18n.t("lbl_download_erro").format(msg_erro[:60]),
                        text_color=CORES["destaque_vermelho"],
                    )
                    if ao_concluir_cb:
                        ao_concluir_cb(False)

                self.after(0, _falha)

        threading.Thread(target=_worker, daemon=True).start()


class ModalConfirmacaoWhisper(ctk.CTkToplevel):
    """Modal interativo exibido quando um video nao possui legenda, permitindo analisar, escolher ou baixar o modelo."""

    def __init__(self, master, nome_arquivo: str, ao_decidir_cb, caminho_arquivo: str | None = None):
        super().__init__(master)
        self._ao_decidir_cb = ao_decidir_cb
        self._caminho_arquivo = caminho_arquivo
        self._decidido = False

        self.title(I18n.t("msg_whisper_perm_titulo"))
        self.geometry("600x370")
        self.minsize(560, 340)
        self.configure(fg_color=CORES["bg_janela"])
        self.transient(master)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self._recusar)
        self.after(50, self.focus)

        self._construir_interface(nome_arquivo)
        if self._caminho_arquivo and os.path.isfile(self._caminho_arquivo):
            self.after(120, lambda: self.painel_whisper.executar_analise(self._caminho_arquivo))

    def _construir_interface(self, nome_arquivo: str):
        fonte_ui = CORES.get("fonte_ui", "Segoe UI")
        raio_card = CORES.get("raio_card", 6)

        lbl_msg = ctk.CTkLabel(
            self,
            text=I18n.t("msg_whisper_perm_corpo").format(nome_arquivo),
            font=(fonte_ui, 12),
            text_color=CORES["texto_principal"],
            justify="left",
            wraplength=550,
        )
        lbl_msg.pack(anchor="w", padx=18, pady=(16, 10))

        self.painel_whisper = PainelSeletorWhisper(
            self,
            ao_mudar_estado_cb=self._atualizar_botao_confirmar,
            caminho_arquivo_padrao=self._caminho_arquivo,
        )
        self.painel_whisper.pack(fill="x", padx=16, pady=6)

        frame_botoes = ctk.CTkFrame(self, fg_color="transparent")
        frame_botoes.pack(fill="x", side="bottom", padx=16, pady=14)

        self.btn_recusar = ctk.CTkButton(
            frame_botoes,
            text=I18n.t("btn_recusar_whisper"),
            font=(fonte_ui, 11),
            fg_color=CORES["bg_card"],
            hover_color=CORES["destaque_vermelho"],
            border_color=CORES["borda_card"],
            border_width=CORES.get("borda_largura", 1),
            text_color=CORES["texto_principal"],
            corner_radius=raio_card,
            width=170,
            height=34,
            command=self._recusar,
        )
        self.btn_recusar.pack(side="left")

        self.btn_confirmar = ctk.CTkButton(
            frame_botoes,
            text=I18n.t("btn_autorizar_whisper"),
            font=(fonte_ui, 11, "bold"),
            fg_color=CORES["destaque_verde"],
            hover_color=CORES["destaque_azul_hover"],
            text_color="#ffffff",
            corner_radius=raio_card,
            width=220,
            height=34,
            command=self._confirmar,
        )
        self.btn_confirmar.pack(side="right")
        self._atualizar_botao_confirmar()

    def _atualizar_botao_confirmar(self):
        if self.painel_whisper.esta_instalado:
            self.btn_confirmar.configure(
                text=I18n.t("btn_autorizar_whisper"),
                fg_color=CORES["destaque_verde"],
            )
        else:
            self.btn_confirmar.configure(
                text=I18n.t("btn_baixar_e_transcrever"),
                fg_color=CORES["destaque_azul"],
            )

    def _confirmar(self):
        if self.painel_whisper.esta_instalado:
            PreferenciasUsuario.definir("modelo_whisper", self.painel_whisper.modelo_selecionado)
            self._finalizar(True)
        else:
            self.btn_confirmar.configure(state="disabled")

            def _apos_download(sucesso: bool):
                if sucesso:
                    self._finalizar(True)
                elif self.winfo_exists():
                    self.btn_confirmar.configure(state="normal")

            self.painel_whisper.iniciar_download(ao_concluir_cb=_apos_download)

    def _recusar(self):
        self.painel_whisper.cancelar_download()
        self._finalizar(False)

    def _finalizar(self, autorizado: bool):
        if self._decidido:
            return
        self._decidido = True
        try:
            self.grab_release()
            self.destroy()
        except Exception:
            pass
        self._ao_decidir_cb(autorizado)
