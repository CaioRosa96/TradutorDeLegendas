"""Contratos abstratos e objetos de valor para motores de transcrição de áudio (ASR)."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum


class StatusWhisper(Enum):
    """Estados operacionais do motor de transcrição local."""

    PRONTO = "pronto"
    NAO_INSTALADO = "nao_instalado"
    ERRO = "erro"


@dataclass(frozen=True, slots=True)
class ResultadoTranscricao:
    """Value Object imutável com os metadados da legenda gerada por transcrição."""

    caminho_srt: str
    idioma_detectado: str
    duracao_segundos: float = 0.0


class ITranscritor(ABC):
    """Contrato formal para motores de transcrição de áudio em legendas."""

    @abstractmethod
    def esta_disponivel(self) -> bool:
        """Verifica se o binário e modelo de transcrição estão acessíveis no disco."""
        pass

    @abstractmethod
    def transcrever(self, caminho_audio: str, idioma: str = "auto") -> ResultadoTranscricao:
        """Transcreve um arquivo de áudio e retorna os metadados do .srt gerado."""
        pass

