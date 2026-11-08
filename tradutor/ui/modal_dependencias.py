"""Janela modal de escolha para instalacao sob demanda ou selecao de pasta do MKVToolNix (GPLv2)."""

import threading
import webbrowser
from tkinter import filedialog
import customtkinter as ctk

from ..i18n import I18n
from ..instalador_dependencias import InstaladorDependencias
from .tema import CORES


class ModalDependencias(ctk.CTkToplevel):
    """Modal exibido quando mkvmerge/mkvextract nao sao encontrados nas pastas local ou padrao."""

    def __init__(self, master, ao_decidir_cb=None):
        super().__init__(master)
        self.title(I18n.t("modal_dep_titulo"))
        self.geometry("580x390")
        self.minsize(540, 360)
        self.configure(fg_color=CORES["bg_janela"])
        self.transient(master)
        self.grab_set()
        self.after(50, self.focus)

        self._ao_decidir_cb = ao_decidir_cb
        self._baixando = False
        self._cancelado = False
        self._decidido = False

        self._construir_interface()
        self.protocol("WM_DELETE_WINDOW", self._ao_cancelar)

    def _construir_interface(self):
        fonte_ui = CORES.get("fonte_ui", "Segoe UI")
        largura_borda = CORES.get("borda_largura", 1)
        raio_card = CORES.get("raio_card", 6)

        self.lbl_subtitulo = ctk.CTkLabel(
            self,
            text=I18n.t("modal_dep_subtitulo"),
            font=(fonte_ui, 12, "bold"),
            text_color=CORES["destaque_azul"],
        )
        self.lbl_subtitulo.pack(anchor="w", padx=20, pady=(16, 6))

        card_corpo = ctk.CTkFrame(
            self,
            fg_color=CORES["bg_card"],
            border_color=CORES["borda_card"],
            border_width=largura_borda,
            corner_radius=raio_card,
        )
        card_corpo.pack(fill="x", padx=20, pady=(0, 12))

        self.lbl_corpo = ctk.CTkLabel(
            card_corpo,
            text=I18n.t("modal_dep_corpo"),
            font=(fonte_ui, 11),
            text_color=CORES["texto_principal"],
            justify="left",
            wraplength=510,
        )
        self.lbl_corpo.pack(anchor="w", padx=14, pady=12)

        self.barra_progresso = ctk.CTkProgressBar(
            self,
            height=8,
            corner_radius=4,
            fg_color=CORES.get("progressbar_bg", CORES["bg_sidebar"]),
            progress_color=CORES["destaque_azul"],
        )
        self.barra_progresso.set(0)

        self.lbl_status = ctk.CTkLabel(
            self,
            text="",
            font=(fonte_ui, 11, "bold"),
            text_color=CORES["texto_secundario"],
            wraplength=520,
        )
        self.lbl_status.pack(anchor="w", padx=20, pady=(0, 8))

        frame_botoes = ctk.CTkFrame(self, fg_color="transparent")
        frame_botoes.pack(fill="x", padx=20, pady=(4, 14))

        self.btn_baixar = ctk.CTkButton(
            frame_botoes,
            text=I18n.t("btn_dep_baixar"),
            font=(fonte_ui, 12, "bold"),
            fg_color=CORES["destaque_verde"],
            hover_color=CORES["destaque_verde_hover"],
            text_color=CORES.get("btn_iniciar_txt", "#ffffff"),
            corner_radius=raio_card,
            height=36,
            command=self._iniciar_download_automatico,
        )
        self.btn_baixar.pack(fill="x", pady=(0, 8))

        self.btn_outra_pasta = ctk.CTkButton(
            frame_botoes,
            text=I18n.t("btn_dep_outra_pasta"),
            font=(fonte_ui, 11, "bold"),
            fg_color=CORES["destaque_azul"],
            hover_color=CORES["destaque_azul_hover"],
            text_color=CORES.get("btn_destaque_txt", "#ffffff"),
            corner_radius=raio_card,
            height=34,
            command=self._selecionar_outra_pasta,
        )
        self.btn_outra_pasta.pack(fill="x", pady=(0, 8))

        self.btn_cancelar = ctk.CTkButton(
            frame_botoes,
            text=I18n.t("btn_dep_cancelar"),
            font=(fonte_ui, 11),
            fg_color=CORES["bg_card"],
            hover_color=CORES["bg_card_hover"],
            border_color=CORES["borda_card"],
            border_width=largura_borda,
            text_color=CORES["texto_secundario"],
            corner_radius=raio_card,
            height=30,
            command=self._ao_cancelar,
        )
        self.btn_cancelar.pack(fill="x")

    def _selecionar_outra_pasta(self):
        if self._baixando:
            return
        pasta = filedialog.askdirectory(parent=self, title=I18n.t("btn_dep_outra_pasta"))
        if not pasta:
            return

        sucesso, caminho_validado = InstaladorDependencias.definir_pasta_existente(pasta)
        if sucesso:
            self.lbl_status.configure(
                text=I18n.t("lbl_dep_sucesso").format(caminho_validado),
                text_color=CORES["destaque_verde"],
            )
            self._finalizar(True)
        else:
            self.lbl_status.configure(
                text=I18n.t("lbl_dep_pasta_invalida"),
                text_color=CORES["destaque_vermelho"],
            )

    def _iniciar_download_automatico(self):
        if self._baixando:
            return
        self._baixando = True
        self._cancelado = False
        self.btn_baixar.configure(state="disabled")
        self.btn_outra_pasta.configure(state="disabled")
        self.barra_progresso.pack(fill="x", padx=20, pady=(0, 6), before=self.lbl_status)
        self.barra_progresso.set(0)
        self.lbl_status.configure(
            text=I18n.t("lbl_dep_instalando_winget"),
            text_color=CORES["destaque_azul"],
        )

        def _progresso(baixados: int, total: int):
            fracao = min(1.0, baixados / max(1, total))
            pct = int(fracao * 100)
            mb_b = baixados / (1024 * 1024)
            mb_t = total / (1024 * 1024)
            try:
                self.after(
                    0,
                    lambda: (
                        self.barra_progresso.set(fracao),
                        self.lbl_status.configure(
                            text=I18n.t("lbl_dep_baixando").format(pct, mb_b, mb_t)
                        ),
                    ),
                )
            except Exception:
                pass

        def _worker():
            try:
                caminho_instalado = InstaladorDependencias.baixar_dependencias(
                    progresso_cb=_progresso,
                    cancelado_cb=lambda: self._cancelado,
                )
                self.after(0, lambda: self._ao_concluir_download(True, caminho_instalado))
            except InterruptedError:
                pass
            except Exception:
                self.after(0, lambda: self._ao_concluir_download(False, ""))

        threading.Thread(target=_worker, daemon=True).start()

    def _ao_concluir_download(self, sucesso: bool, caminho: str):
        self._baixando = False
        if not self.winfo_exists():
            return
        if sucesso:
            self.lbl_status.configure(
                text=I18n.t("lbl_dep_sucesso").format(caminho),
                text_color=CORES["destaque_verde"],
            )
            self._finalizar(True)
        else:
            self.btn_baixar.configure(state="normal")
            self.btn_outra_pasta.configure(state="normal")
            self.lbl_status.configure(
                text=I18n.t("lbl_dep_erro_download"),
                text_color=CORES["destaque_vermelho"],
            )
            try:
                webbrowser.open_new_tab(InstaladorDependencias.URL_PAGINA_OFICIAL_MKVTOOLNIX)
            except Exception:
                pass

    def _ao_cancelar(self):
        self._cancelado = True
        self._finalizar(False)

    def _finalizar(self, resolvido: bool):
        if self._decidido:
            return
        self._decidido = True
        try:
            self.grab_release()
            self.destroy()
        except Exception:
            pass
        if self._ao_decidir_cb:
            self._ao_decidir_cb(resolvido)

