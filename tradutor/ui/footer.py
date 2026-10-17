"""Componente de rodape com barra de progresso, acoes e gaveta retratil de logs."""

import customtkinter as ctk
from .tema import CORES
from ..i18n import I18n


class FooterView(ctk.CTkFrame):
    """Rodape contendo status, progresso, acoes principais e console retratil."""

    def __init__(self, master, on_start_cb, on_cancel_cb):
        largura_borda = CORES.get("borda_largura", 1)
        super().__init__(
            master,
            fg_color=CORES["bg_sidebar"],
            border_color=CORES["borda_card"],
            border_width=largura_borda,
            corner_radius=0
        )
        self.on_start_cb = on_start_cb
        self.on_cancel_cb = on_cancel_cb

        self._logs_visivel = False
        self._construir_widgets()

    def _construir_widgets(self):
        largura_borda = CORES.get("borda_largura", 1)
        raio_card = CORES.get("raio_card", 6)
        fonte_ui = CORES.get("fonte_ui", "Segoe UI")

        # Linha de status e porcentagem
        frame_status_linha = ctk.CTkFrame(self, fg_color="transparent")
        frame_status_linha.pack(fill="x", padx=16, pady=(10, 4))

        self.lbl_status_msg = ctk.CTkLabel(
            frame_status_linha,
            text=I18n.t("status_aguardando"),
            font=(fonte_ui, 11),
            text_color=CORES["texto_secundario"]
        )
        self.lbl_status_msg.pack(side="left")

        self.lbl_progresso_pct = ctk.CTkLabel(
            frame_status_linha,
            text="0%",
            font=(fonte_ui, 11, "bold"),
            text_color=CORES["texto_principal"]
        )
        self.lbl_progresso_pct.pack(side="right")

        self.progressbar = ctk.CTkProgressBar(
            self,
            fg_color=CORES.get("progressbar_bg", CORES["bg_card"]),
            progress_color=CORES["destaque_azul"],
            corner_radius=raio_card,
            height=6
        )
        self.progressbar.set(0)
        self.progressbar.pack(fill="x", padx=16, pady=(0, 8))

        # Linha de botoes de acao
        frame_botoes = ctk.CTkFrame(self, fg_color="transparent")
        frame_botoes.pack(fill="x", padx=16, pady=(0, 10))

        self.btn_toggle_log = ctk.CTkButton(
            frame_botoes,
            text=I18n.t("btn_console"),
            command=self.toggle_logs,
            width=130,
            height=32,
            corner_radius=raio_card,
            fg_color=CORES["bg_card"],
            hover_color=CORES["bg_card_hover"],
            border_color=CORES["borda_card"],
            border_width=largura_borda,
            text_color=CORES["texto_principal"],
            font=(fonte_ui, 11)
        )
        self.btn_toggle_log.pack(side="left")

        self.btn_run = ctk.CTkButton(
            frame_botoes,
            text=I18n.t("btn_iniciar"),
            command=self.on_start_cb,
            width=200,
            height=32,
            corner_radius=raio_card,
            fg_color=CORES["destaque_verde"],
            hover_color=CORES["destaque_verde_hover"],
            text_color=CORES.get("btn_destaque_txt", "#ffffff"),
            font=(fonte_ui, 12, "bold"),
            state="disabled"
        )
        self.btn_run.pack(side="right")

        self.btn_cancelar = ctk.CTkButton(
            frame_botoes,
            text=I18n.t("btn_cancelar"),
            command=self.on_cancel_cb,
            width=120,
            height=32,
            corner_radius=raio_card,
            fg_color=CORES["destaque_vermelho"],
            hover_color=CORES["destaque_vermelho_hover"],
            text_color="white",
            font=(fonte_ui, 11, "bold")
        )

        # Gaveta Inferior de Log (Oculta por padrao)
        self.frame_gaveta_log = ctk.CTkFrame(
            self,
            fg_color=CORES["bg_janela"],
            border_color=CORES["borda_card"],
            border_width=largura_borda,
            corner_radius=raio_card,
            height=135
        )
        self.textbox = ctk.CTkTextbox(
            self.frame_gaveta_log,
            fg_color=CORES["bg_console"],
            text_color=CORES["texto_principal"],
            corner_radius=raio_card,
            font=("Consolas", 10),
            state="disabled"
        )
        self.textbox.pack(fill="both", expand=True, padx=10, pady=6)

    def aplicar_tema(self, cores: dict):
        """Propaga o novo tema para barra de progresso, console e botoes de acao."""
        largura_borda = cores.get("borda_largura", 1)
        raio_card = cores.get("raio_card", 6)
        fonte_ui = cores.get("fonte_ui", "Segoe UI")

        self.configure(
            fg_color=cores["bg_sidebar"],
            border_color=cores["borda_card"],
            border_width=largura_borda
        )
        self.lbl_status_msg.configure(text_color=cores["texto_secundario"], font=(fonte_ui, 11))
        self.lbl_progresso_pct.configure(text_color=cores["texto_principal"], font=(fonte_ui, 11, "bold"))
        self.progressbar.configure(
            fg_color=cores.get("progressbar_bg", cores["bg_card"]),
            progress_color=cores["destaque_azul"],
            corner_radius=raio_card
        )

        self.btn_toggle_log.configure(
            fg_color=cores["bg_card"],
            hover_color=cores["bg_card_hover"],
            border_color=cores["borda_card"],
            border_width=largura_borda,
            text_color=cores["texto_principal"],
            font=(fonte_ui, 11),
            corner_radius=raio_card
        )
        self.btn_run.configure(
            fg_color=cores["destaque_verde"],
            hover_color=cores["destaque_verde_hover"],
            text_color=cores.get("btn_destaque_txt", "#ffffff"),
            font=(fonte_ui, 12, "bold"),
            corner_radius=raio_card
        )
        self.btn_cancelar.configure(
            fg_color=cores["destaque_vermelho"],
            hover_color=cores["destaque_vermelho_hover"],
            font=(fonte_ui, 11, "bold"),
            corner_radius=raio_card
        )
        self.frame_gaveta_log.configure(
            fg_color=cores["bg_janela"],
            border_color=cores["borda_card"],
            border_width=largura_borda,
            corner_radius=raio_card
        )
        self.textbox.configure(
            fg_color=cores["bg_console"],
            text_color=cores["texto_principal"],
            corner_radius=raio_card
        )

    def redefinir_textos(self):
        """Atualiza os textos traduziveis do rodape apos troca de idioma."""
        self.lbl_status_msg.configure(text=I18n.t("status_aguardando"))
        self.btn_toggle_log.configure(
            text=I18n.t("btn_console") if not self._logs_visivel else I18n.t("btn_ocultar_console")
        )
        self.btn_run.configure(text=I18n.t("btn_iniciar"))
        self.btn_cancelar.configure(text=I18n.t("btn_cancelar"))

    def toggle_logs(self):
        """Alterna a visibilidade da gaveta do console de logs."""
        if self._logs_visivel:
            self.frame_gaveta_log.pack_forget()
            self.btn_toggle_log.configure(text=I18n.t("btn_console"))
            self._logs_visivel = False
        else:
            self.frame_gaveta_log.pack(fill="x", padx=16, pady=(0, 10))
            self.btn_toggle_log.configure(text=I18n.t("btn_ocultar_console"))
            self._logs_visivel = True

    def set_status(self, msg: str):
        """Atualiza a mensagem resumida no rodape."""
        texto = str(msg).strip().split('\n')[0]
        if len(texto) > 65:
            texto = texto[:62] + "..."
        self.lbl_status_msg.configure(text=texto)

    def set_progresso(self, current: int, total: int):
        """Atualiza o valor da barra de progresso e o indicador percentual."""
        if total > 0:
            pct = current / total
            self.progressbar.set(pct)
            self.lbl_progresso_pct.configure(text=f"{int(pct * 100)}% ({current}/{total})")

    def reset_progresso(self):
        """Reseta a barra e o label para zero."""
        self.progressbar.set(0)
        self.lbl_progresso_pct.configure(text="0%")

    def escrever_log(self, texto: str):
        """Insere uma linha de mensagem no console de logs."""
        self.textbox.configure(state="normal")
        self.textbox.insert("end", str(texto) + "\n")
        self.textbox.see("end")
        self.textbox.configure(state="disabled")

    def limpar_log(self):
        """Esvazia o conteudo do console de logs."""
        self.textbox.configure(state="normal")
        self.textbox.delete("0.0", "end")
        self.textbox.configure(state="disabled")

    def configurar_modo_execucao(self):
        """Ajusta botoes e status para estado de processamento ativo."""
        self.btn_run.pack_forget()
        self.btn_cancelar.pack(side="right")
        self.btn_cancelar.configure(state="normal", text=I18n.t("btn_cancelar"))
        self.reset_progresso()
        self.limpar_log()
        self.set_status(I18n.t("status_iniciando"))

    def configurar_modo_pronto(self, habilitar_iniciar: bool):
        """Ajusta botoes para estado de espera ou prontidao."""
        self.btn_cancelar.pack_forget()
        self.btn_run.pack(side="right")
        self.btn_run.configure(state="normal" if habilitar_iniciar else "disabled")

    def configurar_modo_cancelando(self):
        """Sinaliza que o cancelamento esta sendo processado."""
        self.btn_cancelar.configure(state="disabled", text=I18n.t("status_cancelando"))
