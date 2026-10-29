from .processador_mkv import ProcessadorMkv
from .processador_srt import ProcessadorSrt


class FabricaProcessadores:
    """Fábrica que decide qual Estratégia usar com base na extensão do arquivo."""

    EXTENSOES_VIDEO = ('.mkv', '.mp4', '.webm', '.avi', '.wmv')
    EXTENSOES_LEGENDA = ('.srt', '.ass', '.txt')

    @staticmethod
    def get_processor(
        filepath,
        log_cb,
        progress_cb,
        ask_overwrite_cb,
        is_running_cb,
        engine=None,
        ask_whisper_cb=None,
        ask_output_format_cb=None,
    ):
        ext = filepath.lower()
        if ext.endswith(FabricaProcessadores.EXTENSOES_VIDEO):
            return ProcessadorMkv(
                log_cb,
                progress_cb,
                ask_overwrite_cb,
                is_running_cb,
                engine=engine,
                ask_whisper_cb=ask_whisper_cb,
                ask_output_format_cb=ask_output_format_cb,
            )
        elif ext.endswith(FabricaProcessadores.EXTENSOES_LEGENDA):
            return ProcessadorSrt(
                log_cb,
                progress_cb,
                ask_overwrite_cb,
                is_running_cb,
                engine=engine,
                ask_whisper_cb=ask_whisper_cb,
                ask_output_format_cb=ask_output_format_cb,
            )
        else:
            raise ValueError(f"Formato não suportado pela Fábrica: {filepath}")
