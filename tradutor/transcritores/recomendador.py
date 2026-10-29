"""Serviço de análise técnica de mídia e hardware para recomendação de modelo Whisperfile."""

import ctypes
import json
import os
import re
import subprocess
from dataclasses import dataclass

from ..config import GerenciadorConfig
from ..manipulador_mkv import ManipuladorMkv


@dataclass(frozen=True, slots=True)
class DiagnosticoAudioWhisper:
    """Value Object imutável com o diagnóstico do vídeo e a recomendação de modelo de IA."""

    modelo_recomendado: str
    modelo_alternativo: str | None
    duracao_segundos: float
    idioma_audio: str
    canais_audio: int
    possui_fundo_musical: bool
    proporcao_silencio: float
    ram_livre_gb: float
    nucleos_cpu: int
    chave_motivo: str


class _MemoryStatusEx(ctypes.Structure):
    """Estrutura nativa Win32 MEMORYSTATUSEX para consulta de memória física sem dependências externas."""

    _fields_ = [
        ("dwLength", ctypes.c_ulong),
        ("dwMemoryLoad", ctypes.c_ulong),
        ("ullTotalPhys", ctypes.c_ulonglong),
        ("ullAvailPhys", ctypes.c_ulonglong),
        ("ullTotalPageFile", ctypes.c_ulonglong),
        ("ullAvailPageFile", ctypes.c_ulonglong),
        ("ullTotalVirtual", ctypes.c_ulonglong),
        ("ullAvailVirtual", ctypes.c_ulonglong),
        ("sullAvailExtendedVirtual", ctypes.c_ulonglong),
    ]


class RecomendadorModeloWhisper:
    """Inspeciona duração, idioma, densidade sonora (música/efeitos) e RAM para recomendar o melhor modelo."""

    IDIOMAS_COMPLEXOS = {"und", "auto", "jpn", "ja", "chi", "zho", "zh", "zh-cn", "kor", "ko", "rus", "ru"}

    @staticmethod
    def obter_recursos_sistema() -> tuple[float, int]:
        """Retorna (ram_livre_gb, nucleos_cpu) consultando a API nativa do sistema operacional."""
        nucleos = os.cpu_count() or 4
        ram_livre_gb = 8.0

        if os.name == "nt":
            try:
                stat = _MemoryStatusEx()
                stat.dwLength = ctypes.sizeof(_MemoryStatusEx)
                if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat)):
                    ram_livre_gb = round(stat.ullAvailPhys / (1024**3), 1)
            except Exception:
                pass

        return ram_livre_gb, nucleos

    @staticmethod
    def inspecionar_metadados_mkv(caminho_arquivo: str) -> tuple[float, str, int]:
        """Retorna (duracao_segundos, idioma_audio, canais_audio) via mkvmerge -J."""
        duracao_s = 0.0
        idioma = "und"
        canais = 2

        if not caminho_arquivo or not os.path.isfile(caminho_arquivo):
            return duracao_s, idioma, canais

        try:
            mkvmerge_bin, _ = GerenciadorConfig.get_mkv_bins()
            res = subprocess.run(
                [mkvmerge_bin, "-J", caminho_arquivo],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="ignore",
                check=False,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
                timeout=10,
            )
            if res.returncode == 0 and res.stdout:
                dados = json.loads(res.stdout)
                props_container = dados.get("container", {}).get("properties", {})
                duracao_ns = props_container.get("duration")
                if isinstance(duracao_ns, (int, float)) and duracao_ns > 0:
                    duracao_s = round(float(duracao_ns) / 1_000_000_000.0, 1)

                for track in dados.get("tracks", []):
                    if track.get("type") == "audio":
                        props = track.get("properties", {})
                        idioma = (props.get("language") or "und").lower()
                        canais = int(props.get("audio_channels") or 2)
                        break
        except Exception:
            pass

        return duracao_s, idioma, canais

    @staticmethod
    def analisar_acustica_ffmpeg(caminho_arquivo: str, duracao_segundos: float) -> tuple[bool, float]:
        """Amostra até 30s do áudio via filtro silencedetect do FFmpeg para detectar música/efeitos contínuos."""
        ffmpeg_bin = ManipuladorMkv._localizar_ffmpeg()
        if not ffmpeg_bin or not caminho_arquivo or not os.path.isfile(caminho_arquivo):
            return True, 0.10

        janela = min(duracao_segundos, 30.0) if duracao_segundos > 0 else 30.0
        try:
            cmd = [
                ffmpeg_bin,
                "-hide_banner",
                "-nostats",
                "-t",
                f"{janela:.1f}",
                "-i",
                caminho_arquivo,
                "-vn",
                "-af",
                "silencedetect=n=-32dB:d=0.35",
                "-f",
                "null",
                "-",
            ]
            res = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="ignore",
                check=False,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
                timeout=15,
            )
            saida = (res.stderr or "") + "\n" + (res.stdout or "")
            duracoes = [float(x) for x in re.findall(r"silence_duration:\s*([0-9.]+)", saida)]
            total_silencio = sum(duracoes)

            inicios = [float(x) for x in re.findall(r"silence_start:\s*([0-9.]+)", saida)]
            if len(inicios) > len(duracoes) and inicios[-1] < janela:
                total_silencio += max(0.0, janela - inicios[-1])

            proporcao = round(min(max(total_silencio / max(janela, 1.0), 0.0), 1.0), 2)
            possui_fundo_musical = proporcao < 0.18
            return possui_fundo_musical, proporcao
        except Exception:
            return True, 0.10

    @classmethod
    def analisar_arquivo(cls, caminho_arquivo: str) -> DiagnosticoAudioWhisper:
        """Executa o diagnóstico completo do arquivo de mídia e retorna a recomendação fundamentada."""
        ram_livre_gb, nucleos_cpu = cls.obter_recursos_sistema()
        duracao_s, idioma, canais = cls.inspecionar_metadados_mkv(caminho_arquivo)
        possui_fundo, prop_silencio = cls.analisar_acustica_ffmpeg(caminho_arquivo, duracao_s)

        modelo_rec, modelo_alt, chave_motivo = cls._decidir_modelo(
            duracao_segundos=duracao_s,
            idioma_audio=idioma,
            canais_audio=canais,
            possui_fundo_musical=possui_fundo,
            proporcao_silencio=prop_silencio,
            ram_livre_gb=ram_livre_gb,
        )

        return DiagnosticoAudioWhisper(
            modelo_recomendado=modelo_rec,
            modelo_alternativo=modelo_alt,
            duracao_segundos=duracao_s,
            idioma_audio=idioma,
            canais_audio=canais,
            possui_fundo_musical=possui_fundo,
            proporcao_silencio=prop_silencio,
            ram_livre_gb=ram_livre_gb,
            nucleos_cpu=nucleos_cpu,
            chave_motivo=chave_motivo,
        )

    @classmethod
    def _decidir_modelo(
        cls,
        duracao_segundos: float,
        idioma_audio: str,
        canais_audio: int,
        possui_fundo_musical: bool,
        proporcao_silencio: float,
        ram_livre_gb: float,
    ) -> tuple[str, str | None, str]:
        """Árvore de decisão determinística para escolha do modelo Whisperfile ideal."""
        if ram_livre_gb < 2.2:
            return "tiny", "small", "diag_motivo_ram_baixa"

        idioma_complexo = idioma_audio.lower() in cls.IDIOMAS_COMPLEXOS
        video_longo = duracao_segundos >= 900.0
        video_curto = 0.0 < duracao_segundos <= 180.0

        if not possui_fundo_musical and not idioma_complexo and video_longo and canais_audio <= 2:
            return "tiny", "small", "diag_motivo_voz_limpa_longo"

        if (canais_audio >= 6 or proporcao_silencio < 0.04) and video_curto and ram_livre_gb >= 6.0:
            return "medium", "small", "diag_motivo_fundo_denso_curto"

        if possui_fundo_musical or idioma_complexo or canais_audio > 2:
            alternativa = "medium" if ram_livre_gb >= 4.0 else "tiny"
            return "small", alternativa, "diag_motivo_musica_ou_und"

        return "small", "tiny", "diag_motivo_equilibrio_padrao"

