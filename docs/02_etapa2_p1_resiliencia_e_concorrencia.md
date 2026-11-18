# Etapa 2 (P1): Resiliencia de Rede, Concorrencia e Fallback

**Instrucao para o Antigravity:** Aplique exatamente os blocos `SEARCH` / `REPLACE` abaixo apos confirmar que a Etapa 1 passou em todos os testes.

---

## 1. `tradutor/tradutores/google.py`
**Objetivo:** Permitir apenas 1 thread de sonda simultanea ao entrar em Half-Open (evitando Thundering Herd das 5 threads) e adicionar jitter leve no backoff exponencial.

### Alteracao 1.1: Controle de sonda Half-Open e jitter

#### SEARCH
```python
import threading
import time
from googletrans import Translator
from .base import ITradutor, ExcecaoDisjuntorAberto
from ..idiomas import Idiomas
from ..logger import app_logger

class MotorTraducaoGoogle(ITradutor):
    """
    Implementação Concreta para a API do Google Translate.
    Encapsula rate-limits, retentativas e possui Circuit Breaker thread-safe:
    se falhar 5 vezes seguidas, para de tentar por 60 segundos
    para evitar banimentos permanentes ou travamentos da thread.
    """
    
    def __init__(self, max_retries=3, failure_threshold=5, recovery_timeout=60):
        self._local = threading.local()
        self._max_retries = max_retries
        self._lock = threading.Lock()
        
        # Estado do Circuit Breaker
        self._failure_count = 0
        self._failure_threshold = failure_threshold
        self._last_failure_time = 0
        self._recovery_timeout = recovery_timeout
        self._is_open = False
```

#### REPLACE
```python
import random
import threading
import time
from googletrans import Translator
from .base import ITradutor, ExcecaoDisjuntorAberto
from ..idiomas import Idiomas
from ..logger import app_logger

class MotorTraducaoGoogle(ITradutor):
    """
    Implementação Concreta para a API do Google Translate.
    Encapsula rate-limits, retentativas e possui Circuit Breaker thread-safe:
    se falhar 5 vezes seguidas, para de tentar por 60 segundos
    para evitar banimentos permanentes ou travamentos da thread.
    """
    
    def __init__(self, max_retries=3, failure_threshold=5, recovery_timeout=60):
        self._local = threading.local()
        self._max_retries = max_retries
        self._lock = threading.Lock()
        
        # Estado do Circuit Breaker
        self._failure_count = 0
        self._failure_threshold = failure_threshold
        self._last_failure_time = 0
        self._recovery_timeout = recovery_timeout
        self._is_open = False
        self._sonda_half_open_ativa = False
```

### Alteracao 1.2: Metodos `_check_circuit`, `_record_failure` e `_record_success`

#### SEARCH
```python
    def _check_circuit(self):
        deve_logar_half_open = False
        with self._lock:
            if self._is_open:
                if time.time() - self._last_failure_time > self._recovery_timeout:
                    self._is_open = False
                    deve_logar_half_open = True
                else:
                    raise ExcecaoDisjuntorAberto("Circuit Breaker ABERTO: Abortando para evitar banimentos.")
        if deve_logar_half_open:
            app_logger.info("Circuit Breaker: Testando recuperação da API (Half-Open).")

    def _record_failure(self):
        deve_logar_erro = False
        with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.time()
            if self._failure_count >= self._failure_threshold:
                self._is_open = True
                deve_logar_erro = True
        if deve_logar_erro:
            app_logger.error(f"Circuit Breaker disparado! Atingiu {self._failure_threshold} falhas seguidas.")

    def _record_success(self):
        deve_logar_recuperacao = False
        with self._lock:
            if self._failure_count > 0:
                deve_logar_recuperacao = True
            self._failure_count = 0
            self._is_open = False
        if deve_logar_recuperacao:
            app_logger.info("Circuit Breaker: Conexão estabilizada. Resetando falhas.")
```

#### REPLACE
```python
    def _check_circuit(self):
        deve_logar_half_open = False
        with self._lock:
            if self._is_open:
                if time.time() - self._last_failure_time > self._recovery_timeout:
                    if self._sonda_half_open_ativa:
                        raise ExcecaoDisjuntorAberto("Circuit Breaker HALF-OPEN: Sonda em andamento.")
                    self._is_open = False
                    self._sonda_half_open_ativa = True
                    deve_logar_half_open = True
                else:
                    raise ExcecaoDisjuntorAberto("Circuit Breaker ABERTO: Abortando para evitar banimentos.")
            elif self._sonda_half_open_ativa:
                raise ExcecaoDisjuntorAberto("Circuit Breaker HALF-OPEN: Sonda em andamento.")
        if deve_logar_half_open:
            app_logger.info("Circuit Breaker: Testando recuperação da API (Half-Open).")

    def _record_failure(self):
        deve_logar_erro = False
        with self._lock:
            self._sonda_half_open_ativa = False
            self._failure_count += 1
            self._last_failure_time = time.time()
            if self._failure_count >= self._failure_threshold:
                self._is_open = True
                deve_logar_erro = True
        if deve_logar_erro:
            app_logger.error(f"Circuit Breaker disparado! Atingiu {self._failure_threshold} falhas seguidas.")

    def _record_success(self):
        deve_logar_recuperacao = False
        with self._lock:
            if self._failure_count > 0 or self._sonda_half_open_ativa:
                deve_logar_recuperacao = True
            self._failure_count = 0
            self._is_open = False
            self._sonda_half_open_ativa = False
        if deve_logar_recuperacao:
            app_logger.info("Circuit Breaker: Conexão estabilizada. Resetando falhas.")
```

---

## 2. `tradutor/servico_traducao.py`
**Objetivo:**
1. Quando `cache_parcial` acertar parte do lote e o sub-lote `pendentes` retornar quantidade de linhas divergente, fazer fallback apenas das linhas `pendentes` sem retraduzir o lote completo de 40 linhas e sem descartar as linhas ja recuperadas do cache parcial.
2. No fallback sequencial, executar `await asyncio.sleep(pausa)` apenas quando houver requisicao real de rede (nao quando a linha vier do cache SQLite).

### Alteracao 2.1: Protecao de `indices_concluidos`, fallback isolado em `pendentes` e `sleep` apenas em chamada de rede

#### SEARCH
```python
                    if cache_parcial:
                        pendentes = []
                        for idx, p_linha in zip(lote_indices, payloads_linhas):
                            if p_linha.texto_mascarado in cache_parcial:
                                r_cached = cache_parcial[p_linha.texto_mascarado]
                                r_rest = self._glossary.restaurar(r_cached, p_linha)
                                subs[idx].text = self._limpar_quebras(r_rest.strip())
                            else:
                                pendentes.append((idx, p_linha))

                        if pendentes:
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

                    # 2. Se não existir, vai na Rede via Engine injetada
```

#### REPLACE
```python
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
```

### Alteracao 2.2: Pular `asyncio.sleep` quando o fallback sequencial obtiver hit no cache local

#### SEARCH
```python
                        r = self._cache.get(texto_protegido, src_lang, dest_lang)
                        if not r:
                            try:
                                r = await loop.run_in_executor(
                                    executor, self._engine.translate, texto_protegido, src_lang, dest_lang
                                )
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
                        pausa = getattr(GerenciadorConfig, "PAUSA_FALLBACK_SEGUNDOS", 0.5)
                        await asyncio.sleep(pausa)
```

#### REPLACE
```python
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
```

---

## 3. `tradutor/servico_textos_extensos.py`
**Objetivo:** Tornar `_executar_com_fallback` recursivo na hierarquia de delimitadores caso um sub-bloco falhe no primeiro nivel de divisao.

### Alteracao 3.1: Fallback recursivo por nivel de delimitador

#### SEARCH
```python
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
```

#### REPLACE
```python
        return await self._fallback_hierarquico(loop, bloco, src_lang, dest_lang, nivel_inicial=0)

    async def _fallback_hierarquico(
        self,
        loop: asyncio.AbstractEventLoop,
        bloco: str,
        src_lang: str,
        dest_lang: str,
        nivel_inicial: int = 0,
    ) -> tuple[str, bool]:
        """Divide recursivamente o bloco pela hierarquia de delimitadores em caso de falha."""
        delimitadores = getattr(self._particionador, "delimitadores", self._particionador._DELIMITADORES)
        for idx_sep in range(nivel_inicial, len(delimitadores)):
            sep = delimitadores[idx_sep]
            if not sep or sep not in bloco:
                continue
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
                        trad_rec, ok_rec = await self._fallback_hierarquico(
                            loop, sb, src_lang, dest_lang, nivel_inicial=idx_sep + 1
                        )
                        if not ok_rec:
                            falha_parcial = True
                        sub_traduzidos.append(trad_rec)
                recomposto = self._particionador.recompor_texto(bloco, sub_blocos, sub_traduzidos)
                sucesso_total = not falha_parcial and not self._is_cancelled()
                return recomposto, sucesso_total

        return bloco, False
```

---

## 4. Testes de Regressao da Etapa 2
Adicione ao final de `tests/unit/test_boost_regressoes.py`:

```python
def test_etapa2_disjuntor_half_open_permite_apenas_uma_sonda_concorrente():
    import time
    import pytest
    from tradutor.tradutores.base import ExcecaoDisjuntorAberto
    from tradutor.tradutores.google import MotorTraducaoGoogle

    motor = MotorTraducaoGoogle(max_retries=1, failure_threshold=2, recovery_timeout=10)
    motor._is_open = True
    motor._failure_count = 2
    motor._last_failure_time = time.time() - 20

    # Primeira thread entra como sonda Half-Open
    motor._check_circuit()
    assert motor._sonda_half_open_ativa is True

    # Segunda thread simultanea deve ser barrada enquanto a sonda nao conclui
    with pytest.raises(ExcecaoDisjuntorAberto):
        motor._check_circuit()

    # Ao registrar sucesso, libera para todas as threads
    motor._record_success()
    assert motor._sonda_half_open_ativa is False
    motor._check_circuit()
```