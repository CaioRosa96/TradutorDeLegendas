"""Gerenciamento persistente de preferencias e configuracoes do usuario."""

import json
import os
from .config import GerenciadorConfig


class PreferenciasUsuario:
    """Carrega e persiste preferencias locais do usuario em preferencias.json."""

    ARQUIVO_PREFERENCIAS = os.path.join(GerenciadorConfig.DIRETORIO_PROJETO, "preferencias.json")

    PADRAO = {
        "idioma_app": "pt-br",
        "tema": "escuro",
        "tocar_som": True,
        "abrir_pasta_ao_concluir": False,
        "politica_sobrescrita": "perguntar",  # "perguntar", "sobrescrever", "pular"
        "mkvtoolnix_custom": ""
    }

    _dados = None

    @classmethod
    def carregar(cls) -> dict:
        """Carrega as preferencias do arquivo JSON ou inicializa com valores padrao."""
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
        """Salva as preferencias no arquivo JSON local."""
        if novos_dados:
            cls.carregar().update(novos_dados)
        try:
            with open(cls.ARQUIVO_PREFERENCIAS, "w", encoding="utf-8") as f:
                json.dump(cls.carregar(), f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[ERRO] Falha ao salvar preferencias.json: {e}")

    @classmethod
    def obter(cls, chave: str, padrao=None):
        """Obtem o valor de uma preferencia especifica."""
        return cls.carregar().get(chave, padrao if padrao is not None else cls.PADRAO.get(chave))

    @classmethod
    def definir(cls, chave: str, valor):
        """Atualiza e persiste imediatamente uma preferencia."""
        cls.carregar()[chave] = valor
        cls.salvar()
