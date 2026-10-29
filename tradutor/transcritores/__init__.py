"""Pacote de motores opcionais de transcrição de áudio (ASR) para geração de legendas."""

from .base import ITranscritor, ResultadoTranscricao, StatusWhisper
from .recomendador import DiagnosticoAudioWhisper, RecomendadorModeloWhisper
from .whisperfile import MotorWhisperfile

__all__ = [
    "ITranscritor",
    "StatusWhisper",
    "ResultadoTranscricao",
    "MotorWhisperfile",
    "DiagnosticoAudioWhisper",
    "RecomendadorModeloWhisper",
]
