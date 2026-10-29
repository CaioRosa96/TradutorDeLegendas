"""Implementação do motor de transcrição baseado no executável portátil Mozilla Whisperfile."""

import os
import shutil
import subprocess
import time
import requests

from ..config import GerenciadorConfig
from ..idiomas import Idiomas
from .base import ITranscritor, ResultadoTranscricao


class MotorWhisperfile(ITranscritor):
    """Adaptador para os executáveis standalone Mozilla Whisperfile (whisper.cpp / Cosmopolitan Libc)."""

    CATALOGO_MODELOS = {
        "tiny": {
            "id": "tiny",
            "executavel": "whisper-tiny.exe",
            "tamanho_aprox": "83 MB",
            "url": "https://huggingface.co/Mozilla/whisperfile/resolve/main/whisper-tiny.llamafile",
            "chave_nome": "whisper_mod_tiny",
        },
        "small": {
            "id": "small",
            "executavel": "whisper-small.exe",
            "tamanho_aprox": "474 MB",
            "url": "https://huggingface.co/Mozilla/whisperfile/resolve/main/whisper-small.llamafile",
            "chave_nome": "whisper_mod_small",
        },
        "medium": {
            "id": "medium",
            "executavel": "whisper-medium.exe",
            "tamanho_aprox": "1.7 GB",
            "url": "https://huggingface.co/Mozilla/whisperfile/resolve/main/whisper-medium.llamafile",
            "chave_nome": "whisper_mod_medium",
        },
        "large-v3": {
            "id": "large-v3",
            "executavel": "whisper-large-v3.exe",
            "tamanho_aprox": "3.1 GB",
            "url": "https://huggingface.co/Mozilla/whisperfile/resolve/main/whisper-large-v3.llamafile",
            "chave_nome": "whisper_mod_large",
        },
    }

    NOMES_PADRAO = (
        "whisper-small.exe",
        "whisper-base.exe",
        "whisper-medium.exe",
        "whisper-large-v3.exe",
        "whisperfile.exe",
        "whisper-tiny.exe",
    )

    def __init__(
        self,
        caminho_executavel: str | None = None,
        timeout_segundos: int = 1800,
        id_modelo: str | None = None,
    ):
        self._caminho_executavel = caminho_executavel
        self._timeout_segundos = timeout_segundos
        self._id_modelo = id_modelo

    @classmethod
    def obter_pasta_bin(cls) -> str:
        """Retorna o diretório bin/ local onde os modelos portáteis são armazenados."""
        return os.path.join(GerenciadorConfig.DIRETORIO_EXECUCAO, "bin")

    @classmethod
    def caminho_modelo(cls, id_modelo: str) -> str | None:
        """Retorna o caminho absoluto de um modelo específico se já estiver instalado."""
        info = cls.CATALOGO_MODELOS.get(id_modelo)
        if not info:
            return None
        nome_exe = info["executavel"]
        for pasta_base in (GerenciadorConfig.DIRETORIO_EXECUCAO, GerenciadorConfig.DIRETORIO_RECURSOS):
            for sub in ("bin", "mkvtoolnix"):
                candidato = os.path.join(pasta_base, sub, nome_exe)
                if os.path.isfile(candidato) and os.path.getsize(candidato) > 1024:
                    return os.path.abspath(candidato)
        return None

    @classmethod
    def esta_modelo_instalado(cls, id_modelo: str) -> bool:
        """Verifica se o modelo informado já foi baixado e existe em disco."""
        return cls.caminho_modelo(id_modelo) is not None

    @classmethod
    def baixar_modelo(cls, id_modelo: str, progresso_cb=None, cancelado_cb=None) -> str:
        """Baixa o executável standalone do modelo Whisperfile selecionado a partir do HuggingFace."""
        info = cls.CATALOGO_MODELOS.get(id_modelo)
        if not info:
            raise ValueError(f"Modelo Whisperfile desconhecido: {id_modelo}")

        pasta_bin = cls.obter_pasta_bin()
        os.makedirs(pasta_bin, exist_ok=True)
        destino_final = os.path.join(pasta_bin, info["executavel"])
        destino_temp = f"{destino_final}.part"

        try:
            with requests.get(info["url"], stream=True, timeout=60) as resp:
                resp.raise_for_status()
                total_bytes = int(resp.headers.get("content-length", 0))
                baixados = 0

                with open(destino_temp, "wb") as f:
                    for chunk in resp.iter_content(chunk_size=1024 * 256):
                        if cancelado_cb and cancelado_cb():
                            raise InterruptedError("Download cancelado pelo usuário.")
                        if chunk:
                            f.write(chunk)
                            baixados += len(chunk)
                            if progresso_cb and total_bytes > 0:
                                progresso_cb(baixados, total_bytes)

            if os.path.exists(destino_final):
                os.remove(destino_final)
            os.replace(destino_temp, destino_final)
            return os.path.abspath(destino_final)
        except Exception:
            if os.path.exists(destino_temp):
                try:
                    os.remove(destino_temp)
                except OSError:
                    pass
            raise

    def resolver_executavel(self) -> str | None:
        """Localiza o binário do whisperfile priorizando o modelo selecionado pelo usuário."""
        candidatos = []
        if self._caminho_executavel:
            candidatos.append(self._caminho_executavel)

        modelo_pref = self._id_modelo
        try:
            from ..config_usuario import PreferenciasUsuario
            custom_cfg = PreferenciasUsuario.obter("caminho_whisperfile", "")
            if custom_cfg:
                candidatos.append(custom_cfg)
            if not modelo_pref:
                modelo_pref = PreferenciasUsuario.obter("modelo_whisper", "small")
        except Exception:
            pass

        if modelo_pref and modelo_pref in self.CATALOGO_MODELOS:
            exe_pref = self.CATALOGO_MODELOS[modelo_pref]["executavel"]
            for pasta_base in (GerenciadorConfig.DIRETORIO_EXECUCAO, GerenciadorConfig.DIRETORIO_RECURSOS):
                candidatos.append(os.path.join(pasta_base, "bin", exe_pref))
                candidatos.append(os.path.join(pasta_base, "mkvtoolnix", exe_pref))

        for pasta_base in (GerenciadorConfig.DIRETORIO_EXECUCAO, GerenciadorConfig.DIRETORIO_RECURSOS):
            for nome in self.NOMES_PADRAO:
                candidatos.append(os.path.join(pasta_base, "bin", nome))
                candidatos.append(os.path.join(pasta_base, "mkvtoolnix", nome))

        for c in candidatos:
            if c and os.path.isfile(c):
                return os.path.abspath(c)

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
