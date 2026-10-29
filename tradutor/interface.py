"""View layer: Orquestradora da Interface Grafica Moderna (v2.8.0).

Monta a janela principal e orquestra a comunicacao entre os componentes
visuais especializados (Header, Sidebar, Fila, Footer e Modais) e o ControladorApp.
"""

import os
import threading
from tkinter import filedialog, messagebox
import customtkinter as ctk

try:
    from tkinterdnd2 import TkinterDnD, DND_FILES
    HAS_DND = True
except ImportError:
    HAS_DND = False

try:
    import winsound
except ImportError:
    winsound = None

from .ui import (
    CORES,
    HeaderView,
    SidebarView,
    PainelFilaView,
    FooterView,
    ModalGrimorio,
    ModalConfiguracoes,
    ModalTemas,
    ModalConfirmacaoWhisper
)
from .config_usuario import PreferenciasUsuario
from .idiomas import Idiomas
from .i18n import I18n


class InterfaceGrafica(ctk.CTk, TkinterDnD.DnDWrapper if HAS_DND else object):
    """View layer: Janela principal e mediadora de eventos da interface visual."""

    def __init__(self):
        super().__init__()
        if HAS_DND:
            self.TkdndVersion = TkinterDnD._require(self)

        self.title(f"{I18n.t('app_nome')} — v2.8.0")
        self.geometry("940x670")
        self.minsize(880, 600)
        self.configure(fg_color=CORES["bg_janela"])

        self._controller = None
        self.files = []
        self._arquivos_sem_legenda = set()
        self._modelos_ia_por_arquivo = {}
        self._em_execucao = False

        self._montar_layout()

        if HAS_DND:
            self.drop_target_register(DND_FILES)
            self.dnd_bind('<<Drop>>', self._on_files_dropped)

        self.protocol("WM_DELETE_WINDOW", self._on_closing_request)

    def set_controller(self, controller):
        """Injeta a referencia do Controller mediador."""
        self._controller = controller

    @property
    def controller(self):
        """Retorna a instancia do controlador mediador."""
        return self._controller

    # ── 1. Montagem e Composicao dos Componentes ────────────────────────────

    def _montar_layout(self):
        # 1. Cabecalho Superior com Acoes Rapidas
        self.header = HeaderView(
            self,
            on_grimorio_cb=self._abrir_grimorio,
            on_tema_cb=self._abrir_seletor_tema,
            on_config_cb=self._abrir_configuracoes
        )
        self.header.pack(side="top", fill="x")

        # 2. Container Central (Duas Colunas)
        self.frame_conteudo = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_conteudo.pack(side="top", fill="both", expand=True, padx=14, pady=(12, 0))

        # Coluna Esquerda: Parametros de Traducao
        self.sidebar = SidebarView(self.frame_conteudo, on_destino_alterado_cb=self._on_destino_alterado)
        self.sidebar.pack(side="left", fill="y", padx=(0, 12))

        # Coluna Direita: Fila e Cards
        self.fila = PainelFilaView(
            self.frame_conteudo,
            on_add_cb=self._select_files,
            on_clear_cb=self._limpar_fila,
            on_remove_item_cb=self._remover_arquivo,
            on_inspect_ia_cb=self._inspecionar_ia_arquivo,
        )
        self.fila.pack(side="left", fill="both", expand=True)

        # 3. Rodape de Status, Progresso e Console de Logs
        self.footer = FooterView(
            self,
            on_start_cb=self._on_start_clicked,
            on_cancel_cb=self._on_cancel_clicked
        )
        self.footer.pack(side="bottom", fill="x", pady=(10, 0))

    # ── 2. Modais e Personalizacao ──────────────────────────────────────────

    def _abrir_grimorio(self):
        ModalGrimorio(self)

    def _abrir_seletor_tema(self):
        ModalTemas(self, ao_trocar_tema_cb=self._aplicar_novo_tema)

    def _abrir_configuracoes(self):
        ModalConfiguracoes(self, ao_alterar_idioma_cb=self._aplicar_novo_idioma)

    def _aplicar_novo_tema(self, nome_tema: str):
        cores = CORES
        self.configure(fg_color=cores["bg_janela"])
        self.header.aplicar_tema(cores)
        self.sidebar.aplicar_tema(cores)
        self.fila.aplicar_tema(cores)
        self.footer.aplicar_tema(cores)

    def _aplicar_novo_idioma(self, codigo_idioma: str):
        self.title(f"{I18n.t('app_nome')} — v2.8.0")
        self.header.redefinir_textos()
        self.sidebar.redefinir_textos()
        self.fila.redefinir_textos(len(self.files))
        self.footer.redefinir_textos()

    # ── 3. Gerenciamento de Arquivos e Fila ──────────────────────────────────

    def _select_files(self):
        files = filedialog.askopenfilenames(
            title=I18n.t("dialogo_selecionar_arquivos"),
            filetypes=[
                (I18n.t("tipo_todos_suportados"), "*.mkv *.mp4 *.webm *.avi *.wmv *.ass *.srt *.txt"),
                (I18n.t("tipo_video_mkv"), "*.mkv *.mp4 *.webm *.avi *.wmv"),
                (I18n.t("tipo_legendas"), "*.ass *.srt *.txt")
            ]
        )
        if files:
            novos = [f for f in files if f not in self.files]
            self.files.extend(novos)
            self._sincronizar_fila()

    def _on_files_dropped(self, event):
        if not HAS_DND:
            return
        arquivos = self.tk.splitlist(event.data)
        extensoes_validas = ('.mkv', '.mp4', '.webm', '.avi', '.wmv', '.ass', '.srt', '.txt')
        validos = [f for f in arquivos if f.lower().endswith(extensoes_validas) and f not in self.files]
        if validos:
            self.files.extend(validos)
            self._sincronizar_fila()
        else:
            messagebox.showwarning(I18n.t("aviso_titulo"), I18n.t("aviso_nenhum_arquivo_valido"))

    def _esta_em_execucao(self) -> bool:
        """Verifica se há um lote em processamento ativo na interface ou no controlador."""
        return self._em_execucao or bool(getattr(self._controller, "is_running", False))

    def _remover_arquivo(self, caminho: str):
        if self._esta_em_execucao():
            arq_atual = getattr(self._controller, "arquivo_atual", None)
            if arq_atual and os.path.abspath(arq_atual) == os.path.abspath(caminho):
                return
        if caminho in self.files:
            self.files.remove(caminho)
            self._arquivos_sem_legenda.discard(caminho)
            self._modelos_ia_por_arquivo.pop(caminho, None)
            self._sincronizar_fila()

    def _limpar_fila(self):
        if self._esta_em_execucao():
            return
        self.files.clear()
        self._arquivos_sem_legenda.clear()
        self._modelos_ia_por_arquivo.clear()
        self._sincronizar_fila()

    def _on_destino_alterado(self, novo_destino: str):
        self.fila.atualizar_destinos(novo_destino)

    def _sincronizar_fila(self):
        self.fila.renderizar_fila(self.files, self.sidebar.idioma_destino)
        if self._esta_em_execucao():
            self.fila.set_interativo(False)
            return
        self.footer.configurar_modo_pronto(len(self.files) > 0)
        if self._controller:
            self._controller.on_files_selected(self.files)

    def _inspecionar_ia_arquivo(self, caminho_arquivo: str):
        """Abre o modal de analise acustica e escolha de modelo para o arquivo selecionado na fila."""
        nome_base = os.path.basename(caminho_arquivo)

        def _ao_confirmar(autorizado: bool):
            if autorizado:
                modelo_escolhido = PreferenciasUsuario.obter("modelo_whisper", "small")
                self._modelos_ia_por_arquivo[caminho_arquivo] = modelo_escolhido
                self.fila.atualizar_status_ia(
                    self._arquivos_sem_legenda,
                    self._modelos_ia_por_arquivo,
                    modelo_padrao=modelo_escolhido,
                )

        ModalConfirmacaoWhisper(
            self,
            nome_base,
            ao_decidir_cb=_ao_confirmar,
            caminho_arquivo=caminho_arquivo,
        )

    # ── 4. Acoes do Usuario delegadas ao Controller ─────────────────────────

    def _on_start_clicked(self):
        if self._controller and self.files:
            self._controller.start_translation(
                self.files,
                self.sidebar.idioma_origem,
                self.sidebar.idioma_destino,
                self.sidebar.manter_legenda
            )

    def _on_cancel_clicked(self):
        if self._controller:
            self._controller.cancel_translation()
            self.footer.configurar_modo_cancelando()

    def _on_closing_request(self):
        if self._controller:
            self._controller.on_closing()
        else:
            self.destroy()

    # ── 5. Callbacks Publicos (Contrato do Controller/Model) ────────────────

    def prepare_for_processing(self):
        """Prepara a interface para o inicio da traducao."""
        self._em_execucao = True
        self.footer.configurar_modo_execucao()
        self.fila.set_interativo(False)

    def update_language_options(self, langs: list):
        """Atualiza a lista de idiomas disponiveis detectados nos MKVs sem ocultar opcoes manuais."""
        langs_definidos = [l for l in langs if l and l.lower() != "und"]
        opcoes = ["auto"] + langs_definidos
        for padrao in Idiomas.opcoes_origem_padrao():
            if padrao not in opcoes:
                opcoes.append(padrao)
        valor_padrao = langs_definidos[0] if len(langs_definidos) == 1 else "auto"
        self.after(0, lambda: self.sidebar.atualizar_opcoes_origem(opcoes, valor_padrao))

    def update_whisper_candidates(self, sem_legenda: set):
        """Exibe o botao de analise de IA apenas nos cards de videos que nao possuem legenda embutida."""
        self._arquivos_sem_legenda = set(sem_legenda)
        modelo_padrao = PreferenciasUsuario.obter("modelo_whisper", "small")
        self.after(
            0,
            lambda: self.fila.atualizar_status_ia(
                self._arquivos_sem_legenda,
                self._modelos_ia_por_arquivo,
                modelo_padrao=modelo_padrao,
            ),
        )

    def log(self, msg: str):
        """Grava no console interno e atualiza status inline (thread-safe)."""
        def _atualizar():
            self.footer.escrever_log(msg)
            self.footer.set_status(msg)
        self.after(0, _atualizar)

    def update_progress(self, current: int, total: int):
        """Atualiza barra de progresso e porcentagem (thread-safe)."""
        self.after(0, lambda: self.footer.set_progresso(current, total))

    def ask_overwrite(self, nomes_arquivos: str) -> bool:
        """Exibe confirmacao modal de sobrescrita de forma thread-safe."""
        politica = PreferenciasUsuario.obter("politica_sobrescrita", "perguntar")
        if politica == "sobrescrever":
            return True
        if politica == "pular":
            return False

        evento = threading.Event()
        resposta = [False]

        def _perguntar():
            r = messagebox.askyesno(
                I18n.t("msg_sobrescrever_titulo"),
                I18n.t("msg_sobrescrever_corpo").format(nomes_arquivos)
            )
            resposta[0] = r
            evento.set()

        self.after(0, _perguntar)
        evento.wait()
        return resposta[0]

    def ask_output_format(self, nome_arquivo: str, extensao: str) -> str:
        """Pergunta ao usuario se deseja converter um video nao-MKV para .mkv ou manter o formato original."""
        evento = threading.Event()
        resposta = ["converter_mkv"]

        def _perguntar():
            converter = messagebox.askyesno(
                I18n.t("msg_formato_saida_titulo"),
                I18n.t("msg_formato_saida_corpo").format(nome_arquivo, extensao.upper()),
            )
            resposta[0] = "converter_mkv" if converter else "manter_original"
            evento.set()

        self.after(0, _perguntar)
        evento.wait()
        return resposta[0]

    def ask_whisper_permission(self, nome_arquivo: str) -> bool:
        """Exibe modal interativo de permissao, diagnostico de video e selecao/download de modelo da IA local Whisperfile."""
        caminho_completo = (
            nome_arquivo
            if os.path.isfile(nome_arquivo)
            else next(
                (f for f in self.files if os.path.basename(f) == os.path.basename(nome_arquivo)),
                None,
            )
        )
        if caminho_completo and caminho_completo in self._modelos_ia_por_arquivo:
            PreferenciasUsuario.definir("modelo_whisper", self._modelos_ia_por_arquivo[caminho_completo])
            return True

        evento = threading.Event()
        resposta = [False]

        def _decidir(autorizado: bool):
            if autorizado and caminho_completo:
                modelo_escolhido = PreferenciasUsuario.obter("modelo_whisper", "small")
                self._modelos_ia_por_arquivo[caminho_completo] = modelo_escolhido
                self.fila.atualizar_status_ia(
                    self._arquivos_sem_legenda,
                    self._modelos_ia_por_arquivo,
                    modelo_padrao=modelo_escolhido,
                )
            resposta[0] = autorizado
            evento.set()

        self.after(
            0,
            lambda: ModalConfirmacaoWhisper(
                self,
                nome_arquivo,
                ao_decidir_cb=_decidir,
                caminho_arquivo=caminho_completo,
            ),
        )
        evento.wait()
        return resposta[0]

    def on_processing_finished(self):
        """Restaura controles e notifica usuario ao concluir."""
        def _finalizar():
            self._em_execucao = False
            self.footer.configurar_modo_pronto(len(self.files) > 0)
            self.fila.set_interativo(True)
            self.footer.set_status(I18n.t("status_concluido"))
            if PreferenciasUsuario.obter("tocar_som", True) and winsound:
                try:
                    winsound.MessageBeep(winsound.MB_ICONASTERISK)
                except Exception:
                    pass
            if PreferenciasUsuario.obter("abrir_pasta_ao_concluir", False) and self.files:
                try:
                    pasta_destino = os.path.dirname(self.files[0])
                    if pasta_destino and os.path.exists(pasta_destino):
                        os.startfile(pasta_destino)
                except Exception:
                    pass
        self.after(0, _finalizar)
