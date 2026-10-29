from .processador_mkv import ProcessadorMkv
from .processador_srt import ProcessadorSrt

class FabricaProcessadores:
    """Fábrica que decide qual Estratégia usar com base na extensão do arquivo."""
    
    @staticmethod
    def get_processor(filepath, log_cb, progress_cb, ask_overwrite_cb, is_running_cb, engine=None):
        ext = filepath.lower()
        if ext.endswith('.mkv'):
            return ProcessadorMkv(log_cb, progress_cb, ask_overwrite_cb, is_running_cb, engine=engine)
        elif ext.endswith(('.srt', '.ass', '.txt')):
            return ProcessadorSrt(log_cb, progress_cb, ask_overwrite_cb, is_running_cb, engine=engine)
        else:
            raise ValueError(f"Formato não suportado pela Fábrica: {filepath}")
