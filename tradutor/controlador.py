class ControladorApp:
    """Controller layer: Ponte entre a View (GUI) e o Model (Orchestrator).

    Traduz ações do usuário em operações de negócio e conecta
    os callbacks do Model aos métodos de atualização da View.
    """

    def __init__(self, view, model):
        self._view = view
        self._model = model

        self._view.set_controller(self)
        self._model.set_callbacks(
            log_cb=self._view.log,
            progress_cb=self._view.update_progress,
            ask_overwrite_cb=self._view.ask_overwrite,
            finish_cb=self._view.on_processing_finished,
            ask_whisper_cb=getattr(self._view, "ask_whisper_permission", None),
            ask_output_format_cb=getattr(self._view, "ask_output_format", None),
        )

    @property
    def is_running(self) -> bool:
        """Retorna se o orquestrador está executando um lote no momento."""
        return bool(getattr(self._model, "is_running", False))

    @property
    def arquivo_atual(self) -> str | None:
        """Retorna o caminho do arquivo atualmente em processamento."""
        return getattr(self._model, "arquivo_em_processamento", None)

    def start_translation(self, files, idioma_origem, idioma_destino, manter_legenda):
        """Prepara a interface e dispara o processamento se não houver lote em andamento."""
        if self.is_running:
            return
        self._view.prepare_for_processing()
        self._model.start(files, idioma_origem, idioma_destino, manter_legenda)

    def cancel_translation(self):
        """Pede ao orquestrador para interromper a fila de traduções."""
        self._model.stop()

    def on_files_selected(self, files):
        """Varre arquivos de vídeo de forma assíncrona em busca de idiomas e trilhas de legenda."""
        import threading
        from .estrategias.fabrica import FabricaProcessadores
        from .manipulador_mkv import ManipuladorMkv

        def _verificar():
            mkvs = [f for f in files if f.lower().endswith(FabricaProcessadores.EXTENSOES_VIDEO)]
            if mkvs:
                langs = ManipuladorMkv.listar_idiomas_legendas(mkvs)
                if langs:
                    self._view.update_language_options(langs)
                sem_legenda = ManipuladorMkv.identificar_mkvs_sem_legenda(mkvs)
                if hasattr(self._view, "update_whisper_candidates"):
                    self._view.update_whisper_candidates(sem_legenda)
            elif hasattr(self._view, "update_whisper_candidates"):
                self._view.update_whisper_candidates(set())

        threading.Thread(target=_verificar, daemon=True).start()

    def on_closing(self):
        """Encerra o processamento e fecha a aplicação."""
        self._model.stop()
        self._view.destroy()
