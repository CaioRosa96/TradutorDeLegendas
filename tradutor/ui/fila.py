"""Componentes de gerenciamento da fila de processamento e cards de arquivo."""

import os
import customtkinter as ctk
from .tema import CORES
from ..i18n import I18n


class CardArquivo(ctk.CTkFrame):
    """Card individual de representacao de um arquivo na fila de traducao."""

    def __init__(self, master, caminho_arquivo: str, destino_lang: str, on_delete_cb):
        largura_borda = CORES.get("borda_largura", 1)
        super().__init__(
            master,
            fg_color=CORES["bg_card"],
            border_color=CORES["borda_card"],
            border_width=largura_borda,
            corner_radius=6,
            height=48
        )
        self.pack_propagate(False)
        self.caminho_arquivo = caminho_arquivo
        self.on_delete_cb = on_delete_cb

        self._construir_widgets(caminho_arquivo, destino_lang)

    def _construir_widgets(self, caminho_arquivo: str, destino_lang: str):
        nome_base = os.path.basename(caminho_arquivo)
        ext = nome_base.rsplit('.', 1)[-1].upper() if '.' in nome_base else "RAW"

        cor_bg_badge = CORES["badge_ext_mkv_bg"] if ext == "MKV" else CORES["badge_ext_outros_bg"]
        cor_txt_badge = CORES["badge_ext_mkv_txt"] if ext == "MKV" else CORES["badge_ext_outros_txt"]

        self.badge_ext = ctk.CTkLabel(
            self,
            text=ext,
            font=("Segoe UI", 10, "bold"),
            fg_color=cor_bg_badge,
            text_color=cor_txt_badge,
            corner_radius=4,
            width=38,
            height=22
        )
        self.badge_ext.pack(side="left", padx=(10, 8), pady=12)

        texto_nome = nome_base if len(nome_base) <= 45 else nome_base[:42] + "..."
        self.lbl_nome = ctk.CTkLabel(
            self,
            text=texto_nome,
            font=("Segoe UI", 11, "bold"),
            text_color=CORES["texto_principal"]
        )
        self.lbl_nome.pack(side="left", padx=4, pady=12)

        self.btn_del = ctk.CTkButton(
            self,
            text="✕",
            command=lambda: self.on_delete_cb(self.caminho_arquivo),
            width=24,
            height=24,
            fg_color="transparent",
            hover_color=CORES["destaque_vermelho"],
            text_color=CORES["texto_secundario"]
        )
        self.btn_del.pack(side="right", padx=(8, 10), pady=12)

        self.badge_fluxo = ctk.CTkLabel(
            self,
            text=f"→ {destino_lang.upper()}",
            font=("Segoe UI", 10, "bold"),
            fg_color=CORES["badge_fluxo_bg"],
            text_color=CORES["badge_fluxo_txt"],
            corner_radius=4,
            width=48,
            height=20
        )
        self.badge_fluxo.pack(side="right", padx=6, pady=12)

    def atualizar_destino(self, novo_destino: str):
        """Atualiza o texto da pill de fluxo de idioma do card."""
        self.badge_fluxo.configure(text=f"→ {novo_destino.upper()}")

    def aplicar_tema(self, cores: dict):
        """Atualiza visual do card de acordo com o tema ativo sem elementos residuais."""
        largura_borda = cores.get("borda_largura", 1)
        self.configure(
            fg_color=cores["bg_card"],
            border_color=cores["borda_card"],
            border_width=largura_borda
        )
        self.lbl_nome.configure(text_color=cores["texto_principal"])
        self.btn_del.configure(text_color=cores["texto_secundario"], hover_color=cores["destaque_vermelho"])

        ext = self.badge_ext.cget("text")
        if ext == "MKV":
            self.badge_ext.configure(
                fg_color=cores["badge_ext_mkv_bg"],
                text_color=cores["badge_ext_mkv_txt"]
            )
        else:
            self.badge_ext.configure(
                fg_color=cores["badge_ext_outros_bg"],
                text_color=cores["badge_ext_outros_txt"]
            )

        self.badge_fluxo.configure(
            fg_color=cores["badge_fluxo_bg"],
            text_color=cores["badge_fluxo_txt"]
        )


class PainelFilaView(ctk.CTkFrame):
    """Painel principal da fila com dropzone e lista de cards rolavel."""

    def __init__(self, master, on_add_cb, on_clear_cb, on_remove_item_cb):
        super().__init__(master, fg_color="transparent")
        self.on_add_cb = on_add_cb
        self.on_clear_cb = on_clear_cb
        self.on_remove_item_cb = on_remove_item_cb

        self._cards_instanciados = []
        self._total_atual = 0
        self._construir_widgets()

    def _construir_widgets(self):
        largura_borda = CORES.get("borda_largura", 1)

        frame_barra = ctk.CTkFrame(self, fg_color="transparent")
        frame_barra.pack(fill="x", pady=(0, 8))

        self.lbl_titulo = ctk.CTkLabel(
            frame_barra,
            text=f"{I18n.t('fila_titulo')} (0)",
            font=("Segoe UI", 14, "bold"),
            text_color=CORES["texto_principal"]
        )
        self.lbl_titulo.pack(side="left")

        self.btn_limpar = ctk.CTkButton(
            frame_barra,
            text=I18n.t("btn_limpar"),
            command=self.on_clear_cb,
            width=65,
            height=28,
            fg_color="transparent",
            text_color=CORES["texto_secundario"],
            hover_color=CORES["bg_card"]
        )
        self.btn_limpar.pack(side="right", padx=(6, 0))

        self.btn_add = ctk.CTkButton(
            frame_barra,
            text=I18n.t("btn_add"),
            command=self.on_add_cb,
            width=145,
            height=28,
            fg_color=CORES["destaque_azul"],
            hover_color=CORES["destaque_azul_hover"],
            text_color="#000000" if CORES.get("nome") == "MS-DOS Retrô" else "white",
            font=("Segoe UI", 12, "bold")
        )
        self.btn_add.pack(side="right")

        # Dropzone para estado vazio
        self.frame_dropzone = ctk.CTkFrame(
            self,
            fg_color=CORES["bg_sidebar"],
            border_color=CORES["borda_card"],
            border_width=largura_borda,
            corner_radius=8
        )
        self.frame_dropzone.pack(fill="both", expand=True)

        self.lbl_drop_icone = ctk.CTkLabel(
            self.frame_dropzone,
            text="[ ↓ ]",
            font=("Consolas", 32, "bold"),
            text_color=CORES["destaque_azul"]
        )
        self.lbl_drop_icone.pack(pady=(70, 6))

        self.lbl_drop_texto = ctk.CTkLabel(
            self.frame_dropzone,
            text=I18n.t("drop_texto"),
            font=("Segoe UI", 13, "bold"),
            text_color=CORES["texto_principal"]
        )
        self.lbl_drop_texto.pack(pady=2)

        self.lbl_drop_sub = ctk.CTkLabel(
            self.frame_dropzone,
            text=I18n.t("drop_sub"),
            font=("Segoe UI", 11),
            text_color=CORES["texto_secundario"]
        )
        self.lbl_drop_sub.pack(pady=2)

        # Container scrollable para os cards quando houver arquivos
        self.scroll_cards = ctk.CTkScrollableFrame(self, fg_color=CORES["bg_janela"], corner_radius=6)

    def renderizar_fila(self, arquivos: list, destino_lang: str):
        """Renderiza ou atualiza os cards de arquivos na fila."""
        for card in self._cards_instanciados:
            card.destroy()
        self._cards_instanciados.clear()

        self._total_atual = len(arquivos)
        self._atualizar_titulo_fila()

        if self._total_atual == 0:
            self.scroll_cards.pack_forget()
            self.frame_dropzone.pack(fill="both", expand=True)
            return

        self.frame_dropzone.pack_forget()
        self.scroll_cards.pack(fill="both", expand=True)

        for arq in arquivos:
            card = CardArquivo(self.scroll_cards, arq, destino_lang, self.on_remove_item_cb)
            card.pack(fill="x", pady=4, padx=2)
            self._cards_instanciados.append(card)

    def _atualizar_titulo_fila(self):
        termo_arq = I18n.t("arquivo_singular") if self._total_atual == 1 else I18n.t("arquivo_plural")
        sufixo = f"({self._total_atual} {termo_arq})"
        self.lbl_titulo.configure(text=f"{I18n.t('fila_titulo')} {sufixo}")

    def redefinir_textos(self, total_arquivos: int = None):
        """Atualiza todos os textos da fila apos troca de idioma."""
        if total_arquivos is not None:
            self._total_atual = total_arquivos
        self._atualizar_titulo_fila()
        self.btn_limpar.configure(text=I18n.t("btn_limpar"))
        self.btn_add.configure(text=I18n.t("btn_add"))
        self.lbl_drop_texto.configure(text=I18n.t("drop_texto"))
        self.lbl_drop_sub.configure(text=I18n.t("drop_sub"))

    def aplicar_tema(self, cores: dict):
        """Propaga as novas cores do tema para dropzone, botoes e cards da fila."""
        largura_borda = cores.get("borda_largura", 1)

        self.lbl_titulo.configure(text_color=cores["texto_principal"])
        self.btn_limpar.configure(text_color=cores["texto_secundario"], hover_color=cores["bg_card"])
        self.btn_add.configure(
            fg_color=cores["destaque_azul"],
            hover_color=cores["destaque_azul_hover"],
            text_color="#000000" if cores.get("nome") == "MS-DOS Retrô" else "white"
        )
        self.frame_dropzone.configure(
            fg_color=cores["bg_sidebar"],
            border_color=cores["borda_card"],
            border_width=largura_borda
        )
        self.lbl_drop_icone.configure(text_color=cores["destaque_azul"])
        self.lbl_drop_texto.configure(text_color=cores["texto_principal"])
        self.lbl_drop_sub.configure(text_color=cores["texto_secundario"])
        self.scroll_cards.configure(fg_color=cores["bg_janela"])

        for card in self._cards_instanciados:
            card.aplicar_tema(cores)

    def atualizar_destinos(self, novo_destino: str):
        """Atualiza a indicacao de idioma de destino em todos os cards ativos."""
        for card in self._cards_instanciados:
            card.atualizar_destino(novo_destino)

    def set_interativo(self, habilitado: bool):
        """Habilita ou desabilita os botoes de manipulacao da fila."""
        estado = "normal" if habilitado else "disabled"
        self.btn_add.configure(state=estado)
        self.btn_limpar.configure(state=estado)
