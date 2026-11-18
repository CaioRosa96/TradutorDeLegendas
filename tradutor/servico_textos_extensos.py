"""Serviço de tradução assíncrona de textos extensos com orçamento dinâmico.

Projetado para integração com o Omnime e tradução de sinopses e descrições,
com controle de concorrência, suporte a cache e fallback resiliente.
"""

from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Callable, Sequence

from .contratos import CacheTraducaoPort
from .idiomas import Idiomas
from .particionador_texto import ParticionadorTexto
from .tradutores.base import ExcecaoDisjuntorAberto, ITradutor


class TradutorTextosExtensos:
    """Traduz textos extensos integrando motor de tradução, cache e particionamento."""

    def __init__(
        self,
        tradutor: ITradutor | None = None,
        cache: CacheTraducaoPort | None = None,
        limite_caracteres: int = 3500,
        max_concorrente: int = 3,
        logger: Callable[[str], None] | None = None,
        is_cancelled_callback: Callable[[], bool] | None = None,
        progress_callback: Callable[[int, int], None] | None = None,
        particionador: ParticionadorTexto | None = None,
        engine: ITradutor | None = None,
    ) -> None:
        motor = tradutor or engine
        if motor is None:
            raise ValueError("Um motor de tradução (ITradutor) deve ser fornecido.")
        self._tradutor = motor
        self._cache = cache
        self._limite_caracteres = max(1, limite_caracteres)
        self._max_concorrente = max(1, max_concorrente)
        self._logger = logger or (lambda msg: None)
        self._is_cancelled = is_cancelled_callback or (lambda: False)
        self._progress_callback = progress_callback or (lambda atual, total: None)
        self._particionador = particionador or ParticionadorTexto(self._limite_caracteres)

    @property
    def tradutor(self) -> ITradutor:
        """Motor de tradução injetado."""
        return self._tradutor

    @property
    def engine(self) -> ITradutor:
        """Alias para o motor de tradução injetado."""
        return self._tradutor

    @property
    def cache(self) -> CacheTraducaoPort | None:
        """Porta de cache opcional injetada."""
        return self._cache

    @property
    def limite_caracteres(self) -> int:
        """Orçamento máximo de caracteres por requisição."""
        return self._limite_caracteres

    def particionar(self, texto: str) -> list[str]:
        """Particiona um texto em blocos respeitando o limite de caracteres."""
        return self._particionador.particionar(texto)

    async def traduzir(
        self,
        texto: str,
        idioma_origem: str = "auto",
        idioma_destino: str = "pt",
        *,
        src_lang: str | None = None,
        dest_lang: str | None = None,
    ) -> str:
        """Traduz um texto extenso de forma assíncrona preservando formatação."""
        if not texto or not texto.strip():
            return texto

        src_efetivo = src_lang if src_lang is not None else idioma_origem
        dest_efetivo = dest_lang if dest_lang is not None else idioma_destino

        dest_norm = Idiomas.normalizar_destino(dest_efetivo) or dest_efetivo
        src_norm = Idiomas.para_google(src_efetivo) or src_efetivo

        blocos = self.particionar(texto)
        if not blocos:
            return texto

        if self._is_cancelled():
            return texto

        loop = asyncio.get_running_loop()
        semaforo = asyncio.Semaphore(self._max_concorrente)
        total_blocos = len(blocos)
        concluidos = 0

        cache_map = self._obter_cache_em_lote(blocos, src_norm, dest_norm)

        async def _processar_bloco(bloco: str) -> str:
            nonlocal concluidos
            if self._is_cancelled():
                return bloco

            if bloco in cache_map:
                concluidos += 1
                self._progress_callback(concluidos, total_blocos)
                return cache_map[bloco]

            cached = self._obter_cache_unitario(bloco, src_norm, dest_norm)
            if cached is not None:
                concluidos += 1
                self._progress_callback(concluidos, total_blocos)
                return cached

            async with semaforo:
                if self._is_cancelled():
                    return bloco
                traduzido, sucesso_total = await self._executar_com_fallback(
                    loop, bloco, src_norm, dest_norm
                )
                if sucesso_total and not self._is_cancelled() and traduzido != bloco:
                    self._persistir_cache_unitario(bloco, src_norm, dest_norm, traduzido)

                concluidos += 1
                self._progress_callback(concluidos, total_blocos)
                return traduzido

        tasks = [_processar_bloco(b) for b in blocos]
        blocos_traduzidos = await asyncio.gather(*tasks)

        return self._particionador.recompor_texto(texto, blocos, blocos_traduzidos)

    def _obter_cache_em_lote(
        self, blocos: Sequence[str], src_lang: str, dest_lang: str
    ) -> dict[str, str]:
        """Consulta cache em lote de forma segura."""
        if self._cache is not None and hasattr(self._cache, "get_many"):
            try:
                return self._cache.get_many(blocos, src_lang, dest_lang) or {}
            except Exception as e:
                self._logger(f"[Aviso] Falha ao consultar cache em lote: {e}")
        return {}

    def _obter_cache_unitario(
        self, bloco: str, src_lang: str, dest_lang: str
    ) -> str | None:
        """Consulta cache unitário de forma segura."""
        if self._cache is not None:
            try:
                return self._cache.get(bloco, src_lang, dest_lang)
            except Exception as e:
                self._logger(f"[Aviso] Falha ao consultar cache: {e}")
        return None

    def _persistir_cache_unitario(
        self, bloco: str, src_lang: str, dest_lang: str, traduzido: str
    ) -> None:
        """Salva no cache de forma defensiva."""
        if self._cache is not None:
            try:
                self._cache.put(bloco, src_lang, dest_lang, traduzido)
            except Exception as e:
                self._logger(f"[Aviso] Falha ao persistir no cache: {e}")

    async def _executar_com_fallback(
        self,
        loop: asyncio.AbstractEventLoop,
        bloco: str,
        src_lang: str,
        dest_lang: str,
    ) -> tuple[str, bool]:
        """Executa a tradução do bloco com fallback recursivo em caso de erro.

        Retorna tupla (texto_traduzido, sucesso_total) onde sucesso_total indica se
        todas as etapas e sub-blocos foram concluídos com sucesso sem falhas parciais.
        """
        try:
            trad = await loop.run_in_executor(
                None, self._tradutor.translate, bloco, src_lang, dest_lang
            )
            return trad, True
        except ExcecaoDisjuntorAberto:
            raise
        except Exception as e:
            self._logger(
                f"[Aviso] Falha na tradução de bloco ({len(bloco)} chars): {e}. Executando fallback..."
            )

        if self._is_cancelled():
            return bloco, False

        # Fallback resiliente: divide pelo delimitador hierárquico mais significativo
        for sep in self._particionador._DELIMITADORES:
            if not sep:
                continue
            if sep in bloco:
                sub_blocos = [p for p in bloco.split(sep) if p]
                if len(sub_blocos) > 1:
                    sub_traduzidos: list[str] = []
                    falha_parcial = False
                    for sb in sub_blocos:
                        if self._is_cancelled():
                            falha_parcial = True
                            sub_traduzidos.append(sb)
                            continue
                        try:
                            trad_sb = await loop.run_in_executor(
                                None, self._tradutor.translate, sb, src_lang, dest_lang
                            )
                            sub_traduzidos.append(trad_sb)
                        except ExcecaoDisjuntorAberto:
                            raise
                        except Exception:
                            falha_parcial = True
                            sub_traduzidos.append(sb)
                    recomposto = self._particionador.recompor_texto(bloco, sub_blocos, sub_traduzidos)
                    sucesso_total = not falha_parcial and not self._is_cancelled()
                    return recomposto, sucesso_total

        return bloco, False

    def traduzir_sincrono(
        self,
        texto: str,
        idioma_origem: str = "auto",
        idioma_destino: str = "pt",
        *,
        src_lang: str | None = None,
        dest_lang: str | None = None,
    ) -> str:
        """Executa a tradução síncrona aguardando a conclusão do pipeline."""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        coro = self.traduzir(
            texto,
            idioma_origem,
            idioma_destino,
            src_lang=src_lang,
            dest_lang=dest_lang,
        )

        if loop and loop.is_running():
            with ThreadPoolExecutor(max_workers=1) as pool:
                return pool.submit(asyncio.run, coro).result()
        return asyncio.run(coro)
