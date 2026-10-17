"""Componente de rodape com barra de progresso, acoes e gaveta retratil de logs."""

import customtkinter as ctk
from .tema import CORES


class FooterView(ctk.CTkFrame):
    """Rodape contendo status, progresso, acoes principais e console retratil."""

    def __init__(self, master, on_start_cb, on_cancel_cb):
        super().__init__(master, fg_color=CORES["bg_sidebar"], corner_radius=0)
        self.on_start_cb = on_start_cb
        self.on_cancel_cb = on_cancel_cb

        self._logs_visivel = False
        self._construir_widgets()

    def _construir_widgets(self):
        # Linha de status e porcentagem
        frame_status_linha = ctk.CTkFrame(self, fg_color="transparent")
        frame_status_linha.pack(fill="x", padx=16, pady=(10, 4))

        self.lbl_status_msg = ctk.CTkLabel(
            frame_status_linha,
            text="Pronto para processar",
            font=("Segoe UI", 11),
            text_color=CORES["texto_secundario"]
        )
        self.lbl_status_msg.pack(side="left")

        self.lbl_progresso_pct = ctk.CTkLabel(
            frame_status_linha,
            text="0%",
            font=("Segoe UI", 11, "bold"),
            text_color=CORES["texto_principal"]
        )
        self.lbl_progresso_pct.pack(side="right")

        self.progressbar = ctk.CTkProgressBar(
            self,
            fg_color=CORES["bg_card"],
            progress_color=CORES["destaque_azul"],
            height=6
        )
        self.progressbar.set(0)
        self.progressbar.pack(fill="x", padx=16, pady=(0, 8))

        # Linha de botoes de acao
        frame_botoes = ctk.CTkFrame(self, fg_color="transparent")
        frame_botoes.pack(fill="x", padx=16, pady=(0, 10))

        self.btn_toggle_log = ctk.CTkButton(
            frame_botoes,
            text="▼ Console de Logs",
            command=self.toggle_logs,
            width=130,
            height=32,
            fg_color=CORES["bg_card"],
            hover_color=CORES["bg_card_hover"],
            font=("Segoe UI", 11)
        )
        self.btn_toggle_log.pack(side="left")

        self.btn_run = ctk.CTkButton(
            frame_botoes,
            text="INICIAR TRADUCAO",
            command=self.on_start_cb,
            width=200,
            height=32,
            fg_color=CORES["destaque_verde"],
            hover_color=CORES["destaque_verde_hover"],
            font=("Segoe UI", 12, "bold"),
            state="disabled"
        )
        self.btn_run.pack(side="right")

        self.btn_cancelar = ctk.CTkButton(
            frame_botoes,
            text="✖ Cancelar",
            command=self.on_cancel_cb,
            width=120,
            height=32,
            fg_color=CORES["destaque_vermelho"],
            hover_color=CORES["destaque_vermelho_hover"],
            font=("Segoe UI", 11, "bold")
        )

        # Gaveta Inferior de Log (Oculta por padrao)
        self.frame_gaveta_log = ctk.CTkFrame(self, fg_color=CORES["bg_janela"], height=135)
        self.textbox = ctk.CTkTextbox(
            self.frame_gaveta_log,
            fg_color=CORES["bg_console"],
            text_color=CORES["texto_secundario"],
            font=("Consolas", 10),
            state="disabled"
        )
        self.textbox.pack(fill="both", expand=True, padx=10, pady=6)

    def toggle_logs(self):
        """Alterna a visibilidade da gaveta do console de logs."""
        if self._logs_visivel:
            self.frame_gaveta_log.pack_forget()
            self.btn_toggle_log.configure(text="▼ Console de Logs")
            self._logs_visivel = False
        else:
            self.frame_gaveta_log.pack(fill="x", padx=16, pady=(0, 10))
            self.btn_toggle_log.configure(text="▲ Ocultar Logs")
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
        self.btn_cancelar.configure(state="normal", text="✖ Cancelar")
        self.reset_progresso()
        self.limpar_log()
        self.set_status("Iniciando pipeline assincrono...")

    def configurar_modo_pronto(self, habilitar_iniciar: bool):
        """Ajusta botoes para estado de espera ou prontidao."""
        self.btn_cancelar.pack_forget()
        self.btn_run.pack(side="right")
        self.btn_run.configure(state="normal" if habilitar_iniciar else "disabled")

    def configurar_modo_cancelando(self):
        """Sinaliza que o cancelamento esta sendo processado."""
        self.btn_cancelar.configure(state="disabled", text="Cancelando...")
