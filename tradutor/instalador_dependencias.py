"""Servico de diagnostico, vinculacao de pasta customizada e instalacao via winget para MKVToolNix/FFmpeg."""

from dataclasses import dataclass
import os
import shutil
import subprocess

from .config import GerenciadorConfig
from .config_usuario import PreferenciasUsuario


@dataclass(frozen=True, slots=True)
class StatusDependencias:
    """Value Object imutavel com o estado de deteccao das ferramentas externas."""

    mkvtoolnix_ok: bool
    ffmpeg_ok: bool
    caminho_mkvtoolnix: str
    caminho_ffmpeg: str


class InstaladorDependencias:
    """Gerencia a resolucao, validacao de pasta externa e instalacao oficial de binarios GPLv2."""

    URL_PAGINA_OFICIAL_MKVTOOLNIX = "https://mkvtoolnix.download/downloads.html#windows"
    WINGET_ID_MKVTOOLNIX = "MoritzBunkus.MKVToolNix"

    @classmethod
    def diagnosticar(cls) -> StatusDependencias:
        """Inspeciona o ambiente atual e retorna o status detalhado do MKVToolNix e FFmpeg."""
        mkv_ok = GerenciadorConfig.check_dependencies()
        caminho_mkv = GerenciadorConfig.get_mkvtoolnix_path() if mkv_ok else ""
        caminho_ff = GerenciadorConfig.get_ffmpeg_path() or ""
        return StatusDependencias(
            mkvtoolnix_ok=mkv_ok,
            ffmpeg_ok=bool(caminho_ff),
            caminho_mkvtoolnix=caminho_mkv,
            caminho_ffmpeg=caminho_ff,
        )

    @classmethod
    def definir_pasta_existente(cls, caminho_pasta: str) -> tuple[bool, str]:
        """Valida se a pasta contem mkvmerge.exe e mkvextract.exe e persiste nas preferencias."""
        pasta_valida = GerenciadorConfig.validar_pasta_mkvtoolnix(caminho_pasta)
        if not pasta_valida:
            return False, ""

        PreferenciasUsuario.definir("mkvtoolnix_custom", pasta_valida)
        ffmpeg_candidato = os.path.join(pasta_valida, "ffmpeg.exe")
        if os.path.isfile(ffmpeg_candidato):
            PreferenciasUsuario.definir("ffmpeg_custom", pasta_valida)

        return True, pasta_valida

    @classmethod
    def obter_pasta_destino_local(cls) -> str:
        """Retorna a pasta local mkvtoolnix/ ao lado do executavel/script."""
        return os.path.join(GerenciadorConfig.DIRETORIO_EXECUCAO, "mkvtoolnix")

    @classmethod
    def _instalar_via_winget(cls) -> bool:
        """Tenta instalar o MKVToolNix silenciosamente via Windows Package Manager (winget)."""
        if not shutil.which("winget"):
            return False
        try:
            cmd = [
                "winget",
                "install",
                "--id",
                cls.WINGET_ID_MKVTOOLNIX,
                "-e",
                "--accept-source-agreements",
                "--accept-package-agreements",
            ]
            subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,
                check=False,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
            return GerenciadorConfig.check_dependencies()
        except Exception:
            return False

    @classmethod
    def baixar_dependencias(
        cls,
        progresso_cb=None,
        cancelado_cb=None,
    ) -> str:
        """Instala o MKVToolNix sob demanda via winget (fonte oficial GPLv2 sem redistribuicao no .exe)."""
        if cancelado_cb and cancelado_cb():
            raise InterruptedError("Instalacao cancelada pelo usuario.")

        if GerenciadorConfig.check_dependencies():
            return GerenciadorConfig.get_mkvtoolnix_path()

        if cls._instalar_via_winget():
            if cancelado_cb and cancelado_cb():
                raise InterruptedError("Instalacao cancelada pelo usuario.")
            return GerenciadorConfig.get_mkvtoolnix_path()

        raise RuntimeError(
            "Nao foi possivel instalar o MKVToolNix automaticamente via winget. "
            f"Baixe manualmente em {cls.URL_PAGINA_OFICIAL_MKVTOOLNIX} ou selecione a pasta existente."
        )

