import os
import shutil
import asyncio
from abc import ABC, abstractmethod

from ..config import GerenciadorConfig
from ..servico_traducao import ServicoTraducao
from ..tradutores import MotorTraducaoGoogle
from ..idiomas import Idiomas


class ProcessadorArquivoBase(ABC):
    """
    Template Method Pattern: Define o esqueleto do processamento
    de qualquer arquivo (MKV, SRT, ASS, TXT). Delega os detalhes
    específicos para as subclasses (Estratégias).
    """

    def __init__(
        self,
        log_cb,
        progress_cb,
        ask_overwrite_cb,
        is_running_cb,
        engine=None,
        ask_whisper_cb=None,
        ask_output_format_cb=None,
    ):
        self.log = log_cb
        self.update_progress = progress_cb
        self.ask_overwrite = ask_overwrite_cb
        self.is_running = is_running_cb
        self.engine = engine
        self.ask_whisper = ask_whisper_cb
        self.ask_output_format = ask_output_format_cb

    def process(self, origem, idioma_origem, idioma_destino, manter_legenda) -> bool:
        """Executa o pipeline padrão para um arquivo."""

        # 1. Preparação Específica (Extração MKV, Transcrição IA ou Bypass SRT)
        arq_trabalho, idioma_real = self.prepare(origem, idioma_origem)
        if not arq_trabalho:
            return False

        # 2. Verificações de Idioma
        src_google = Idiomas.para_google(idioma_real)
        if src_google == "auto":
            self.log("[AVISO] Idioma de origem indefinido no contêiner. Usando autodetecção.")
        else:
            self.log(f"Idioma de origem: {idioma_real} (Google: {src_google})")

        mesmo_idioma = src_google == idioma_destino.lower()
        if mesmo_idioma:
            if self.should_skip_if_same_language():
                self.log(f"-> Origem e destino iguais ({src_google}). Arquivo pulado.")
                self.cleanup_temporary(arq_trabalho)
                return False
            else:
                self.log(f"[INFO] Origem e destino iguais ({src_google}). Embutindo legenda transcrita diretamente.")

        # 3. Resolução de Caminhos de Saída
        caminhos_saida = self.get_output_paths(origem, idioma_destino, arq_trabalho)

        # 4. Verificação de Conflitos (Arquivos Existentes)
        if not self._check_conflicts(caminhos_saida, arq_trabalho):
            return False

        try:
            caminho_legenda_final = caminhos_saida['legenda']

            # 5. Tradução (ou cópia direta quando já transcrito no idioma de destino)
            if mesmo_idioma and getattr(self, "_transcrito_por_ia", False):
                shutil.copyfile(arq_trabalho, caminho_legenda_final)
            else:
                self.log(self.get_translation_message())
                engine = self.engine or MotorTraducaoGoogle(max_retries=GerenciadorConfig.MAX_RETENTATIVAS)
                translator_svc = ServicoTraducao(
                    logger=self.log,
                    progress_callback=self.update_progress,
                    is_cancelled_callback=lambda: not self.is_running(),
                    engine=engine,
                    video_filename=os.path.basename(origem),
                )
                asyncio.run(translator_svc.pipeline(arq_trabalho, caminho_legenda_final, idioma_real, idioma_destino))

            if not self.is_running():
                return False

            # 6. Finalização (Muxing MKV ou Conclusão SRT)
            self.finalize(origem, caminho_legenda_final, caminhos_saida, idioma_destino, arq_trabalho, manter_legenda)
            return True

        except Exception as e:
            self.cleanup_temporary(arq_trabalho)
            raise e

    def _check_conflicts(self, caminhos_saida: dict, arq_trabalho: str) -> bool:
        """Verifica se os arquivos de saída já existem e pede confirmação ao usuário."""
        conflitos = [
            os.path.basename(p)
            for p in caminhos_saida.values()
            if p and os.path.exists(p)
        ]

        if conflitos:
            nomes = ", ".join(conflitos)
            self.log(f"Aguardando confirmação para sobrescrever: {nomes}...")
            if not self.ask_overwrite(nomes):
                self.log("-> Arquivo pulado pelo usuário (não sobrescrever).")
                self.cleanup_temporary(arq_trabalho)
                return False
            self.log("-> Sobrescrita confirmada. Continuando...")
        return True

    @abstractmethod
    def prepare(self, origem: str, idioma_origem: str) -> tuple[str, str]:
        """Prepara o arquivo de legenda de trabalho e descobre o idioma real."""
        pass

    @abstractmethod
    def should_skip_if_same_language(self) -> bool:
        """Define se deve abortar caso origem == destino."""
        pass

    @abstractmethod
    def cleanup_temporary(self, arq_trabalho: str):
        """Limpa arquivos temporários gerados na etapa prepare (se houver)."""
        pass

    @abstractmethod
    def get_output_paths(self, origem: str, idioma_destino: str, arq_trabalho: str) -> dict:
        """Retorna dicionário com caminhos de saída esperados ('legenda' e opcional 'video')."""
        pass

    @abstractmethod
    def get_translation_message(self) -> str:
        """Mensagem de log exibida antes de iniciar a tradução."""
        pass

    @abstractmethod
    def finalize(self, origem: str, legenda_traduzida: str, caminhos_saida: dict, idioma_destino: str, arq_trabalho: str, manter_legenda: bool):
        """Etapa pós-tradução (ex: muxing de vídeo e limpeza de temporários)."""
        pass
