"""View layer: Orquestradora da Interface Grafica Moderna (v2.7.0).

Monta a janela principal e orquestra a comunicacao entre os componentes
visuais especializados (Header, Sidebar, Fila, Footer e Modais) e o ControladorApp.
"""

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
    ModalTemas
)
from .config_usuario import PreferenciasUsuario
from .i18n import I18n


class InterfaceGrafica(ctk.CTk, TkinterDnD.DnDWrapper if HAS_DND else object):
    """View layer: Janela principal e mediadora de eventos da interface visual."""

    def __init__(self):
        super().__init__()
        if HAS_DND:
            self.TkdndVersion = TkinterDnD._require(self)

        self.title(f"{I18n.t('app_nome')} — v2.7.0")
        self.geometry("940x670")
        self.minsize(880, 600)
        self.configure(fg_color=CORES["bg_janela"])

        self._controller = None
        self.files = []

        self._montar_layout()

        if HAS_DND:
            self.drop_target_register(DND_FILES)
            self.dnd_bind('<<Drop>>', self._on_files_dropped)

        self.protocol("WM_DELETE_WINDOW", self._on_closing_request)

    def set_controller(self, controller):
        """Injeta a referencia do Controller mediador."""
        self._controller = controller

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
            on_remove_item_cb=self._remover_arquivo
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
        self.title(f"{I18n.t('app_nome')} — v2.7.0")
        self.header.redefinir_textos()
        self.sidebar.redefinir_textos()
        self.fila.redefinir_textos(len(self.files))
        self.footer.redefinir_textos()


    # ── 3. Gerenciamento de Arquivos e Fila ──────────────────────────────────

    def _select_files(self):
        files = filedialog.askopenfilenames(
            title=I18n.t("dialogo_selecionar_arquivos"),
            filetypes=[
                (I18n.t("tipo_todos_suportados"), "*.mkv *.ass *.srt *.txt"),
                (I18n.t("tipo_video_mkv"), "*.mkv"),
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
        extensoes_validas = ('.mkv', '.ass', '.srt', '.txt')
        validos = [f for f in arquivos if f.lower().endswith(extensoes_validas) and f not in self.files]
        if validos:
            self.files.extend(validos)
            self._sincronizar_fila()
        else:
            messagebox.showwarning(I18n.t("aviso_titulo"), I18n.t("aviso_nenhum_arquivo_valido"))

    def _remover_arquivo(self, caminho: str):
        if caminho in self.files:
            self.files.remove(caminho)
            self._sincronizar_fila()

    def _limpar_fila(self):
        self.files.clear()
        self._sincronizar_fila()

    def _on_destino_alterado(self, novo_destino: str):
        self.fila.atualizar_destinos(novo_destino)

    def _sincronizar_fila(self):
        self.fila.renderizar_fila(self.files, self.sidebar.idioma_destino)
        self.footer.configurar_modo_pronto(len(self.files) > 0)
        if self._controller:
            self._controller.on_files_selected(self.files)

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
        self.footer.configurar_modo_execucao()
        self.fila.set_interativo(False)

    def update_language_options(self, langs: list):
        """Atualiza a lista de idiomas disponiveis detectados nos MKVs."""
        opcoes = ["auto"] + langs
        valor_padrao = langs[0] if len(langs) == 1 else "auto"
        self.after(0, lambda: self.sidebar.atualizar_opcoes_origem(opcoes, valor_padrao))

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

    def on_processing_finished(self):
        """Restaura controles e notifica usuario ao concluir."""
        def _finalizar():
            self.footer.configurar_modo_pronto(len(self.files) > 0)
            self.fila.set_interativo(True)
            self.footer.set_status(I18n.t("status_concluido"))
            if PreferenciasUsuario.obter("tocar_som", True) and winsound:
                try:
                    winsound.MessageBeep(winsound.MB_ICONASTERISK)
                except Exception:
                    pass
        self.after(0, _finalizar)
