"""Gerenciamento persistente de preferencias e configuracoes do usuario."""

import json
import os
import sys
import threading
import time

_DIRETORIO_BASE = (
    os.path.dirname(sys.executable)
    if getattr(sys, "frozen", False)
    else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)


class PreferenciasUsuario:
    """Carrega e persiste preferencias locais do usuario em preferencias.json."""

    ARQUIVO_PREFERENCIAS = os.path.join(_DIRETORIO_BASE, "preferencias.json")

    PADRAO = {
        "idioma_app": "pt-br",
        "tema": "escuro",
        "tocar_som": True,
        "abrir_pasta_ao_concluir": False,
        "politica_sobrescrita": "perguntar",  # "perguntar", "sobrescrever", "pular"
        "formato_saida_video": "perguntar",  # "perguntar", "converter_mkv", "manter_original"
        "verificar_atualizacoes_ao_iniciar": True,
        "mkvtoolnix_custom": "",
        "ffmpeg_custom": "",
        "auto_alimentar_anilist": True,
        "transcricao_habilitada": False,
        "modelo_whisper": "small",  # "tiny", "small", "medium", "large-v3"
        "caminho_whisperfile": "",
        "forcar_transcricao": False,
    }

    _dados = None
    _lock = threading.RLock()

    @classmethod
    def carregar(cls) -> dict:
        """Carrega as preferencias do arquivo JSON ou inicializa com valores padrao."""
        with cls._lock:
            if cls._dados is not None:
                return cls._dados

            if os.path.exists(cls.ARQUIVO_PREFERENCIAS):
                try:
                    with open(cls.ARQUIVO_PREFERENCIAS, "r", encoding="utf-8") as f:
                        carregado = json.load(f)
                        cls._dados = {**cls.PADRAO, **carregado}
                        return cls._dados
                except Exception:
                    pass

            cls._dados = dict(cls.PADRAO)
            return cls._dados

    @classmethod
    def salvar(cls, novos_dados: dict = None):
        """Salva as preferencias no arquivo JSON local com escrita atomica."""
        with cls._lock:
            dados = cls.carregar()
            if novos_dados:
                dados.update(novos_dados)
            temp_path = f"{cls.ARQUIVO_PREFERENCIAS}.{os.getpid()}_{threading.get_ident()}.tmp"
            try:
                diretorio_pai = os.path.dirname(cls.ARQUIVO_PREFERENCIAS)
                if diretorio_pai:
                    os.makedirs(diretorio_pai, exist_ok=True)
                with open(temp_path, "w", encoding="utf-8") as f:
                    json.dump(dados, f, indent=2, ensure_ascii=False)
                    f.flush()
                    os.fsync(f.fileno())

                for tentativa in range(3):
                    try:
                        os.replace(temp_path, cls.ARQUIVO_PREFERENCIAS)
                        break
                    except PermissionError:
                        if tentativa < 2:
                            time.sleep(0.02)
                        else:
                            raise
            except Exception as e:
                if os.path.exists(temp_path):
                    try:
                        os.remove(temp_path)
                    except OSError:
                        pass
                print(f"[ERRO] Falha ao salvar preferencias.json: {e}")

    @classmethod
    def obter(cls, chave: str, padrao=None):
        """Obtem o valor de uma preferencia especifica."""
        with cls._lock:
            return cls.carregar().get(chave, padrao if padrao is not None else cls.PADRAO.get(chave))

    @classmethod
    def definir(cls, chave: str, valor):
        """Atualiza e persiste imediatamente uma preferencia."""
        with cls._lock:
            cls.carregar()[chave] = valor
            cls.salvar()
