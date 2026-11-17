"""Contratos de domínio compartilhados entre escudo, serviço de tradução, cache e orquestração."""
from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Mapping, Protocol, Sequence, runtime_checkable


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


@dataclass(frozen=True, slots=True)
class ConfiguracaoPipeline:
    """Configuração imutável para a execução do pipeline de processamento."""

    idioma_destino: str = "pt"
    idioma_origem: str = "auto"
    politica_sobrescrita: str = "perguntar"
    formato_saida_video: str = "converter_mkv"
    manter_legenda_externa: bool = False
    habilitar_whisper: bool = False
    forcar_whisper: bool = False
    modelo_whisper_padrao: str = "small"


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

    def put_many(
        self,
        itens: Mapping[str, str] | Sequence[tuple[str, str, str, str]],
        src_lang: str = "auto",
        dest_lang: str = "pt",
    ) -> None: ...


@runtime_checkable
class InteracaoUsuarioPort(Protocol):
    """Porta formal para interação com o usuário (diálogos, confirmações e progresso)."""

    def log(self, mensagem: str) -> None: ...

    def progresso(self, atual: int, total: int) -> None: ...

    def confirmar_sobrescrita(self, nomes_arquivos: str) -> bool: ...

    def escolher_formato_saida(self, nome_arquivo: str, extensao: str) -> str: ...

    def solicitar_dependencias(self) -> bool: ...

    def autorizar_whisper(self, nome_arquivo: str) -> bool: ...

    def ao_concluir(self) -> None: ...
