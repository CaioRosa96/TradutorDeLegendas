"""Implementação do motor de transcrição baseado no executável portátil Mozilla Whisperfile."""

import os
import shutil
import subprocess
import time

from ..config import GerenciadorConfig
from ..idiomas import Idiomas
from .base import ITranscritor, ResultadoTranscricao
from .repositorio_modelos import RepositorioModelosWhisper


class MotorWhisperfile(ITranscritor):
    """Adaptador para os executáveis standalone Mozilla Whisperfile (whisper.cpp / Cosmopolitan Libc)."""

    CATALOGO_MODELOS = RepositorioModelosWhisper.CATALOGO_MODELOS
    NOMES_PADRAO = RepositorioModelosWhisper.NOMES_PADRAO

    def __init__(
        self,
        caminho_executavel: str | None = None,
        timeout_segundos: int = 1800,
        id_modelo: str | None = None,
        repositorio: type[RepositorioModelosWhisper] | None = None,
    ):
        self._repositorio = repositorio or RepositorioModelosWhisper
        self._timeout_segundos = timeout_segundos

        if not id_modelo or not caminho_executavel:
            try:
                from ..config_usuario import PreferenciasUsuario
                if not id_modelo:
                    id_modelo = PreferenciasUsuario.obter("modelo_whisper", "small")
                if not caminho_executavel:
                    cfg_path = PreferenciasUsuario.obter("caminho_whisperfile", "")
                    if cfg_path:
                        caminho_executavel = cfg_path
            except Exception:
                pass

        self._caminho_executavel = caminho_executavel
        self._id_modelo = id_modelo or "small"

    @classmethod
    def obter_pasta_bin(cls) -> str:
        """Retorna o diretório bin/ local onde os modelos portáteis são armazenados."""
        return RepositorioModelosWhisper.obter_pasta_bin()

    @classmethod
    def caminho_modelo(cls, id_modelo: str) -> str | None:
        """Retorna o caminho absoluto de um modelo específico se já estiver instalado."""
        return RepositorioModelosWhisper.caminho_modelo(id_modelo)

    @classmethod
    def esta_modelo_instalado(cls, id_modelo: str) -> bool:
        """Verifica se o modelo informado já foi baixado e existe em disco."""
        return RepositorioModelosWhisper.esta_modelo_instalado(id_modelo)

    @classmethod
    def baixar_modelo(cls, id_modelo: str, progresso_cb=None, cancelado_cb=None) -> str:
        """Baixa o executável standalone do modelo Whisperfile selecionado a partir do HuggingFace."""
        return RepositorioModelosWhisper.baixar_modelo(id_modelo, progresso_cb, cancelado_cb)

    def resolver_executavel(self) -> str | None:
        """Localiza o binário do whisperfile no sistema ou na pasta bin/."""
        if self._caminho_executavel and os.path.isfile(self._caminho_executavel):
            return os.path.abspath(self._caminho_executavel)

        if self._id_modelo:
            caminho_mod = self._repositorio.caminho_modelo(self._id_modelo)
            if caminho_mod:
                return caminho_mod

        for pasta_base in (GerenciadorConfig.DIRETORIO_EXECUCAO, GerenciadorConfig.DIRETORIO_RECURSOS):
            for nome in self.NOMES_PADRAO:
                for sub in ("bin", "mkvtoolnix"):
                    candidato = os.path.join(pasta_base, sub, nome)
                    if os.path.isfile(candidato):
                        return os.path.abspath(candidato)

        for nome in self.NOMES_PADRAO:
            no_path = shutil.which(nome)
            if no_path:
                return os.path.abspath(no_path)

        return None

    def esta_disponivel(self) -> bool:
        """Indica se há ao menos um binário do Whisperfile disponível para execução."""
        return self.resolver_executavel() is not None

    @staticmethod
    def _normalizar_idioma_whisper(idioma: str | None) -> str:
        """Converte códigos ISO-639-2 (ex: 'jpn', 'eng') para ISO-639-1 aceito pelo whisper.cpp."""
        cod = Idiomas.para_google(idioma)
        if cod == "zh-cn":
            return "zh"
        return cod

    def transcrever(self, caminho_audio: str, idioma: str = "auto") -> ResultadoTranscricao:
        """Executa o Whisperfile sobre o arquivo de áudio e gera um arquivo .srt sincronizado."""
        exe = self.resolver_executavel()
        if not exe:
            raise FileNotFoundError("Binário do Mozilla Whisperfile não encontrado.")

        if not os.path.isfile(caminho_audio):
            raise FileNotFoundError(f"Arquivo de áudio não encontrado: {caminho_audio}")

        idioma_norm = self._normalizar_idioma_whisper(idioma) or "auto"
        comando = [exe, "-f", caminho_audio, "-osrt", "-l", idioma_norm, "-mc", "0"]

        inicio = time.time()
        resultado = subprocess.run(
            comando,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
            check=False,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            timeout=self._timeout_segundos,
        )
        duracao = round(time.time() - inicio, 2)

        if resultado.returncode != 0:
            detalhe = (resultado.stderr or resultado.stdout or "").strip()
            raise RuntimeError(f"Falha na transcrição via Whisperfile (código {resultado.returncode}): {detalhe}")

        caminho_srt = f"{caminho_audio}.srt"
        if not os.path.exists(caminho_srt):
            base_sem_ext = os.path.splitext(caminho_audio)[0]
            alternativo = f"{base_sem_ext}.srt"
            if os.path.exists(alternativo):
                caminho_srt = alternativo
            else:
                raise FileNotFoundError("O arquivo .srt não foi gerado pelo Whisperfile após a transcrição.")

        return ResultadoTranscricao(
            caminho_srt=caminho_srt,
            idioma_detectado=idioma_norm,
            duracao_segundos=duracao,
        )
