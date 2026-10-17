"""View layer: Orquestradora da Interface Grafica Moderna (v2.7.0).

Monta a janela principal e orquestra a comunicacao entre os componentes
visuais especializados (Header, Sidebar, Fila e Footer) e o ControladorApp.
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

from .ui import CORES, HeaderView, SidebarView, PainelFilaView, FooterView


class InterfaceGrafica(ctk.CTk, TkinterDnD.DnDWrapper if HAS_DND else object):
    """View layer: Janela principal e mediadora de eventos da interface visual."""

    def __init__(self):
        super().__init__()
        if HAS_DND:
            self.TkdndVersion = TkinterDnD._require(self)

        self.title("Taradutor de Legendas — v2.7.0")
        self.geometry("920x660")
        self.minsize(860, 600)
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
        # 1. Cabecalho Superior
        self.header = HeaderView(self)
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

    # ── 2. Gerenciamento de Arquivos e Fila ──────────────────────────────────

    def _select_files(self):
        files = filedialog.askopenfilenames(
            title="Selecione os videos MKV ou arquivos de legenda",
            filetypes=[
                ("Todos Suportados", "*.mkv *.ass *.srt *.txt"),
                ("Video MKV", "*.mkv"),
                ("Legenda", "*.ass *.srt *.txt")
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
            messagebox.showwarning("Aviso", "Nenhum arquivo valido suportado (MKV/ASS/SRT/TXT).")

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

    # ── 3. Acoes do Usuario delegadas ao Controller ─────────────────────────

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

    # ── 4. Callbacks Publicos (Contrato do Controller/Model) ────────────────

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
        evento = threading.Event()
        resposta = [False]

        def _perguntar():
            r = messagebox.askyesno(
                "Arquivo ja existe",
                f"O(s) arquivo(s) abaixo ja existe(m):\n\n{nomes_arquivos}\n\nDeseja sobrescrever?"
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
            self.footer.set_status("Processamento concluido com sucesso!")
            if winsound:
                try:
                    winsound.MessageBeep(winsound.MB_ICONASTERISK)
                except Exception:
                    pass
        self.after(0, _finalizar)
