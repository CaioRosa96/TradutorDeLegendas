"""Componentes de gerenciamento da fila de processamento e cards de arquivo."""

import os
import customtkinter as ctk
from .tema import CORES


class CardArquivo(ctk.CTkFrame):
    """Card individual de representacao de um arquivo na fila de traducao."""

    def __init__(self, master, caminho_arquivo: str, destino_lang: str, on_delete_cb):
        super().__init__(
            master,
            fg_color=CORES["bg_card"],
            border_color=CORES["borda_card"],
            border_width=1,
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
        cor_badge = CORES["destaque_azul"] if ext == "MKV" else "#8b5cf6"

        badge_ext = ctk.CTkLabel(
            self,
            text=ext,
            font=("Segoe UI", 10, "bold"),
            fg_color=cor_badge,
            text_color="white",
            corner_radius=4,
            width=38,
            height=22
        )
        badge_ext.pack(side="left", padx=(10, 8), pady=12)

        texto_nome = nome_base if len(nome_base) <= 45 else nome_base[:42] + "..."
        lbl_nome = ctk.CTkLabel(
            self,
            text=texto_nome,
            font=("Segoe UI", 11, "bold"),
            text_color=CORES["texto_principal"]
        )
        lbl_nome.pack(side="left", padx=4, pady=12)

        btn_del = ctk.CTkButton(
            self,
            text="✕",
            command=lambda: self.on_delete_cb(self.caminho_arquivo),
            width=24,
            height=24,
            fg_color="transparent",
            hover_color=CORES["destaque_vermelho"],
            text_color=CORES["texto_secundario"]
        )
        btn_del.pack(side="right", padx=(8, 10), pady=12)

        self.badge_fluxo = ctk.CTkLabel(
            self,
            text=f"→ {destino_lang.upper()}",
            font=("Segoe UI", 10),
            fg_color="#1a1b26",
            text_color=CORES["destaque_verde"],
            corner_radius=4,
            width=48,
            height=20
        )
        self.badge_fluxo.pack(side="right", padx=6, pady=12)

    def atualizar_destino(self, novo_destino: str):
        """Atualiza o texto da pill de fluxo de idioma do card."""
        self.badge_fluxo.configure(text=f"→ {novo_destino.upper()}")


class PainelFilaView(ctk.CTkFrame):
    """Painel principal da fila com dropzone e lista de cards rolavel."""

    def __init__(self, master, on_add_cb, on_clear_cb, on_remove_item_cb):
        super().__init__(master, fg_color="transparent")
        self.on_add_cb = on_add_cb
        self.on_clear_cb = on_clear_cb
        self.on_remove_item_cb = on_remove_item_cb

        self._cards_instanciados = []
        self._construir_widgets()

    def _construir_widgets(self):
        # Barra superior com titulo e botoes de controle da fila
        frame_barra = ctk.CTkFrame(self, fg_color="transparent")
        frame_barra.pack(fill="x", pady=(0, 8))

        self.lbl_titulo = ctk.CTkLabel(
            frame_barra,
            text="Fila de Processamento (0 arquivos)",
            font=("Segoe UI", 14, "bold"),
            text_color=CORES["texto_principal"]
        )
        self.lbl_titulo.pack(side="left")

        self.btn_limpar = ctk.CTkButton(
            frame_barra,
            text="Limpar",
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
            text="+ Adicionar Arquivos",
            command=self.on_add_cb,
            width=145,
            height=28,
            fg_color=CORES["destaque_azul"],
            hover_color=CORES["destaque_azul_hover"],
            font=("Segoe UI", 12, "bold")
        )
        self.btn_add.pack(side="right")

        # Dropzone para estado vazio
        self.frame_dropzone = ctk.CTkFrame(
            self,
            fg_color=CORES["bg_sidebar"],
            border_color=CORES["borda_card"],
            border_width=1,
            corner_radius=8
        )
        self.frame_dropzone.pack(fill="both", expand=True)

        lbl_icone = ctk.CTkLabel(
            self.frame_dropzone,
            text="[ ↓ ]",
            font=("Consolas", 32, "bold"),
            text_color=CORES["destaque_azul"]
        )
        lbl_icone.pack(pady=(70, 6))

        lbl_texto = ctk.CTkLabel(
            self.frame_dropzone,
            text="Arraste e solte videos MKV ou legendas SRT/ASS/TXT aqui",
            font=("Segoe UI", 13, "bold"),
            text_color=CORES["texto_principal"]
        )
        lbl_texto.pack(pady=2)

        lbl_sub = ctk.CTkLabel(
            self.frame_dropzone,
            text="Ou utilize o botao '+ Adicionar Arquivos' acima",
            font=("Segoe UI", 11),
            text_color=CORES["texto_secundario"]
        )
        lbl_sub.pack(pady=2)

        # Container scrollable para os cards quando houver arquivos
        self.scroll_cards = ctk.CTkScrollableFrame(self, fg_color="transparent", corner_radius=0)

    def renderizar_fila(self, arquivos: list, destino_lang: str):
        """Renderiza ou atualiza os cards de arquivos na fila."""
        for card in self._cards_instanciados:
            card.destroy()
        self._cards_instanciados.clear()

        total = len(arquivos)
        self.lbl_titulo.configure(
            text=f"Fila de Processamento ({total} arquivo{'s' if total != 1 else ''})"
        )

        if total == 0:
            self.scroll_cards.pack_forget()
            self.frame_dropzone.pack(fill="both", expand=True)
            return

        self.frame_dropzone.pack_forget()
        self.scroll_cards.pack(fill="both", expand=True)

        for arq in arquivos:
            card = CardArquivo(self.scroll_cards, arq, destino_lang, self.on_remove_item_cb)
            card.pack(fill="x", pady=4, padx=2)
            self._cards_instanciados.append(card)

    def atualizar_destinos(self, novo_destino: str):
        """Atualiza a indicacao de idioma de destino em todos os cards ativos."""
        for card in self._cards_instanciados:
            card.atualizar_destino(novo_destino)

    def set_interativo(self, habilitado: bool):
        """Habilita ou desabilita os botoes de manipulacao da fila."""
        estado = "normal" if habilitado else "disabled"
        self.btn_add.configure(state=estado)
        self.btn_limpar.configure(state=estado)
