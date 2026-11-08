"""Servico de diagnostico, vinculacao de pasta customizada e download sob demanda do MKVToolNix/FFmpeg."""

from dataclasses import dataclass
import os
import shutil
import subprocess
import zipfile
import requests

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
    """Gerencia a resolucao, validacao de pasta externa e download sob demanda de binarios GPLv2."""

    URL_PACOTE_PORTATIL = (
        "https://github.com/CaioRosa96/TradutorDeLegendas/releases/latest/download/mkvtoolnix-portable-win64.zip"
    )
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
    def _extrair_executaveis_zip(cls, caminho_zip: str, pasta_destino: str):
        """Extrai mkvmerge.exe, mkvextract.exe e ffmpeg.exe (se presentes) de um arquivo .zip."""
        alvos = {"mkvmerge.exe", "mkvextract.exe", "ffmpeg.exe"}
        os.makedirs(pasta_destino, exist_ok=True)

        with zipfile.ZipFile(caminho_zip, "r") as zf:
            for membro in zf.infolist():
                nome_base = os.path.basename(membro.filename).lower()
                if nome_base in alvos and not membro.is_dir():
                    destino_bin = os.path.join(pasta_destino, nome_base)
                    destino_temp = f"{destino_bin}.part"
                    with zf.open(membro) as origem_f, open(destino_temp, "wb") as dest_f:
                        shutil.copyfileobj(origem_f, dest_f)
                    if os.path.exists(destino_bin):
                        os.remove(destino_bin)
                    os.replace(destino_temp, destino_bin)

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
        url_pacote: str | None = None,
    ) -> str:
        """Baixa o pacote portatil para mkvtoolnix/ ou aciona fallback via winget."""
        pasta_destino = cls.obter_pasta_destino_local()
        os.makedirs(pasta_destino, exist_ok=True)
        arquivo_zip_temp = os.path.join(pasta_destino, "mkvtoolnix_portable.zip.part")
        url_alvo = url_pacote or cls.URL_PACOTE_PORTATIL

        try:
            with requests.get(url_alvo, stream=True, timeout=60) as resp:
                resp.raise_for_status()
                total_bytes = int(resp.headers.get("content-length", 0))
                baixados = 0

                with open(arquivo_zip_temp, "wb") as f:
                    for chunk in resp.iter_content(chunk_size=1024 * 256):
                        if cancelado_cb and cancelado_cb():
                            raise InterruptedError("Download cancelado pelo usuario.")
                        if chunk:
                            f.write(chunk)
                            baixados += len(chunk)
                            if progresso_cb and total_bytes > 0:
                                progresso_cb(baixados, total_bytes)

            cls._extrair_executaveis_zip(arquivo_zip_temp, pasta_destino)
            if GerenciadorConfig.check_dependencies():
                return GerenciadorConfig.get_mkvtoolnix_path()
        except InterruptedError:
            raise
        except Exception as erro_http:
            if cls._instalar_via_winget():
                return GerenciadorConfig.get_mkvtoolnix_path()
            raise RuntimeError(
                f"Nao foi possivel baixar automaticamente o MKVToolNix ({erro_http})."
            ) from erro_http
        finally:
            if os.path.exists(arquivo_zip_temp):
                try:
                    os.remove(arquivo_zip_temp)
                except OSError:
                    pass

        raise RuntimeError("Os executaveis mkvmerge.exe e mkvextract.exe nao foram encontrados apos o download.")

