import os
import shutil
import sys


class GerenciadorConfig:
    """Configurações globais e detecção externa de ferramentas de vídeo (MKVToolNix e FFmpeg)."""

    TAMANHO_LOTE = 40
    MAX_CONCORRENTE = 5
    MAX_RETENTATIVAS = 3
    PAUSA_FALLBACK_SEGUNDOS = 0.5

    # Diretório onde o executável ou script está rodando (para dados persistentes e binários locais)
    DIRETORIO_EXECUCAO = (
        os.path.dirname(sys.executable)
        if getattr(sys, "frozen", False)
        else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )

    # Diretório onde os recursos sob licença MIT (locales, glossários) foram extraídos
    DIRETORIO_RECURSOS = (
        getattr(sys, "_MEIPASS", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        if getattr(sys, "frozen", False)
        else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )

    DIRETORIO_PROJETO = DIRETORIO_EXECUCAO
    LOCAL_MKVTOOLNIX = os.path.join(DIRETORIO_EXECUCAO, "mkvtoolnix")
    SYSTEM_MKVTOOLNIX = r"C:\Program Files\MKVToolNix"
    SYSTEM_MKVTOOLNIX_X86 = r"C:\Program Files (x86)\MKVToolNix"
    ARQUIVO_GLOSSARIO_PADRAO = os.path.join(DIRETORIO_EXECUCAO, "glossario.txt")
    DIRETORIO_GLOSSARIOS = os.path.join(DIRETORIO_EXECUCAO, "glossarios")

    @classmethod
    def validar_pasta_mkvtoolnix(cls, caminho: str) -> str | None:
        """Verifica se a pasta informada (ou subpasta bin/mkvtoolnix) contém mkvmerge.exe e mkvextract.exe."""
        if not caminho:
            return None
        caminho_limpo = os.path.abspath(caminho.strip())
        if os.path.isfile(caminho_limpo):
            caminho_limpo = os.path.dirname(caminho_limpo)

        subpastas_candidatas = [
            caminho_limpo,
            os.path.join(caminho_limpo, "bin"),
            os.path.join(caminho_limpo, "mkvtoolnix"),
        ]
        for pasta in subpastas_candidatas:
            mkvmerge = os.path.join(pasta, "mkvmerge.exe")
            mkvextract = os.path.join(pasta, "mkvextract.exe")
            if os.path.isfile(mkvmerge) and os.path.isfile(mkvextract):
                return pasta
        return None

    @classmethod
    def get_mkvtoolnix_path(cls) -> str:
        """Retorna o caminho do MKVToolNix priorizando: pasta customizada do usuário, pasta local e sistema."""
        try:
            from .config_usuario import PreferenciasUsuario

            custom_path = PreferenciasUsuario.obter("mkvtoolnix_custom", "")
            resolvido_custom = cls.validar_pasta_mkvtoolnix(custom_path)
            if resolvido_custom:
                return resolvido_custom
        except Exception:
            pass

        for sub in ("mkvtoolnix", "bin"):
            local_externo = os.path.join(cls.DIRETORIO_EXECUCAO, sub)
            resolvido_local = cls.validar_pasta_mkvtoolnix(local_externo)
            if resolvido_local:
                return resolvido_local

        for pasta_sis in (cls.SYSTEM_MKVTOOLNIX, cls.SYSTEM_MKVTOOLNIX_X86):
            resolvido_sis = cls.validar_pasta_mkvtoolnix(pasta_sis)
            if resolvido_sis:
                return resolvido_sis

        no_path = shutil.which("mkvmerge")
        if no_path:
            resolvido_path = cls.validar_pasta_mkvtoolnix(os.path.dirname(no_path))
            if resolvido_path:
                return resolvido_path

        return cls.SYSTEM_MKVTOOLNIX

    @classmethod
    def get_mkv_bins(cls) -> tuple[str, str]:
        """Retorna tupla (mkvmerge, mkvextract) com caminhos absolutos."""
        path = cls.get_mkvtoolnix_path()
        return os.path.join(path, "mkvmerge.exe"), os.path.join(path, "mkvextract.exe")

    @classmethod
    def check_dependencies(cls) -> bool:
        """Verifica se mkvmerge e mkvextract existem e são acessíveis no sistema."""
        mkvmerge, mkvextract = cls.get_mkv_bins()
        return os.path.isfile(mkvmerge) and os.path.isfile(mkvextract)

    @classmethod
    def get_ffmpeg_path(cls) -> str | None:
        """Localiza o executável ffmpeg priorizando pasta customizada, pasta local e PATH do sistema."""
        pastas_custom = []
        try:
            from .config_usuario import PreferenciasUsuario

            for chave in ("ffmpeg_custom", "mkvtoolnix_custom"):
                val = PreferenciasUsuario.obter(chave, "")
                if val:
                    pastas_custom.append(val.strip())
        except Exception:
            pass

        for custom in pastas_custom:
            if os.path.isfile(custom) and os.path.basename(custom).lower() == "ffmpeg.exe":
                return os.path.abspath(custom)
            for sub in ("", "bin", "mkvtoolnix"):
                candidato = os.path.join(custom, sub, "ffmpeg.exe") if sub else os.path.join(custom, "ffmpeg.exe")
                if os.path.isfile(candidato):
                    return os.path.abspath(candidato)

        for sub in ("bin", "mkvtoolnix"):
            candidato = os.path.join(cls.DIRETORIO_EXECUCAO, sub, "ffmpeg.exe")
            if os.path.isfile(candidato):
                return os.path.abspath(candidato)

        for padrao_sis in (r"C:\Program Files\ffmpeg\bin\ffmpeg.exe", r"C:\ffmpeg\bin\ffmpeg.exe"):
            if os.path.isfile(padrao_sis):
                return padrao_sis

        no_path = shutil.which("ffmpeg")
        return os.path.abspath(no_path) if no_path else None
