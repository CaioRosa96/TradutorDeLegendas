"""Testes de concorrência do Circuit Breaker do MotorTraducaoGoogle.

O motor é compartilhado pelas threads do ThreadPoolExecutor do ServicoTraducao,
portanto a transição de estado do disjuntor precisa ser atômica e a chamada de
rede precisa permanecer fora da seção crítica.
"""
import os
import sys
import threading
import time
from types import SimpleNamespace

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from tradutor.tradutores.google import ExcecaoDisjuntorAberto, MotorTraducaoGoogle

TIMEOUT_SINCRONIA = 2.0


@pytest.fixture
def translator_falso(mocker):
    """Substitui o cliente googletrans para impedir qualquer acesso à rede."""
    return mocker.patch('tradutor.tradutores.google.Translator').return_value


@pytest.fixture
def logger_falso(mocker):
    return mocker.patch('tradutor.tradutores.google.app_logger')


def test_half_open_nao_sobrescreve_disjuntor_reaberto_por_outra_thread(translator_falso, logger_falso):
    """Reproduz a escrita obsoleta (stale write) na transição half-open.

    Thread A lê o disjuntor aberto e expirado e decide fechá-lo. Antes de gravar,
    a thread B registra uma nova falha que reabre o disjuntor. Sem atomicidade,
    A grava `_is_open = False` por cima e o disjuntor fica fechado com o contador
    acima do limiar, liberando requisições que deveriam ser bloqueadas.
    """
    motor = MotorTraducaoGoogle(failure_threshold=2, recovery_timeout=60)
    motor._is_open = True
    motor._failure_count = 2
    motor._last_failure_time = time.time() - 61

    a_decidiu = threading.Event()
    b_terminou = threading.Event()

    def pausar_thread_a(*_args, **_kwargs):
        a_decidiu.set()
        b_terminou.wait(TIMEOUT_SINCRONIA)

    logger_falso.info.side_effect = pausar_thread_a

    def thread_b():
        a_decidiu.wait(TIMEOUT_SINCRONIA)
        motor._record_failure()
        b_terminou.set()

    tb = threading.Thread(target=thread_b)
    tb.start()
    motor._check_circuit()
    tb.join(TIMEOUT_SINCRONIA)

    assert motor._failure_count == 3
    assert motor._is_open is True
    with pytest.raises(ExcecaoDisjuntorAberto):
        motor._check_circuit()


def test_falhas_concorrentes_nao_perdem_incrementos(translator_falso, logger_falso):
    """Todas as falhas registradas simultaneamente devem ser contabilizadas."""
    motor = MotorTraducaoGoogle(failure_threshold=10_000)
    total_threads, falhas_por_thread = 8, 500
    barreira = threading.Barrier(total_threads)

    def registrar():
        barreira.wait(TIMEOUT_SINCRONIA)
        for _ in range(falhas_por_thread):
            motor._record_failure()

    threads = [threading.Thread(target=registrar) for _ in range(total_threads)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert motor._failure_count == total_threads * falhas_por_thread


def test_chamada_de_rede_permanece_fora_do_lock(translator_falso, logger_falso):
    """Três threads precisam estar simultaneamente dentro da chamada de rede.

    Se o lock do disjuntor envolvesse a requisição HTTP, as threads seriam
    serializadas e a barreira expiraria (BrokenBarrierError).
    """
    total_threads = 3
    barreira = threading.Barrier(total_threads, timeout=TIMEOUT_SINCRONIA)

    def rede_simulada(texto, src, dest):
        barreira.wait()
        return SimpleNamespace(text=f"[{dest}] {texto}")

    translator_falso.translate.side_effect = rede_simulada
    motor = MotorTraducaoGoogle(max_retries=1)
    resultados, erros = [], []

    def traduzir(i):
        try:
            resultados.append(motor.translate(f"linha {i}", "en", "pt"))
        except Exception as exc:
            erros.append(exc)

    threads = [threading.Thread(target=traduzir, args=(i,)) for i in range(total_threads)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert erros == []
    assert sorted(resultados) == ["[pt] linha 0", "[pt] linha 1", "[pt] linha 2"]
    assert motor._failure_count == 0
