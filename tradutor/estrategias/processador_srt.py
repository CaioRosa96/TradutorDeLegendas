import os
from .processador_base import ProcessadorArquivoBase
from ..idiomas import Idiomas

class ProcessadorSrt(ProcessadorArquivoBase):
    """Estratégia específica para legendas avulsas (SRT, ASS)."""

    def prepare(self, origem, idioma_origem):
        # Para SRT, o arquivo de trabalho é ele mesmo
        return origem, idioma_origem

    def should_skip_if_same_language(self) -> bool:
        # Legendas soltas não pulam, pois o menu pode estar errado
        return False

    def cleanup_temporary(self, arq_trabalho):
        pass # Não há arquivos "_ORIGINAL" para SRT avulso

    def get_output_paths(self, origem, idioma_destino, arq_trabalho) -> dict:
        destino_dir = self.output_dir or os.path.dirname(origem)
        os.makedirs(destino_dir, exist_ok=True)
        nome_base = os.path.basename(origem)
        extensao = nome_base.rsplit('.', 1)[-1]
        nome_sem_ext = nome_base.rsplit('.', 1)[0]
        sufixo = (Idiomas.normalizar_destino(idioma_destino) or Idiomas.para_google(idioma_destino) or "pt").upper()
        
        return {
            'legenda': os.path.join(destino_dir, f"{nome_sem_ext}_{sufixo}.{extensao}"),
            'video': None
        }

    def get_translation_message(self) -> str:
        return "[Etapa 1/1] Tradução via Motor Injetado (Pysubs2)"

    def finalize(self, origem, legenda_traduzida, caminhos_saida, idioma_destino, arq_trabalho, manter_legenda):
        # Para legendas avulsas, não há multiplexação, apenas sucesso!
        pass
