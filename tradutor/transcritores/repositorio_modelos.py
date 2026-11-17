"""Repositório e gerenciador de download dos modelos Mozilla Whisperfile."""

import os
import requests

from ..config import GerenciadorConfig


class RepositorioModelosWhisper:
    """Gerencia o catálogo, localização em disco e download dos modelos Whisperfile."""

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

    @classmethod
    def obter_pasta_bin(cls) -> str:
        """Retorna o caminho da pasta bin/ onde ficam os executáveis portáteis."""
        return os.path.join(GerenciadorConfig.DIRETORIO_EXECUCAO, "bin")

    @classmethod
    def caminho_modelo(cls, id_modelo: str) -> str | None:
        """Retorna o caminho absoluto do executável do modelo caso exista em disco."""
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
        """Indica se o binário correspondente ao modelo já foi baixado."""
        return cls.caminho_modelo(id_modelo) is not None

    @classmethod
    def baixar_modelo(cls, id_modelo: str, progresso_cb=None, cancelado_cb=None) -> str:
        """Baixa o executável do modelo via streaming HTTP com salvamento atômico."""
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
