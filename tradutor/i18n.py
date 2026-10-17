"""Motor de internacionalização (i18n) desacoplado baseado em catálogos JSON.

Gerencia o carregamento sob demanda, cache em memória e fallback seguro
para todos os textos da interface gráfica, modais e diálogos do sistema.
"""

import json
import os
from .config_usuario import PreferenciasUsuario


class I18n:
    """Central leve de internacionalização com carregamento sob demanda de catálogos."""

    _idioma_ativo = "pt-br"
    _cache_locales = {}
    _diretorio_locales = os.path.join(os.path.dirname(os.path.abspath(__file__)), "locales")

    IDIOMAS_SUPORTADOS = {
        "pt-br": "Português (Brasil)",
        "en": "English (US)",
        "es": "Español",
        "ja": "日本語",
        "zh-cn": "中文 (简体)"
    }

    @classmethod
    def inicializar(cls):
        """Carrega o idioma salvo e pré-carrega o catálogo ativo e o fallback."""
        cls._idioma_ativo = PreferenciasUsuario.obter("idioma_app", "pt-br")
        cls._carregar_catalogo("pt-br")
        if cls._idioma_ativo != "pt-br":
            cls._carregar_catalogo(cls._idioma_ativo)

    @classmethod
    def obter_idioma(cls) -> str:
        """Retorna o código do idioma ativo (ex: 'pt-br', 'en', 'zh-cn')."""
        return cls._idioma_ativo

    @classmethod
    def definir_idioma(cls, codigo: str):
        """Altera o idioma ativo e persiste nas preferências de usuário."""
        if codigo in cls.IDIOMAS_SUPORTADOS:
            cls._idioma_ativo = codigo
            cls._carregar_catalogo(codigo)
            PreferenciasUsuario.definir("idioma_app", codigo)

    @classmethod
    def t(cls, chave: str, default: str = "") -> str:
        """Retorna o texto traduzido para a chave informada com fallback seguro."""
        catalogo_ativo = cls._carregar_catalogo(cls._idioma_ativo)
        if chave in catalogo_ativo:
            return catalogo_ativo[chave]

        catalogo_fallback = cls._carregar_catalogo("pt-br")
        return catalogo_fallback.get(chave, default or chave)

    @classmethod
    def _carregar_catalogo(cls, codigo: str) -> dict:
        """Carrega e armazena em cache o catálogo JSON do idioma informado."""
        if codigo in cls._cache_locales:
            return cls._cache_locales[codigo]

        caminho = os.path.join(cls._diretorio_locales, f"{codigo}.json")
        if os.path.exists(caminho):
            try:
                with open(caminho, "r", encoding="utf-8") as f:
                    dados = json.load(f)
                    cls._cache_locales[codigo] = dados
                    return dados
            except Exception:
                pass

        return cls._cache_locales.get("pt-br", {})
