import os
import sys


class GerenciadorConfig:
    """Configurações globais e detecção de dependências do projeto."""

    TAMANHO_LOTE = 40
    MAX_CONCORRENTE = 5
    MAX_RETENTATIVAS = 3

    # Diretório onde o executável ou script está rodando (para dados persistentes)
    DIRETORIO_EXECUCAO = (
        os.path.dirname(sys.executable)
        if getattr(sys, "frozen", False)
        else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )

    # Diretório onde os recursos e binários embutidos foram extraídos
    DIRETORIO_RECURSOS = (
        getattr(sys, "_MEIPASS", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        if getattr(sys, "frozen", False)
        else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )

    DIRETORIO_PROJETO = DIRETORIO_EXECUCAO
    LOCAL_MKVTOOLNIX = os.path.join(DIRETORIO_EXECUCAO, "mkvtoolnix")
    SYSTEM_MKVTOOLNIX = r"C:\Program Files\MKVToolNix"
    ARQUIVO_GLOSSARIO_PADRAO = os.path.join(DIRETORIO_EXECUCAO, "glossario.txt")
    DIRETORIO_GLOSSARIOS = os.path.join(DIRETORIO_EXECUCAO, "glossarios")

    @classmethod
    def get_mkvtoolnix_path(cls):
        """Retorna o caminho do MKVToolNix, priorizando pasta customizada, local externa, embutida e sistema."""
        try:
            from .config_usuario import PreferenciasUsuario
            custom_path = PreferenciasUsuario.obter("mkvtoolnix_custom", "")
            if custom_path and os.path.exists(os.path.join(custom_path, "mkvmerge.exe")):
                return custom_path
        except Exception:
            pass

        local_externo = os.path.join(cls.DIRETORIO_EXECUCAO, "mkvtoolnix")
        if os.path.exists(os.path.join(local_externo, "mkvmerge.exe")):
            return local_externo

        local_embutido = os.path.join(cls.DIRETORIO_RECURSOS, "mkvtoolnix")
        if os.path.exists(os.path.join(local_embutido, "mkvmerge.exe")):
            return local_embutido

        return cls.SYSTEM_MKVTOOLNIX

    @classmethod
    def get_mkv_bins(cls):
        """Retorna tupla (mkvmerge, mkvextract) com caminhos absolutos."""
        path = cls.get_mkvtoolnix_path()
        return os.path.join(path, "mkvmerge.exe"), os.path.join(path, "mkvextract.exe")

    @classmethod
    def check_dependencies(cls):
        """Verifica se mkvmerge e mkvextract existem no sistema."""
        mkvmerge, mkvextract = cls.get_mkv_bins()
        return os.path.exists(mkvmerge) and os.path.exists(mkvextract)

