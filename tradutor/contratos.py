"""Contratos de domínio compartilhados entre escudo, serviço de tradução e cache."""
from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Mapping, Protocol, runtime_checkable


@dataclass(frozen=True, slots=True)
class LinhaProtegida:
    """Value Object que vincula o texto original ao texto mascarado e aos seus tokens.

    O `mapa_tokens` é copiado para um `MappingProxyType`, impedindo que alterações
    no dicionário de origem ou no mapa exposto corrompam a restauração posterior.
    """

    id_linha: int
    texto_original: str
    texto_mascarado: str
    mapa_tokens: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "mapa_tokens", MappingProxyType(dict(self.mapa_tokens)))

    @property
    def possui_tokens(self) -> bool:
        return bool(self.mapa_tokens)


@dataclass(frozen=True, slots=True)
class ResultadoTraducaoLinha:
    """Resultado imutável da tradução de uma linha, alinhado pelo `id_linha` original."""

    id_linha: int
    texto_traduzido: str
    sucesso: bool
    origem_cache: bool = False
    usou_fallback: bool = False
    erro: str | None = None


@runtime_checkable
class EscudoTagsPort(Protocol):
    """Porta do escudo anti-alucinação (tags ASS/HTML e termos do glossário)."""

    def proteger(self, texto: str, id_linha: int = 0) -> LinhaProtegida: ...

    def restaurar(self, texto_traduzido: str, payload: LinhaProtegida) -> str: ...


@runtime_checkable
class CacheTraducaoPort(Protocol):
    """Porta para persistência e recuperação de cache de traduções."""

    def get(self, texto: str, src_lang: str, dest_lang: str) -> str | None: ...

    def put(self, texto: str, src_lang: str, dest_lang: str, texto_traduzido: str) -> None: ...

    def get_many(self, textos: Sequence[str], src_lang: str, dest_lang: str) -> dict[str, str]: ...

    def put_many(self, itens: Sequence[tuple[str, str, str, str]]) -> None: ...
