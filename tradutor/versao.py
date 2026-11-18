"""Metadados centralizados de versão e edição da aplicação (Fonte Única da Verdade)."""
from __future__ import annotations

from typing import Final


class InfoVersao:
    """Contrato estático com informações de versão e edição do aplicativo.

    Inspirado no padrão de contratos/interfaces imutáveis do Java (Single Source
    of Truth), centraliza todas as informações de versão consumidas pela UI,
    Logger, Verificador de Atualizações e sistema de internacionalização (i18n).
    """

    NUMERO: Final[str] = "2.9.3"
    NOME_EDICAO: Final[str] = "Lossless Modern UI"

    @classmethod
    def tag(cls) -> str:
        """Retorna a tag de versão com prefixo 'v' (ex.: 'v2.9.1')."""
        return f"v{cls.NUMERO}"

    @classmethod
    def completa(cls) -> str:
        """Retorna a versão acompanhada do nome da edição (ex.: 'v2.9.1 (Lossless Modern UI)')."""
        return f"v{cls.NUMERO} ({cls.NOME_EDICAO})"

    @classmethod
    def titulo_janela(cls, nome_app: str) -> str:
        """Formata o título para a barra de título da janela principal (ex.: 'Tradutor de Legendas — v2.9.1')."""
        return f"{nome_app} — {cls.tag()}"

    @classmethod
    def formatar_rotulo_sobre(cls, template_i18n: str) -> str:
        """Formata o rótulo da aba Sobre a partir do template de idioma com {0} e nome da edição."""
        texto_versao = template_i18n.format(cls.NUMERO)
        return f"{texto_versao} ({cls.NOME_EDICAO})"
