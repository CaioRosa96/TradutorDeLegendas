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
    def garantir_estrutura_glossarios(cls, filepath_global: str | None = None) -> str:
        """Garante que a pasta glossarios/ e o arquivo glossario.txt existam no diretório de execução.

        Quando executado via binário PyInstaller (--onefile), sincroniza automaticamente os
        glossários empacotados em DIRETORIO_RECURSOS (_MEIPASS) para DIRETORIO_EXECUCAO sem
        sobrescrever arquivos já customizados pelo usuário.
        """
        arq_global = filepath_global or cls.ARQUIVO_GLOSSARIO_PADRAO
        pasta_destino = cls.DIRETORIO_GLOSSARIOS

        try:
            os.makedirs(pasta_destino, exist_ok=True)
        except Exception:
            pass

        # 1. Inicializa ou copia o glossário global
        if not os.path.isfile(arq_global):
            origem_recurso_global = os.path.join(cls.DIRETORIO_RECURSOS, "glossario.txt")
            try:
                if (
                    os.path.isfile(origem_recurso_global)
                    and os.path.abspath(origem_recurso_global) != os.path.abspath(arq_global)
                ):
                    shutil.copy2(origem_recurso_global, arq_global)
                else:
                    with open(arq_global, "w", encoding="utf-8") as f:
                        f.write("# Dicionário / Glossário de Proteção\n")
                        f.write("# Adicione as palavras que você NÃO quer que o Google traduza errado.\n")
                        f.write("# Formato 1: Palavra Original = Palavra Destino\n")
                        f.write("# Formato 2: Apenas a Palavra (protege contra qualquer mudança)\n")
                        f.write("# Exemplos:\n")
                        f.write("# The Force=A Força\n")
                        f.write("# Hogwarts\n")
                        f.write("# Goku\n")
            except Exception:
                pass

        # 2. Copia glossários de animes empacotados em _MEIPASS (se ainda não existirem na pasta local)
        pasta_recurso_gloss = os.path.join(cls.DIRETORIO_RECURSOS, "glossarios")
        try:
            if (
                os.path.isdir(pasta_recurso_gloss)
                and os.path.abspath(pasta_recurso_gloss) != os.path.abspath(pasta_destino)
            ):
                for nome in os.listdir(pasta_recurso_gloss):
                    if nome.lower().endswith(".txt"):
                        orig = os.path.join(pasta_recurso_gloss, nome)
                        dest = os.path.join(pasta_destino, nome)
                        if os.path.isfile(orig) and not os.path.exists(dest):
                            shutil.copy2(orig, dest)
        except Exception:
            pass

        # 3. Garante arquivo de instruções LEIA_ME.txt na pasta local
        leia_me = os.path.join(pasta_destino, "LEIA_ME.txt")
        if not os.path.exists(leia_me):
            try:
                with open(leia_me, "w", encoding="utf-8") as f:
                    f.write("Coloque aqui dicionários específicos de animes (ex: Bleach.txt, One Piece.txt).\n")
                    f.write(
                        "Se o nome do vídeo que está sendo traduzido contiver o nome do arquivo, "
                        "este dicionário será carregado automaticamente junto com o global.\n"
                    )
            except Exception:
                pass

        return pasta_destino

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
