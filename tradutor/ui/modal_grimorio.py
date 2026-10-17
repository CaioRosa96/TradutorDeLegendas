"""Janela modal de inspecao e navegacao do Grimorio de Glossarios (Anti-Alucinacao)."""

import os
import subprocess
import customtkinter as ctk

from ..config import GerenciadorConfig
from ..i18n import I18n
from .tema import CORES


class ModalGrimorio(ctk.CTkToplevel):
    """Modal de consulta e gerenciamento visual dos glossarios e entidades de anime."""

    def __init__(self, master):
        super().__init__(master)
        self.title(I18n.t("modal_grimorio_titulo"))
        self.geometry("740x520")
        self.minsize(680, 460)
        self.configure(fg_color=CORES["bg_janela"])
        self.transient(master)
        self.after(50, self.focus)

        self._glossarios = {}
        self._anime_selecionado = None
        self._carregar_dados_glossarios()
        self._construir_interface()

    def _carregar_dados_glossarios(self):
        """Carrega e indexa os arquivos de termos de animes e termos globais."""
        self._glossarios.clear()

        # 1. Glossario Global
        if os.path.exists(GerenciadorConfig.ARQUIVO_GLOSSARIO_PADRAO):
            termos = self._ler_termos_arquivo(GerenciadorConfig.ARQUIVO_GLOSSARIO_PADRAO)
            rotulo_global = I18n.t("grimorio_glossario_global")
            self._glossarios[rotulo_global] = {
                "caminho": GerenciadorConfig.ARQUIVO_GLOSSARIO_PADRAO,
                "termos": termos,
                "tipo": "global"
            }

        # 2. Glossarios individuais por anime
        pasta = GerenciadorConfig.DIRETORIO_GLOSSARIOS
        if os.path.exists(pasta):
            for nome in sorted(os.listdir(pasta)):
                if nome.lower().endswith(".txt"):
                    caminho = os.path.join(pasta, nome)
                    nome_anime = os.path.splitext(nome)[0]
                    termos = self._ler_termos_arquivo(caminho)
                    self._glossarios[nome_anime] = {
                        "caminho": caminho,
                        "termos": termos,
                        "tipo": "anime"
                    }

    def _ler_termos_arquivo(self, caminho: str) -> list:
        try:
            with open(caminho, "r", encoding="utf-8") as f:
                return [linha.strip() for linha in f if linha.strip() and not linha.startswith("#")]
        except Exception:
            return []

    def _construir_interface(self):
        # 1. Topo: Titulo, Busca e Botao de Abrir Pasta
        frame_topo = ctk.CTkFrame(self, fg_color=CORES["bg_sidebar"], height=52, corner_radius=0)
        frame_topo.pack(side="top", fill="x")

        lbl_tit = ctk.CTkLabel(
            frame_topo,
            text=I18n.t("grimorio_titulo_topo"),
            font=("Segoe UI", 13, "bold"),
            text_color=CORES["texto_principal"]
        )
        lbl_tit.pack(side="left", padx=16, pady=10)

        btn_pasta = ctk.CTkButton(
            frame_topo,
            text=I18n.t("btn_abrir_explorer"),
            font=("Segoe UI", 11),
            fg_color=CORES["destaque_azul"],
            hover_color=CORES["destaque_azul_hover"],
            height=28,
            command=self._abrir_pasta_explorer
        )
        btn_pasta.pack(side="right", padx=16, pady=10)

        # 2. Container Central
        conteudo = ctk.CTkFrame(self, fg_color="transparent")
        conteudo.pack(side="top", fill="both", expand=True, padx=14, pady=12)

        # Coluna Esquerda: Busca + Lista de Animes
        col_esq = ctk.CTkFrame(conteudo, fg_color=CORES["bg_sidebar"], width=260, corner_radius=6)
        col_esq.pack(side="left", fill="y", padx=(0, 10))
        col_esq.pack_propagate(False)

        self.txt_busca = ctk.CTkEntry(
            col_esq,
            placeholder_text=I18n.t("grimorio_busca_placeholder"),
            font=("Segoe UI", 11),
            height=30
        )
        self.txt_busca.pack(fill="x", padx=10, pady=(10, 8))
        self.txt_busca.bind("<KeyRelease>", lambda e: self._filtrar_lista())

        self.scroll_animes = ctk.CTkScrollableFrame(col_esq, fg_color="transparent")
        self.scroll_animes.pack(fill="both", expand=True, padx=6, pady=(0, 8))

        # Coluna Direita: Termos do Anime Selecionado
        self.col_dir = ctk.CTkFrame(conteudo, fg_color=CORES["bg_sidebar"], corner_radius=6)
        self.col_dir.pack(side="left", fill="both", expand=True)

        self.lbl_anime_atual = ctk.CTkLabel(
            self.col_dir,
            text=I18n.t("grimorio_selecione_anime"),
            font=("Segoe UI", 12, "bold"),
            text_color=CORES["texto_secundario"]
        )
        self.lbl_anime_atual.pack(anchor="w", padx=14, pady=(12, 4))

        self.lbl_badge_termos = ctk.CTkLabel(
            self.col_dir,
            text="",
            font=("Segoe UI", 11),
            text_color=CORES["destaque_verde"]
        )
        self.lbl_badge_termos.pack(anchor="w", padx=14, pady=(0, 6))

        self.txt_termos = ctk.CTkTextbox(
            self.col_dir,
            font=("Consolas", 11),
            fg_color=CORES["bg_console"],
            text_color=CORES["texto_principal"],
            wrap="none"
        )
        self.txt_termos.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        self._renderizar_botoes_animes(list(self._glossarios.keys()))
        if self._glossarios:
            primeiro = list(self._glossarios.keys())[0]
            self._selecionar_anime(primeiro)

    def _renderizar_botoes_animes(self, lista_nomes: list):
        for widget in self.scroll_animes.winfo_children():
            widget.destroy()

        for nome in lista_nomes:
            dados = self._glossarios[nome]
            qtd = len(dados["termos"])
            btn = ctk.CTkButton(
                self.scroll_animes,
                text=f"{nome} ({qtd})",
                anchor="w",
                font=("Segoe UI", 11),
                fg_color=CORES["bg_card"],
                hover_color=CORES["bg_card_hover"],
                text_color=CORES["texto_principal"],
                height=32,
                command=lambda n=nome: self._selecionar_anime(n)
            )
            btn.pack(fill="x", pady=2)

    def _filtrar_lista(self):
        termo = self.txt_busca.get().strip().lower()
        filtrados = [n for n in self._glossarios if termo in n.lower()]
        self._renderizar_botoes_animes(filtrados)

    def _selecionar_anime(self, nome: str):
        self._anime_selecionado = nome
        dados = self._glossarios.get(nome, {})
        termos = dados.get("termos", [])

        rotulo_anime = I18n.t("grimorio_anime_rotulo").format(nome)
        self.lbl_anime_atual.configure(
            text=rotulo_anime,
            text_color=CORES["texto_principal"]
        )
        self.lbl_badge_termos.configure(
            text=I18n.t("grimorio_badge_termos").format(len(termos))
        )

        self.txt_termos.configure(state="normal")
        self.txt_termos.delete("1.0", "end")
        self.txt_termos.insert("end", "\n".join(termos))
        self.txt_termos.configure(state="disabled")

    def _abrir_pasta_explorer(self):
        pasta = GerenciadorConfig.DIRETORIO_GLOSSARIOS
        if os.path.exists(pasta):
            try:
                os.startfile(pasta)
            except Exception:
                subprocess.Popen(["explorer", pasta])
