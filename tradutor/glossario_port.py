"""Portas e adaptadores para busca de entidades e enriquecimento de glossários."""
from __future__ import annotations

import os
from typing import Mapping, Protocol, Sequence, runtime_checkable

from .anilist import (
    buscar_anime,
    buscar_personagens,
    extrair_nomes_ordenados,
    limpar_nome_anime,
    salvar_glossario_arquivo,
)


@runtime_checkable
class BuscadorEntidadesPort(Protocol):
    """Porta do serviço de busca de entidades e nomes próprios para enriquecimento de glossários."""

    def buscar_nomes_proprios(self, titulo_obra: str) -> list[str]:
        """Busca nomes próprios e entidades associadas ao título da obra ou arquivo de vídeo.

        Args:
            titulo_obra: Título da obra ou nome do arquivo de vídeo.

        Returns:
            Lista de nomes próprios em ordem de relevância ou comprimento decrescente.
        """
        ...


class AdaptadorAniListGraphQL(BuscadorEntidadesPort):
    """Adaptador de busca de entidades que consome a API GraphQL pública do AniList."""

    def __init__(self, pasta_destino: str | None = None, persistir_arquivo: bool = False) -> None:
        """Inicializa o adaptador AniList.

        Args:
            pasta_destino: Diretório opcional para persistir o glossário gerado em disco.
            persistir_arquivo: Se True e pasta_destino informada, salva os termos encontrados em arquivo.
        """
        self.pasta_destino = pasta_destino
        self.persistir_arquivo = persistir_arquivo

    def buscar_nomes_proprios(self, titulo_obra: str) -> list[str]:
        """Busca nomes próprios no AniList a partir do título da obra ou nome de arquivo.

        Delega a resolução do título para limpar_nome_anime, a consulta para
        buscar_anime e buscar_personagens, e a ordenação para extrair_nomes_ordenados.
        """
        if not titulo_obra:
            return []

        nome_limpo = limpar_nome_anime(titulo_obra)
        if not nome_limpo:
            nome_limpo = titulo_obra.strip()
        if not nome_limpo:
            return []

        try:
            animes = buscar_anime(nome_limpo)
            if not animes:
                return []

            anime = animes[0]
            anime_id = anime.get("id")
            if not anime_id:
                return []

            personagens = buscar_personagens(anime_id)
            if not personagens:
                return []

            nomes = extrair_nomes_ordenados(personagens)

            if self.persistir_arquivo and self.pasta_destino and nomes:
                try:
                    titulo_info = anime.get("title", {})
                    titulo = titulo_info.get("romaji") or titulo_info.get("english") or nome_limpo
                    salvar_glossario_arquivo(
                        pasta_destino=self.pasta_destino,
                        titulo=titulo,
                        anime_id=anime_id,
                        nome_limpo=nome_limpo,
                        nomes=nomes,
                    )
                except Exception:
                    pass

            return nomes
        except Exception:
            return []


class AdaptadorMemoriaGlossario(BuscadorEntidadesPort):
    """Adaptador em memória para injeção direta de entidades pré-carregadas pelo Omnime ou testes."""

    def __init__(
        self,
        entidades: Mapping[str, Sequence[str]] | Sequence[str] | None = None,
    ) -> None:
        """Inicializa o adaptador em memória.

        Args:
            entidades: Dicionário mapeando título/chave da obra para lista de termos,
                       ou sequência direta de termos a serem sempre retornados.
        """
        self._mapa_obras: dict[str, list[str]] = {}
        self._termos_diretos: list[str] = []

        if entidades is None:
            return

        if isinstance(entidades, Mapping):
            for chave, termos in entidades.items():
                self._mapa_obras[chave.strip().lower()] = list(termos)
        elif isinstance(entidades, (list, tuple, set)):
            self._termos_diretos = list(entidades)

    def cadastrar_obra(self, titulo_obra: str, nomes: Sequence[str]) -> None:
        """Registra termos associados a uma obra específica."""
        self._mapa_obras[titulo_obra.strip().lower()] = list(nomes)

    def buscar_nomes_proprios(self, titulo_obra: str) -> list[str]:
        """Busca nomes próprios na memória interna.

        Retorna a lista de entidades vinculadas ao título ou termos diretos configurados.
        """
        if not titulo_obra:
            return list(self._termos_diretos)

        titulo_limpo = titulo_obra.strip().lower().replace('_', ' ').replace('-', ' ')

        for chave, termos in self._mapa_obras.items():
            chave_norm = chave.replace('_', ' ').replace('-', ' ')
            if chave_norm == titulo_limpo:
                return list(termos)

        for chave, termos in self._mapa_obras.items():
            chave_norm = chave.replace('_', ' ').replace('-', ' ')
            if chave_norm in titulo_limpo or titulo_limpo in chave_norm:
                return list(termos)

        if self._termos_diretos:
            return list(self._termos_diretos)

        return []
