"""Porta de domínio e adaptadores para manipulação e multiplexação de mídia."""
from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from typing import Callable, Protocol, Sequence, runtime_checkable

from .config import GerenciadorConfig
from .manipulador_mkv import ManipuladorMkv


@dataclass(frozen=True, slots=True)
class TrilhaMidia:
    """Representa os metadados imutáveis de uma trilha contida em um arquivo multimídia."""

    id: int
    tipo: str
    idioma: str = "und"
    codec: str = ""
    formato: str = ""
    nome: str = ""


@runtime_checkable
class ManipuladorMidiaPort(Protocol):
    """Porta de domínio para inspeção, extração e multiplexação de mídias."""

    def listar_trilhas(self, arquivo: str) -> Sequence[TrilhaMidia]:
        """Inspeciona o arquivo e retorna a lista de trilhas identificadas."""
        ...

    def extrair_legenda(self, arquivo: str, id_trilha: int, destino: str) -> str:
        """Extrai uma trilha de legenda específica para o caminho indicado."""
        ...

    def extrair_audio(self, arquivo: str, destino: str) -> str:
        """Extrai o fluxo de áudio para transcrição ou processamento externo."""
        ...

    def embutir_legenda(
        self,
        video: str,
        legenda: str,
        saida: str,
        idioma: str = "pt",
    ) -> str:
        """Multiplexa o contêiner de vídeo com a legenda traduzida."""
        ...


def _eh_diretorio(caminho: str) -> bool:
    """Verifica se o caminho informado representa um diretório existente ou pretendido."""
    if os.path.isdir(caminho) or caminho.endswith(("/", "\\")):
        return True
    _, ext = os.path.splitext(caminho)
    return not bool(ext)


class AdaptadorMkvToolNixFFmpeg(ManipuladorMidiaPort):
    """Adaptador de infraestrutura que delega operações para MKVToolNix e FFmpeg via subprocess."""

    def __init__(self, logger: Callable[[str], None] | None = None) -> None:
        self._logger = logger or (lambda _msg: None)

    def listar_trilhas(self, arquivo: str) -> list[TrilhaMidia]:
        """Obtém as trilhas do contêiner multimídia via ManipuladorMkv."""
        return ManipuladorMkv.listar_trilhas(arquivo)

    def extrair_legenda(self, arquivo: str, id_trilha: int, destino: str) -> str:
        """Extrai a trilha de legenda indicada delegando para o subprocesso isolado."""
        caminho_final = destino
        if _eh_diretorio(destino):
            nome_base = os.path.basename(arquivo).rsplit(".", 1)[0]
            caminho_final = os.path.join(destino, f"{nome_base}_trilha_{id_trilha}.ass")
        os.makedirs(os.path.dirname(os.path.abspath(caminho_final)), exist_ok=True)
        return ManipuladorMkv.extrair_trilha(arquivo, id_trilha, caminho_final)

    def extrair_audio(self, arquivo: str, destino: str) -> str:
        """Extrai o fluxo de áudio do arquivo delegando para ManipuladorMkv."""
        pasta_destino = destino if _eh_diretorio(destino) else (os.path.dirname(os.path.abspath(destino)) or ".")
        os.makedirs(pasta_destino, exist_ok=True)
        caminho_extraido, _ = ManipuladorMkv.extrair_audio(
            caminho_mkv=arquivo,
            pasta_destino=pasta_destino,
            idioma_preferido=None,
            logger=self._logger,
        )
        if not _eh_diretorio(destino) and caminho_extraido != destino and os.path.exists(caminho_extraido):
            shutil.move(caminho_extraido, destino)
            return destino
        return caminho_extraido

    def embutir_legenda(
        self,
        video: str,
        legenda: str,
        saida: str,
        idioma: str = "pt",
    ) -> str:
        """Multiplexa a legenda traduzida no contêiner final via ManipuladorMkv."""
        os.makedirs(os.path.dirname(os.path.abspath(saida)), exist_ok=True)
        return ManipuladorMkv.embutir_legenda(
            caminho_mkv_original=video,
            caminho_legenda_traduzida=legenda,
            caminho_saida=saida,
            idioma_destino=idioma,
            logger=self._logger,
        )


class FakeManipuladorMidia(ManipuladorMidiaPort):
    """Implementação em memória da porta de mídia para testes determinísticos sem binários."""

    def __init__(
        self,
        trilhas: Sequence[TrilhaMidia] | dict[str, Sequence[TrilhaMidia]] | None = None,
    ) -> None:
        self._trilhas_configuradas = trilhas
        self.chamadas_listar_trilhas: list[str] = []
        self.chamadas_extrair_legenda: list[tuple[str, int, str]] = []
        self.chamadas_extrair_audio: list[tuple[str, str]] = []
        self.chamadas_embutir_legenda: list[tuple[str, str, str, str]] = []

        self.conteudo_legenda_padrao: str = (
            "1\n00:00:01,000 --> 00:00:02,000\nLinha fake de teste\n"
        )
        self.simular_erro_listar_trilhas: Exception | None = None
        self.simular_erro_extrair_legenda: Exception | None = None
        self.simular_erro_extrair_audio: Exception | None = None
        self.simular_erro_embutir_legenda: Exception | None = None

    def listar_trilhas(self, arquivo: str) -> list[TrilhaMidia]:
        self.chamadas_listar_trilhas.append(arquivo)
        if self.simular_erro_listar_trilhas is not None:
            raise self.simular_erro_listar_trilhas

        if isinstance(self._trilhas_configuradas, dict):
            if arquivo in self._trilhas_configuradas:
                return list(self._trilhas_configuradas[arquivo])
            nome = os.path.basename(arquivo)
            if nome in self._trilhas_configuradas:
                return list(self._trilhas_configuradas[nome])
            return []

        if self._trilhas_configuradas is not None:
            return list(self._trilhas_configuradas)

        return [
            TrilhaMidia(id=0, tipo="video", idioma="und", codec="AVC/H.264"),
            TrilhaMidia(id=1, tipo="audio", idioma="ja", codec="AAC", formato=".aac"),
            TrilhaMidia(id=2, tipo="subtitles", idioma="ja", codec="SubRip/SRT", formato=".srt"),
        ]

    def extrair_legenda(self, arquivo: str, id_trilha: int, destino: str) -> str:
        self.chamadas_extrair_legenda.append((arquivo, id_trilha, destino))
        if self.simular_erro_extrair_legenda is not None:
            raise self.simular_erro_extrair_legenda

        caminho_final = destino
        if _eh_diretorio(destino):
            caminho_final = os.path.join(destino, f"legenda_extraida_{id_trilha}.srt")

        os.makedirs(os.path.dirname(os.path.abspath(caminho_final)), exist_ok=True)
        if not os.path.exists(caminho_final):
            with open(caminho_final, "w", encoding="utf-8") as f:
                f.write(self.conteudo_legenda_padrao)
        return caminho_final

    def extrair_audio(self, arquivo: str, destino: str) -> str:
        self.chamadas_extrair_audio.append((arquivo, destino))
        if self.simular_erro_extrair_audio is not None:
            raise self.simular_erro_extrair_audio

        caminho_final = destino
        if _eh_diretorio(destino):
            caminho_final = os.path.join(destino, "audio_extraido.wav")

        os.makedirs(os.path.dirname(os.path.abspath(caminho_final)), exist_ok=True)
        if not os.path.exists(caminho_final):
            with open(caminho_final, "wb") as f:
                f.write(b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x80>\x00\x00\x00}\x00\x00\x02\x00\x10\x00data\x00\x00\x00\x00")
        return caminho_final

    def embutir_legenda(
        self,
        video: str,
        legenda: str,
        saida: str,
        idioma: str = "pt",
    ) -> str:
        self.chamadas_embutir_legenda.append((video, legenda, saida, idioma))
        if self.simular_erro_embutir_legenda is not None:
            raise self.simular_erro_embutir_legenda

        os.makedirs(os.path.dirname(os.path.abspath(saida)), exist_ok=True)
        if not os.path.exists(saida):
            with open(saida, "wb") as f:
                f.write(b"VIDEO_CONTAINER_FAKE")
        return saida
