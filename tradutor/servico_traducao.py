import os
import re
import time
import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor

import pysubs2

from .config import GerenciadorConfig
from .glossario import GerenciadorGlossario
from .idiomas import Idiomas
from .cache import CacheTraducoes
from .contratos import LinhaProtegida, ResultadoTraducaoLinha
from .tradutores import ExcecaoDisjuntorAberto


class ServicoTraducao:
    """Serviço de tradução assíncrona de legendas via Google Translate.

    Processa legendas em lotes concorrentes, com fallback sequencial
    quando a API retorna quantidade inconsistente de linhas.
    """

    def __init__(
        self,
        logger,
        progress_callback,
        is_cancelled_callback=None,
        engine=None,
        video_filename=None,
        habilitar_auto_alimentar=None,
    ):
        self._logger = logger
        self._progress_callback = progress_callback
        self._is_cancelled = is_cancelled_callback or (lambda: False)
        self._linhas_processadas = 0
        self._total_linhas = 0
        if habilitar_auto_alimentar is None:
            try:
                from .config_usuario import PreferenciasUsuario
                habilitar_auto_alimentar = bool(PreferenciasUsuario.obter("auto_alimentar_anilist", True))
            except Exception:
                habilitar_auto_alimentar = False
        self._glossary = GerenciadorGlossario(
            video_filename=video_filename,
            habilitar_auto_alimentar=habilitar_auto_alimentar,
        )
        self._cache = CacheTraducoes()
        
        if engine is None:
            raise ValueError("Um motor de tradução (ITradutor) deve ser fornecido.")
        self._engine = engine
        self._linhas_traduzidas_sucesso = 0
        self._disjuntor_disparado = False
        self._lock_stats = threading.Lock()

    @staticmethod
    def _limpar_quebras(texto):
        """Restaura marcadores de quebra de linha \\N e \\n removendo espaços injetados."""
        texto = re.sub(r'\s*\\\s*N\s*', r'\\N', texto)
        texto = re.sub(r'\s*\\\s*n\s*', r'\\n', texto)
        return texto

    @staticmethod
    def _map_lang(iso_639_2):
        """Mapeia os códigos de idioma do MKV para o Google Translate."""
        return Idiomas.para_google(iso_639_2)

    def _salvar_cache_seguro(self, texto: str, src_lang: str, dest_lang: str, traducao: str) -> None:
        """Persiste uma tradução unitária no cache em modo best-effort sem abortar o lote."""
        if "TKGLOSS" in texto or "TKGLOSS" in traducao:
            return
        try:
            self._cache.put(texto, src_lang, dest_lang, traducao)
        except Exception as e:
            self._logger(f"[Aviso] Falha ao gravar no cache local (ignorada): {e}")

    def _salvar_lote_cache_seguro(self, itens: dict[str, str], src_lang: str, dest_lang: str) -> None:
        """Persiste múltiplas traduções no cache em modo best-effort sem reverter legendas."""
        if not itens or not hasattr(self._cache, "put_many"):
            return
        itens_limpos = {
            k: v for k, v in itens.items()
            if "TKGLOSS" not in k and "TKGLOSS" not in v
        }
        if not itens_limpos:
            return
        try:
            self._cache.put_many(itens_limpos, src_lang, dest_lang)
        except Exception as e:
            self._logger(f"[Aviso] Falha ao gravar lote no cache local (ignorada): {e}")

    async def _traduzir_lote(self, executor, semaforo, lote_indices, subs, pbar_lock, src_lang="auto", dest_lang="pt"):
        """Traduz um lote de linhas de legenda de forma assíncrona."""
        if self._is_cancelled():
            return

        loop = asyncio.get_running_loop()

        textos_preparados = []
        for idx in lote_indices:
            texto = subs[idx].text.replace("\r\n", r"\N").replace("\n", r"\N")
            texto = texto.replace(r"\N", " \\N ").replace(r"\n", " \\n ")
            textos_preparados.append(texto)

        bloco = "\n".join(textos_preparados)
        payload_bloco = self._glossary.proteger(bloco, id_linha=0)
        bloco_protegido = payload_bloco.texto_mascarado

        async with semaforo:
            if self._is_cancelled():
                return
            try:
                # 1. Busca no Cache Local (Nível 1: Bloco Inteiro)
                traduzido = self._cache.get(bloco_protegido, src_lang, dest_lang)
                payloads_linhas = None

                if not traduzido:
                    # Nível 2: Verifica linhas cacheadas individualmente via get_many
                    payloads_linhas = [
                        self._glossary.proteger(t, id_linha=idx)
                        for idx, t in zip(lote_indices, textos_preparados)
                    ]
                    chaves_linhas = [p.texto_mascarado for p in payloads_linhas]
                    cache_parcial = getattr(self._cache, "get_many", lambda *_: {})(
                        chaves_linhas, src_lang, dest_lang
                    )
                    if not isinstance(cache_parcial, dict):
                        cache_parcial = {}

                    if cache_parcial and all(c in cache_parcial for c in chaves_linhas):
                        for idx, p_linha in zip(lote_indices, payloads_linhas):
                            r_cached = cache_parcial[p_linha.texto_mascarado]
                            r_rest = self._glossary.restaurar(r_cached, p_linha)
                            subs[idx].text = self._limpar_quebras(r_rest.strip())
                        with self._lock_stats:
                            self._linhas_traduzidas_sucesso += len(lote_indices)
                        with pbar_lock:
                            self._linhas_processadas += len(lote_indices)
                            self._progress_callback(self._linhas_processadas, self._total_linhas)
                        return

                    if cache_parcial:
                        pendentes = []
                        acertos_parciais = 0
                        for idx, p_linha in zip(lote_indices, payloads_linhas):
                            if p_linha.texto_mascarado in cache_parcial:
                                r_cached = cache_parcial[p_linha.texto_mascarado]
                                r_rest = self._glossary.restaurar(r_cached, p_linha)
                                subs[idx].text = self._limpar_quebras(r_rest.strip())
                                acertos_parciais += 1
                            else:
                                pendentes.append((idx, p_linha))

                        if pendentes:
                            try:
                                sub_bloco = "\n".join(p.texto_mascarado for _, p in pendentes)
                                sub_trad = await loop.run_in_executor(
                                    executor, self._engine.translate, sub_bloco, src_lang, dest_lang
                                )
                                sub_linhas = sub_trad.split("\n")
                                if len(sub_linhas) == len(pendentes) + 1 and not sub_linhas[-1].strip():
                                    sub_linhas = sub_linhas[:-1]
                                if len(sub_linhas) == len(pendentes):
                                    novos_lote = {}
                                    for (idx, p_linha), linha_bruta in zip(pendentes, sub_linhas):
                                        r_rest = self._glossary.restaurar(linha_bruta, p_linha)
                                        f_limpa = self._limpar_quebras(r_rest.strip())
                                        subs[idx].text = f_limpa
                                        if not p_linha.possui_tokens and p_linha.texto_mascarado:
                                            novos_lote[p_linha.texto_mascarado] = f_limpa
                                    self._salvar_lote_cache_seguro(novos_lote, src_lang, dest_lang)
                                    with self._lock_stats:
                                        self._linhas_traduzidas_sucesso += len(lote_indices)
                                    with pbar_lock:
                                        self._linhas_processadas += len(lote_indices)
                                        self._progress_callback(self._linhas_processadas, self._total_linhas)
                                    return
                            except ExcecaoDisjuntorAberto:
                                with self._lock_stats:
                                    self._disjuntor_disparado = True
                                    self._linhas_traduzidas_sucesso += acertos_parciais
                                for idx_pend, p_pend in pendentes:
                                    subs[idx_pend].text = self._limpar_quebras(p_pend.texto_original)
                                with pbar_lock:
                                    self._linhas_processadas += len(lote_indices)
                                    self._progress_callback(self._linhas_processadas, self._total_linhas)
                                return
                            except Exception as e:
                                if "circuit breaker" in str(e).lower() or "disjuntor" in str(e).lower():
                                    with self._lock_stats:
                                        self._disjuntor_disparado = True
                                        self._linhas_traduzidas_sucesso += acertos_parciais
                                    for idx_pend, p_pend in pendentes:
                                        subs[idx_pend].text = self._limpar_quebras(p_pend.texto_original)
                                    with pbar_lock:
                                        self._linhas_processadas += len(lote_indices)
                                        self._progress_callback(self._linhas_processadas, self._total_linhas)
                                    return

                            # Fallback restrito apenas aos itens pendentes (preserva acertos_parciais)
                            with self._lock_stats:
                                self._linhas_traduzidas_sucesso += acertos_parciais
                            for pos_p, (idx_pend, p_pend) in enumerate(pendentes):
                                if self._is_cancelled():
                                    for rem_idx, rem_p in pendentes[pos_p:]:
                                        subs[rem_idx].text = self._limpar_quebras(rem_p.texto_original)
                                    break
                                try:
                                    r_pend = await loop.run_in_executor(
                                        executor, self._engine.translate, p_pend.texto_mascarado, src_lang, dest_lang
                                    )
                                except ExcecaoDisjuntorAberto:
                                    with self._lock_stats:
                                        self._disjuntor_disparado = True
                                    for rem_idx, rem_p in pendentes[pos_p:]:
                                        subs[rem_idx].text = self._limpar_quebras(rem_p.texto_original)
                                    break
                                except Exception:
                                    subs[idx_pend].text = self._limpar_quebras(p_pend.texto_original)
                                    continue
                                if not p_pend.possui_tokens:
                                    self._salvar_cache_seguro(p_pend.texto_mascarado, src_lang, dest_lang, r_pend)
                                r_rest_pend = self._glossary.restaurar(r_pend, p_pend)
                                subs[idx_pend].text = self._limpar_quebras(r_rest_pend)
                                with self._lock_stats:
                                    self._linhas_traduzidas_sucesso += 1
                                pausa = getattr(GerenciadorConfig, "PAUSA_FALLBACK_SEGUNDOS", 0.5)
                                await asyncio.sleep(pausa)

                            with pbar_lock:
                                self._linhas_processadas += len(lote_indices)
                                self._progress_callback(self._linhas_processadas, self._total_linhas)
                            return

                    # 2. Se não existir, vai na Rede via Engine injetada
                    traduzido = await loop.run_in_executor(executor, self._engine.translate, bloco_protegido, src_lang, dest_lang)
                    # 3. Salva no Cache (best-effort se não contiver tokens sintetizados)
                    if not payload_bloco.possui_tokens:
                        self._salvar_cache_seguro(bloco_protegido, src_lang, dest_lang, traduzido)
                    
                traduzido_restaurado = self._glossary.restaurar(traduzido, payload_bloco)
                
                linhas_retornadas = traduzido_restaurado.split("\n")
                if len(linhas_retornadas) == len(lote_indices) + 1 and not linhas_retornadas[-1].strip():
                    linhas_retornadas = linhas_retornadas[:-1]

                frases_limpas = [self._limpar_quebras(f.strip()) for f in linhas_retornadas]

                if len(frases_limpas) == len(lote_indices):
                    for i, idx in enumerate(lote_indices):
                        subs[idx].text = frases_limpas[i]
                    with self._lock_stats:
                        self._linhas_traduzidas_sucesso += len(lote_indices)
                    if payloads_linhas:
                        novos_individuais = {
                            p_linha.texto_mascarado: frase_limpa
                            for p_linha, frase_limpa in zip(payloads_linhas, frases_limpas)
                            if not p_linha.possui_tokens and p_linha.texto_mascarado
                        }
                        self._salvar_lote_cache_seguro(novos_individuais, src_lang, dest_lang)
                else:
                    self._logger("[Aviso] Dessincronia no lote. Executando fallback sequencial...")
                    for pos, (idx, texto) in enumerate(zip(lote_indices, textos_preparados)):
                        if self._is_cancelled():
                            for rem_idx, rem_texto in zip(lote_indices[pos:], textos_preparados[pos:]):
                                subs[rem_idx].text = self._limpar_quebras(rem_texto)
                            break

                        payload_linha = self._glossary.proteger(texto, id_linha=idx)
                        texto_protegido = payload_linha.texto_mascarado

                        r = self._cache.get(texto_protegido, src_lang, dest_lang)
                        consultou_rede = False
                        if not r:
                            try:
                                r = await loop.run_in_executor(
                                    executor, self._engine.translate, texto_protegido, src_lang, dest_lang
                                )
                                consultou_rede = True
                            except ExcecaoDisjuntorAberto:
                                with self._lock_stats:
                                    self._disjuntor_disparado = True
                                for rem_idx, rem_texto in zip(lote_indices[pos:], textos_preparados[pos:]):
                                    subs[rem_idx].text = self._limpar_quebras(rem_texto)
                                break
                            except Exception:
                                subs[idx].text = self._limpar_quebras(texto)
                                continue
                            if not payload_linha.possui_tokens:
                                self._salvar_cache_seguro(texto_protegido, src_lang, dest_lang, r)

                        r_restaurado = self._glossary.restaurar(r, payload_linha)
                        subs[idx].text = self._limpar_quebras(r_restaurado)
                        with self._lock_stats:
                            self._linhas_traduzidas_sucesso += 1
                        if self._is_cancelled():
                            for rem_idx, rem_texto in zip(lote_indices[pos + 1:], textos_preparados[pos + 1:]):
                                subs[rem_idx].text = self._limpar_quebras(rem_texto)
                            break
                        if consultou_rede:
                            pausa = getattr(GerenciadorConfig, "PAUSA_FALLBACK_SEGUNDOS", 0.5)
                            await asyncio.sleep(pausa)
            except Exception as e:
                if isinstance(e, ExcecaoDisjuntorAberto) or "circuit breaker" in str(e).lower() or "disjuntor" in str(e).lower():
                    with self._lock_stats:
                        self._disjuntor_disparado = True
                self._logger(f"[Erro Crítico] Lote ignorado. Motivo: {e}")
                for i, idx in enumerate(lote_indices):
                    subs[idx].text = self._limpar_quebras(textos_preparados[i])

        with pbar_lock:
            self._linhas_processadas += len(lote_indices)
            self._progress_callback(self._linhas_processadas, self._total_linhas)

    async def pipeline(self, origem, destino, idioma_preferido="auto", idioma_destino="pt", idioma_origem=None) -> bool:
        """Pipeline completo: carrega legenda, traduz todos os lotes e salva.

        Args:
            origem: Caminho do arquivo de legenda original.
            destino: Caminho do arquivo de legenda traduzida.
            idioma_preferido: Idioma de origem (ex: 'eng', 'fra').
            idioma_destino: Idioma de destino (ex: 'pt', 'en').
            idioma_origem: Alias opcional para idioma_preferido.

        Returns:
            bool: True se o arquivo foi traduzido e salvo com sucesso; False caso contrário.
        """
        dest_norm = Idiomas.normalizar_destino(idioma_destino)
        if not dest_norm:
            raise ValueError(f"Idioma de destino invalido ou nao suportado: '{idioma_destino}'")

        src_efetivo = idioma_origem or idioma_preferido or "auto"
        src_lang = self._map_lang(src_efetivo)
        
        self._logger(f"Carregando legendas de {os.path.basename(origem)}...")
        try:
            subs = pysubs2.load(origem)
        except Exception as e:
            self._logger(f"Erro ao carregar legenda com pysubs2: {e}")
            raise

        indices_map = [i for i, event in enumerate(subs) if event.text.strip()]
        self._total_linhas = len(indices_map)
        self._linhas_processadas = 0
        with self._lock_stats:
            self._linhas_traduzidas_sucesso = 0
            self._disjuntor_disparado = False

        self._logger(f"Total de diálogos encontrados: {self._total_linhas}")
        self._progress_callback(0, self._total_linhas)

        lotes = self._montar_lotes(subs, indices_map)
        semaforo = asyncio.Semaphore(GerenciadorConfig.MAX_CONCORRENTE)
        pbar_lock = threading.Lock()

        with ThreadPoolExecutor(max_workers=GerenciadorConfig.MAX_CONCORRENTE) as executor:
            tasks = [self._traduzir_lote(executor, semaforo, lote, subs, pbar_lock, src_lang, dest_norm) for lote in lotes]
            await asyncio.gather(*tasks)

        if self._is_cancelled():
            self._logger("[AVISO] Tradução abortada pelo usuário.")
            return False

        if self._disjuntor_disparado:
            self._logger("[ERRO CRÍTICO] Tradução interrompida: Circuit Breaker disparado.")
            raise ExcecaoDisjuntorAberto("Circuit Breaker ABERTO: Abortando para evitar banimentos.")

        if self._total_linhas > 0 and self._linhas_traduzidas_sucesso == 0:
            self._logger("[ERRO CRÍTICO] Falha total: nenhuma linha pôde ser traduzida com sucesso.")
            raise RuntimeError("Falha total na tradução: nenhuma linha foi traduzida.")

        self._logger("Salvando arquivo de legendas traduzido...")
        self._salvar_legenda_atomico(subs, destino)
        return True

    @staticmethod
    def _montar_lotes(subs, indices_map: list[int]) -> list[list[int]]:
        """Agrupa índices respeitando simultaneamente limite de linhas e orçamento de caracteres."""
        max_linhas = max(1, int(getattr(GerenciadorConfig, "TAMANHO_LOTE", 40)))
        max_chars = max(200, int(getattr(GerenciadorConfig, "LIMITE_CARACTERES_LOTE", 3500)))
        lotes: list[list[int]] = []
        lote_atual: list[int] = []
        chars_atual = 0

        for idx in indices_map:
            tam_linha = len(subs[idx].text) + 1
            if lote_atual and (len(lote_atual) >= max_linhas or chars_atual + tam_linha > max_chars):
                lotes.append(lote_atual)
                lote_atual = [idx]
                chars_atual = tam_linha
            else:
                lote_atual.append(idx)
                chars_atual += tam_linha

        if lote_atual:
            lotes.append(lote_atual)
        return lotes

    @staticmethod
    def _salvar_legenda_atomico(subs, destino: str) -> None:
        """Salva a legenda em arquivo temporário com a mesma extensão e promove via os.replace."""
        base_dest, ext_dest = os.path.splitext(destino)
        ext_efetiva = ext_dest if ext_dest else ".srt"
        destino_tmp = f"{base_dest}.tmp_{os.getpid()}_{threading.get_ident()}{ext_efetiva}"
        try:
            subs.save(destino_tmp)
            os.replace(destino_tmp, destino)
        except Exception:
            if os.path.isfile(destino_tmp):
                try:
                    os.remove(destino_tmp)
                except OSError:
                    pass
            raise
