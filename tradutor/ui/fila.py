"""Componentes de gerenciamento da fila em grade tabular densa (estilo utilitario desktop)."""

import os
import customtkinter as ctk
from .tema import CORES
from ..idiomas import Idiomas
from ..i18n import I18n


class CardArquivo(ctk.CTkFrame):
    """Linha tabular compacta representando um arquivo na fila de processamento."""

    def __init__(self, master, caminho_arquivo: str, destino_lang: str, on_delete_cb, on_inspect_ia_cb=None):
        largura_borda = CORES.get("borda_largura", 1)
        raio_card = CORES.get("raio_card", 2)
        super().__init__(
            master,
            fg_color=CORES["bg_card"],
            border_color=CORES["borda_card"],
            border_width=largura_borda,
            corner_radius=raio_card,
            height=30,
        )
        self.pack_propagate(False)
        self.caminho_arquivo = caminho_arquivo
        self._destino_lang = destino_lang
        self.on_delete_cb = on_delete_cb
        self.on_inspect_ia_cb = on_inspect_ia_cb
        self._requer_ia = False
        self._modelo_ia = "small"
        self._confirmado_ia = False

        self._construir_widgets(caminho_arquivo, destino_lang)

    def _construir_widgets(self, caminho_arquivo: str, destino_lang: str):
        fonte_ui = CORES.get("fonte_ui", "Segoe UI")
        raio_card = CORES.get("raio_card", 2)
        nome_base = os.path.basename(caminho_arquivo)
        ext = nome_base.rsplit(".", 1)[-1].upper() if "." in nome_base else "RAW"

        eh_video = ext in ("MKV", "MP4", "WEBM", "AVI", "WMV")
        cor_bg_badge = CORES["badge_ext_mkv_bg"] if eh_video else CORES["badge_ext_outros_bg"]
        cor_txt_badge = CORES["badge_ext_mkv_txt"] if eh_video else CORES["badge_ext_outros_txt"]

        self.badge_ext = ctk.CTkLabel(
            self,
            text=ext,
            font=("Consolas", 10, "bold"),
            fg_color=cor_bg_badge,
            text_color=cor_txt_badge,
            corner_radius=raio_card,
            width=44,
            height=18,
        )
        self.badge_ext.pack(side="left", padx=(6, 8), pady=4)

        texto_nome = nome_base if len(nome_base) <= 68 else nome_base[:65] + "..."
        self.lbl_nome = ctk.CTkLabel(
            self,
            text=texto_nome,
            font=(fonte_ui, 11),
            text_color=CORES["texto_principal"],
            anchor="w",
        )
        self.lbl_nome.pack(side="left", fill="x", expand=True, padx=2, pady=4)

        self.btn_del = ctk.CTkButton(
            self,
            text="×",
            command=lambda: self.on_delete_cb(self.caminho_arquivo),
            width=22,
            height=20,
            corner_radius=raio_card,
            font=("Consolas", 12, "bold"),
            fg_color="transparent",
            hover_color=CORES["destaque_vermelho"],
            text_color=CORES["texto_secundario"],
        )
        self.btn_del.pack(side="right", padx=(4, 6), pady=4)

        abrev_dest = Idiomas.abreviar_destino(destino_lang, I18n.obter_idioma())
        self.badge_fluxo = ctk.CTkLabel(
            self,
            text=f"->{abrev_dest}",
            font=("Consolas", 10, "bold"),
            fg_color=CORES["badge_fluxo_bg"],
            text_color=CORES["badge_fluxo_txt"],
            corner_radius=raio_card,
            width=48,
            height=18,
        )
        self.badge_fluxo.pack(side="right", padx=4, pady=4)

        self.btn_ia = ctk.CTkButton(
            self,
            text="",
            command=self._ao_clicar_ia,
            height=20,
            width=110,
            corner_radius=raio_card,
            font=("Consolas", 10, "bold"),
            fg_color=CORES["bg_sidebar"],
            hover_color=CORES["bg_card_hover"],
            border_color=CORES["destaque_azul"],
            border_width=1,
            text_color=CORES["destaque_azul"],
        )

    def _ao_clicar_ia(self):
        if self.on_inspect_ia_cb:
            self.on_inspect_ia_cb(self.caminho_arquivo)

    def definir_status_ia(self, requer_ia: bool, modelo_id: str = "small", confirmado: bool = False):
        """Exibe ou oculta o botao de analise/escolha de IA apenas para arquivos que usarao transcricao."""
        self._requer_ia = requer_ia
        self._modelo_ia = modelo_id or "small"
        self._confirmado_ia = confirmado

        if not requer_ia:
            self.btn_ia.pack_forget()
            return

        chave = "btn_card_ia_pronta" if confirmado else "btn_card_analisar_ia"
        cor_destaque = CORES["destaque_verde"] if confirmado else CORES["destaque_azul"]
        self.btn_ia.configure(
            text=I18n.t(chave).format(self._modelo_ia.upper()),
            border_color=cor_destaque,
            text_color=cor_destaque,
            fg_color=CORES["bg_sidebar"],
            hover_color=CORES["bg_card_hover"],
        )
        self.btn_ia.pack(side="right", padx=4, pady=4)

    def atualizar_destino(self, novo_destino: str):
        """Atualiza o texto do indicador de fluxo de idioma da linha e botao de IA se ativo."""
        self._destino_lang = novo_destino
        abrev_dest = Idiomas.abreviar_destino(novo_destino, I18n.obter_idioma())
        self.badge_fluxo.configure(text=f"->{abrev_dest}")
        if self._requer_ia:
            self.definir_status_ia(True, self._modelo_ia, self._confirmado_ia)

    def aplicar_tema(self, cores: dict):
        """Atualiza visual da linha de acordo com o tema ativo."""
        largura_borda = cores.get("borda_largura", 1)
        raio_card = cores.get("raio_card", 2)
        fonte_ui = cores.get("fonte_ui", "Segoe UI")

        self.configure(
            fg_color=cores["bg_card"],
            border_color=cores["borda_card"],
            border_width=largura_borda,
            corner_radius=raio_card,
        )
        self.lbl_nome.configure(text_color=cores["texto_principal"], font=(fonte_ui, 11))
        self.btn_del.configure(
            text_color=cores["texto_secundario"],
            hover_color=cores["destaque_vermelho"],
            corner_radius=raio_card,
        )

        ext = self.badge_ext.cget("text")
        if ext in ("MKV", "MP4", "WEBM", "AVI", "WMV"):
            self.badge_ext.configure(
                fg_color=cores["badge_ext_mkv_bg"],
                text_color=cores["badge_ext_mkv_txt"],
                font=("Consolas", 10, "bold"),
                corner_radius=raio_card,
            )
        else:
            self.badge_ext.configure(
                fg_color=cores["badge_ext_outros_bg"],
                text_color=cores["badge_ext_outros_txt"],
                font=("Consolas", 10, "bold"),
                corner_radius=raio_card,
            )

        self.badge_fluxo.configure(
            fg_color=cores["badge_fluxo_bg"],
            text_color=cores["badge_fluxo_txt"],
            font=("Consolas", 10, "bold"),
            corner_radius=raio_card,
        )
        if self._requer_ia:
            self.definir_status_ia(True, self._modelo_ia, self._confirmado_ia)


class PainelFilaView(ctk.CTkFrame):
    """Painel principal da fila com cabecalho de tabela, poco de drop e grade densa rolavel."""

    def __init__(self, master, on_add_cb, on_clear_cb, on_remove_item_cb, on_inspect_ia_cb=None):
        super().__init__(master, fg_color="transparent")
        self.on_add_cb = on_add_cb
        self.on_clear_cb = on_clear_cb
        self.on_remove_item_cb = on_remove_item_cb
        self.on_inspect_ia_cb = on_inspect_ia_cb

        self._cards_instanciados = []
        self._total_atual = 0
        self._arquivos_sem_legenda = set()
        self._modelos_por_arquivo = {}
        self._modelo_padrao = "small"
        self._construir_widgets()

    def _construir_widgets(self):
        largura_borda = CORES.get("borda_largura", 1)
        raio_card = CORES.get("raio_card", 2)
        fonte_ui = CORES.get("fonte_ui", "Segoe UI")

        frame_barra = ctk.CTkFrame(self, fg_color="transparent")
        frame_barra.pack(fill="x", pady=(0, 6))

        self.lbl_titulo = ctk.CTkLabel(
            frame_barra,
            text=f"{I18n.t('fila_titulo')} (0)",
            font=(fonte_ui, 12, "bold"),
            text_color=CORES["texto_principal"],
        )
        self.lbl_titulo.pack(side="left")

        self.btn_limpar = ctk.CTkButton(
            frame_barra,
            text=I18n.t("btn_limpar"),
            command=self.on_clear_cb,
            width=64,
            height=24,
            corner_radius=raio_card,
            font=(fonte_ui, 11),
            fg_color=CORES["bg_card"],
            border_color=CORES["borda_card"],
            border_width=largura_borda,
            text_color=CORES["texto_secundario"],
            hover_color=CORES["bg_card_hover"],
        )
        self.btn_limpar.pack(side="right", padx=(4, 0))

        self.btn_add = ctk.CTkButton(
            frame_barra,
            text=I18n.t("btn_add"),
            command=self.on_add_cb,
            width=136,
            height=24,
            corner_radius=raio_card,
            fg_color=CORES["destaque_azul"],
            hover_color=CORES["destaque_azul_hover"],
            text_color=CORES.get("btn_destaque_txt", "#ffffff"),
            font=(fonte_ui, 11, "bold"),
        )
        self.btn_add.pack(side="right")

        # Cabecalho de Colunas estilo Tabela Nativa
        self.frame_cabecalho_tabela = ctk.CTkFrame(
            self,
            fg_color=CORES["bg_sidebar"],
            border_color=CORES["borda_card"],
            border_width=largura_borda,
            corner_radius=0,
            height=24,
        )
        self.frame_cabecalho_tabela.pack(fill="x", pady=(0, 2))
        self.frame_cabecalho_tabela.pack_propagate(False)

        self.lbl_col_tipo = ctk.CTkLabel(
            self.frame_cabecalho_tabela,
            text=I18n.t("fila_col_fmt"),
            font=("Consolas", 10, "bold"),
            text_color=CORES["texto_secundario"],
            width=48,
            anchor="w",
        )
        self.lbl_col_tipo.pack(side="left", padx=(8, 4))

        self.lbl_col_nome = ctk.CTkLabel(
            self.frame_cabecalho_tabela,
            text=I18n.t("fila_col_arquivo"),
            font=("Consolas", 10, "bold"),
            text_color=CORES["texto_secundario"],
            anchor="w",
        )
        self.lbl_col_nome.pack(side="left", fill="x", expand=True, padx=2)

        self.lbl_col_alvo = ctk.CTkLabel(
            self.frame_cabecalho_tabela,
            text=I18n.t("fila_col_destino"),
            font=("Consolas", 10, "bold"),
            text_color=CORES["texto_secundario"],
            width=84,
            anchor="e",
        )
        self.lbl_col_alvo.pack(side="right", padx=(4, 28))

        # Dropzone rebaixada sobria para estado vazio
        self.frame_dropzone = ctk.CTkFrame(
            self,
            fg_color=CORES["bg_console"],
            border_color=CORES["borda_card"],
            border_width=largura_borda,
            corner_radius=raio_card,
        )
        self.frame_dropzone.pack(fill="both", expand=True)

        self.lbl_drop_icone = ctk.CTkLabel(
            self.frame_dropzone,
            text="[ + ]",
            font=("Consolas", 18, "bold"),
            text_color=CORES["texto_secundario"],
        )
        self.lbl_drop_icone.pack(pady=(90, 4))

        self.lbl_drop_texto = ctk.CTkLabel(
            self.frame_dropzone,
            text=I18n.t("drop_texto"),
            font=(fonte_ui, 11),
            text_color=CORES["texto_principal"],
        )
        self.lbl_drop_texto.pack(pady=1)

        self.lbl_drop_sub = ctk.CTkLabel(
            self.frame_dropzone,
            text=I18n.t("drop_sub"),
            font=(fonte_ui, 10),
            text_color=CORES["texto_secundario"],
        )
        self.lbl_drop_sub.pack(pady=1)

        # Container scrollable para as linhas da tabela
        self.scroll_cards = ctk.CTkScrollableFrame(
            self,
            fg_color=CORES["bg_console"],
            border_color=CORES["borda_card"],
            border_width=largura_borda,
            corner_radius=raio_card,
        )

    def renderizar_fila(self, arquivos: list, destino_lang: str):
        """Renderiza ou atualiza as linhas de arquivos na grade da fila."""
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
            card = CardArquivo(
                self.scroll_cards,
                arq,
                destino_lang,
                self.on_remove_item_cb,
                on_inspect_ia_cb=self.on_inspect_ia_cb,
            )
            card.pack(fill="x", pady=1, padx=1)
            self._cards_instanciados.append(card)

        self._aplicar_status_ia_nos_cards()

    def atualizar_status_ia(self, arquivos_sem_legenda: set, modelos_por_arquivo: dict, modelo_padrao: str = "small"):
        """Atualiza nas linhas quais arquivos requerem IA e o modelo selecionado para cada um."""
        self._arquivos_sem_legenda = set(arquivos_sem_legenda)
        self._modelos_por_arquivo = dict(modelos_por_arquivo)
        self._modelo_padrao = modelo_padrao or "small"
        self._aplicar_status_ia_nos_cards()

    def _aplicar_status_ia_nos_cards(self):
        for card in self._cards_instanciados:
            arq = card.caminho_arquivo
            requer = arq in self._arquivos_sem_legenda
            confirmado = arq in self._modelos_por_arquivo
            modelo = self._modelos_por_arquivo.get(arq, self._modelo_padrao)
            card.definir_status_ia(requer, modelo_id=modelo, confirmado=confirmado)

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
        self.lbl_col_tipo.configure(text=I18n.t("fila_col_fmt"))
        self.lbl_col_nome.configure(text=I18n.t("fila_col_arquivo"))
        self.lbl_col_alvo.configure(text=I18n.t("fila_col_destino"))
        self.lbl_drop_texto.configure(text=I18n.t("drop_texto"))
        self.lbl_drop_sub.configure(text=I18n.t("drop_sub"))
        for card in self._cards_instanciados:
            card.atualizar_destino(card._destino_lang)

    def aplicar_tema(self, cores: dict):
        """Propaga as novas cores, fontes e cantos do tema para dropzone, cabecalho e linhas da fila."""
        largura_borda = cores.get("borda_largura", 1)
        raio_card = cores.get("raio_card", 2)
        fonte_ui = cores.get("fonte_ui", "Segoe UI")

        self.lbl_titulo.configure(text_color=cores["texto_principal"], font=(fonte_ui, 12, "bold"))
        self.btn_limpar.configure(
            fg_color=cores["bg_card"],
            border_color=cores["borda_card"],
            border_width=largura_borda,
            text_color=cores["texto_secundario"],
            hover_color=cores["bg_card_hover"],
            font=(fonte_ui, 11),
            corner_radius=raio_card,
        )
        self.btn_add.configure(
            fg_color=cores["destaque_azul"],
            hover_color=cores["destaque_azul_hover"],
            text_color=cores.get("btn_destaque_txt", "#ffffff"),
            font=(fonte_ui, 11, "bold"),
            corner_radius=raio_card,
        )
        self.frame_cabecalho_tabela.configure(
            fg_color=cores["bg_sidebar"],
            border_color=cores["borda_card"],
            border_width=largura_borda,
        )
        for lbl_col in (self.lbl_col_tipo, self.lbl_col_nome, self.lbl_col_alvo):
            lbl_col.configure(text_color=cores["texto_secundario"])

        self.frame_dropzone.configure(
            fg_color=cores["bg_console"],
            border_color=cores["borda_card"],
            border_width=largura_borda,
            corner_radius=raio_card,
        )
        self.lbl_drop_icone.configure(text_color=cores["texto_secundario"])
        self.lbl_drop_texto.configure(text_color=cores["texto_principal"], font=(fonte_ui, 11))
        self.lbl_drop_sub.configure(text_color=cores["texto_secundario"], font=(fonte_ui, 10))
        self.scroll_cards.configure(
            fg_color=cores["bg_console"],
            border_color=cores["borda_card"],
            border_width=largura_borda,
            corner_radius=raio_card,
        )

        for card in self._cards_instanciados:
            card.aplicar_tema(cores)

    def atualizar_destinos(self, novo_destino: str):
        """Atualiza a indicacao de idioma de destino em todas as linhas ativas."""
        for card in self._cards_instanciados:
            card.atualizar_destino(novo_destino)

    def set_interativo(self, habilitado: bool):
        """Habilita ou desabilita os botoes de manipulacao da fila."""
        estado = "normal" if habilitado else "disabled"
        self.btn_add.configure(state=estado)
        self.btn_limpar.configure(state=estado)
        for card in self._cards_instanciados:
            card.btn_ia.configure(state=estado)
