import pytest
import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import AsyncMock, MagicMock, call

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from tradutor.config import GerenciadorConfig
from tradutor.contratos import LinhaProtegida
from tradutor.servico_traducao import ServicoTraducao
from tradutor.tradutores.base import ExcecaoDisjuntorAberto

class EventoLegendaDummy:
    """Mock básico para simular eventos de legenda do pysubs2."""
    def __init__(self, text):
        self.text = text

@pytest.fixture
def servico_setup(mocker):
    """
    Fixture que cria uma instância de ServicoTraducao isolada:
    - Sem Banco de Dados Real (Cache mockado)
    - Sem Acesso a Disco (Glossario mockado)
    - Com Callbacks de log e progresso falsos.
    """
    mocker.patch('tradutor.servico_traducao.CacheTraducoes')
    mocker.patch('tradutor.servico_traducao.GerenciadorGlossario')
    mocker.patch.object(GerenciadorConfig, 'PAUSA_FALLBACK_SEGUNDOS', 0)
    
    mock_logger = MagicMock()
    mock_progress = MagicMock()
    mock_engine = MagicMock()
    
    servico = ServicoTraducao(
        logger=mock_logger,
        progress_callback=mock_progress,
        engine=mock_engine,
        video_filename="fake_video.mkv"
    )
    
    # Escudo neutro: devolve o texto sem tokens e restaura sem alterações
    servico._glossary.proteger.side_effect = lambda texto, id_linha=0: LinhaProtegida(
        id_linha=id_linha, texto_original=texto, texto_mascarado=texto
    )
    servico._glossary.restaurar.side_effect = lambda texto, payload: texto
    
    # Mockando o comportamento do cache
    servico._cache.get.return_value = None
    
    return servico, mock_engine, mock_logger, mock_progress


@pytest.mark.asyncio
async def test_traduzir_lote_happy_path(servico_setup):
    """
    Cenário A: O motor traduz perfeitamente um lote.
    A quantidade de linhas retornadas bate com a enviada.
    """
    servico, mock_engine, _, _ = servico_setup
    
    # Configura o retorno do Engine para ser idêntico em quantidade de linhas
    mock_engine.translate.return_value = "Linha 1 traduzida\nLinha 2 traduzida\nLinha 3 traduzida"
    
    subs = [
        EventoLegendaDummy("Line 1"),
        EventoLegendaDummy("Line 2"),
        EventoLegendaDummy("Line 3")
    ]
    lote_indices = [0, 1, 2]
    
    semaforo = asyncio.Semaphore(1)
    pbar_lock = threading.Lock()
    
    with ThreadPoolExecutor(max_workers=1) as executor:
        await servico._traduzir_lote(executor, semaforo, lote_indices, subs, pbar_lock)
        
    # Verifica se o motor foi chamado exatamente 1 vez (em lote)
    assert mock_engine.translate.call_count == 1
    
    # Verifica se os objetos originais foram atualizados
    assert subs[0].text == "Linha 1 traduzida"
    assert subs[1].text == "Linha 2 traduzida"
    assert subs[2].text == "Linha 3 traduzida"


@pytest.mark.asyncio
async def test_traduzir_lote_fallback_sequencial(servico_setup):
    """
    Cenário B: O motor "alucina" e retorna menos linhas do que o lote continha.
    O sistema DEVE detectar a dessincronia e enviar cada linha individualmente.
    """
    servico, mock_engine, mock_logger, _ = servico_setup
    
    # O motor foi mandado traduzir 3 linhas, mas devolve 2 (dessincronia).
    # Como ele vai rodar sequencial depois, usamos um side_effect para a primeira vez devolver erro de lote
    # E as 3 vezes subsequentes devolverem traduções singulares.
    mock_engine.translate.side_effect = [
        "Linha única e errada, o google comeu o resto",  # Lote quebrado
        "Linha 1 fallback",                              # Fallback 1
        "Linha 2 fallback",                              # Fallback 2
        "Linha 3 fallback"                               # Fallback 3
    ]
    
    subs = [
        EventoLegendaDummy("Line 1"),
        EventoLegendaDummy("Line 2"),
        EventoLegendaDummy("Line 3")
    ]
    lote_indices = [0, 1, 2]
    
    semaforo = asyncio.Semaphore(1)
    pbar_lock = threading.Lock()
    
    with ThreadPoolExecutor(max_workers=1) as executor:
        await servico._traduzir_lote(executor, semaforo, lote_indices, subs, pbar_lock)
        
    # Deve ter chamado 4 vezes: 1 para a tentativa em lote + 3 para o fallback sequencial
    assert mock_engine.translate.call_count == 4
    
    # Deve registrar no logger o aviso do fallback
    mock_logger.assert_any_call("[Aviso] Dessincronia no lote. Executando fallback sequencial...")
    
    # Verifica se a tradução final recuperou com os fallbacks
    assert subs[0].text == "Linha 1 fallback"
    assert subs[1].text == "Linha 2 fallback"
    assert subs[2].text == "Linha 3 fallback"


@pytest.mark.asyncio
async def test_traduzir_lote_excecao(servico_setup):
    """
    Cenário C: A API cai, ou o banco recusa a conexão (Erro Crítico).
    O lote deve ser ignorado de forma segura, mantendo o texto original.
    """
    servico, mock_engine, mock_logger, _ = servico_setup
    
    # Força um erro crítico na API
    mock_engine.translate.side_effect = Exception("Internal Server Error")
    
    subs = [
        EventoLegendaDummy("Keep me 1"),
        EventoLegendaDummy("Keep me 2")
    ]
    lote_indices = [0, 1]
    
    semaforo = asyncio.Semaphore(1)
    pbar_lock = threading.Lock()
    
    with ThreadPoolExecutor(max_workers=1) as executor:
        await servico._traduzir_lote(executor, semaforo, lote_indices, subs, pbar_lock)
        
    # O logger deve reportar erro crítico
    logger_calls = [call.args[0] for call in mock_logger.call_args_list]
    assert any("[Erro Crítico] Lote ignorado" in call for call in logger_calls)
    
    # As legendas originais não podem ter sido apagadas
    assert subs[0].text == "Keep me 1"
    assert subs[1].text == "Keep me 2"


@pytest.mark.asyncio
async def test_traduzir_lote_preserva_linhas_vazias_sem_fallback(servico_setup):
    """
    Garante que se uma linha for vazia ou traduzida como espaço,
    o sistema não descarta a linha com filter agressivo e não aciona fallback indevido.
    """
    servico, mock_engine, mock_logger, _ = servico_setup
    
    # Motor devolve 3 linhas, a do meio é vazia
    mock_engine.translate.return_value = "Linha 1\n\nLinha 3"
    
    subs = [
        EventoLegendaDummy("Line 1"),
        EventoLegendaDummy(""),
        EventoLegendaDummy("Line 3")
    ]
    lote_indices = [0, 1, 2]
    
    semaforo = asyncio.Semaphore(1)
    pbar_lock = threading.Lock()
    
    with ThreadPoolExecutor(max_workers=1) as executor:
        await servico._traduzir_lote(executor, semaforo, lote_indices, subs, pbar_lock)
        
    # Deve chamar apenas 1 vez (em lote), sem fallback
    assert mock_engine.translate.call_count == 1
    assert subs[0].text == "Linha 1"
    assert subs[1].text == ""
    assert subs[2].text == "Linha 3"


async def _executar_lote(servico, subs):
    """Executa um lote único cobrindo todos os eventos fornecidos."""
    with ThreadPoolExecutor(max_workers=1) as executor:
        await servico._traduzir_lote(
            executor, asyncio.Semaphore(1), list(range(len(subs))), subs, threading.Lock()
        )


@pytest.mark.asyncio
async def test_fallback_falha_isolada_preserva_linhas_vizinhas(servico_setup):
    """
    Uma falha em uma única linha do fallback não pode descartar as traduções
    já obtidas para as linhas anteriores nem impedir as seguintes.
    Antes da Fase 2, a exceção revertia o lote inteiro para o texto original.
    """
    servico, mock_engine, mock_logger, _ = servico_setup
    mock_engine.translate.side_effect = [
        "Lote dessincronizado",
        "Linha 1 fallback",
        TimeoutError("Timeout na linha 2"),
        "Linha 3 fallback",
    ]
    subs = [EventoLegendaDummy("Line 1"), EventoLegendaDummy("Line 2"), EventoLegendaDummy("Line 3")]

    await _executar_lote(servico, subs)

    assert mock_engine.translate.call_count == 4
    assert [s.text for s in subs] == ["Linha 1 fallback", "Line 2", "Linha 3 fallback"]
    logs = [c.args[0] for c in mock_logger.call_args_list]
    assert not any("[Erro Crítico]" in log for log in logs)


@pytest.mark.asyncio
async def test_fallback_interrompe_quando_disjuntor_abre(servico_setup):
    """Com o disjuntor aberto, as linhas restantes não são enviadas e mantêm o original."""
    servico, mock_engine, _, _ = servico_setup
    mock_engine.translate.side_effect = [
        "Lote dessincronizado",
        "Linha 1 fallback",
        ExcecaoDisjuntorAberto("Circuit Breaker ABERTO"),
    ]
    subs = [EventoLegendaDummy("Line 1"), EventoLegendaDummy("Line 2"), EventoLegendaDummy("Line 3")]

    await _executar_lote(servico, subs)

    assert mock_engine.translate.call_count == 3
    assert [s.text for s in subs] == ["Linha 1 fallback", "Line 2", "Line 3"]
    assert subs[-1].text == "Line 3"


@pytest.mark.asyncio
async def test_fallback_disjuntor_aberto_na_primeira_linha_limpa_todas_as_restantes(servico_setup):
    """Quando o disjuntor abre logo na primeira linha do fallback, todas as linhas restantes
    do lote, inclusive a última, devem ter suas quebras limpas deterministicamente."""
    servico, mock_engine, _, _ = servico_setup
    mock_engine.translate.side_effect = [
        "Lote dessincronizado",
        ExcecaoDisjuntorAberto("Circuit Breaker ABERTO"),
    ]
    subs = [
        EventoLegendaDummy(r"Line 1 \ N com espaco"),
        EventoLegendaDummy(r"Line 2 \ n outro"),
        EventoLegendaDummy(r"Line 3 \ N ultima linha"),
    ]

    await _executar_lote(servico, subs)

    assert mock_engine.translate.call_count == 2
    assert subs[0].text == r"Line 1\Ncom espaco"
    assert subs[1].text == r"Line 2\noutro"
    assert subs[2].text == r"Line 3\Nultima linha"
    assert subs[-1].text == r"Line 3\Nultima linha"


@pytest.mark.asyncio
async def test_fallback_respeita_cancelamento(servico_setup):
    """Após o cancelamento, nenhuma nova linha é enviada ao motor."""
    servico, mock_engine, _, _ = servico_setup
    chamadas = {"n": 0}

    def traduzir(texto, src, dest):
        chamadas["n"] += 1
        return "Lote dessincronizado" if chamadas["n"] == 1 else f"{texto} traduzida"

    mock_engine.translate.side_effect = traduzir
    servico._is_cancelled = lambda: chamadas["n"] >= 2
    subs = [EventoLegendaDummy("Line 1"), EventoLegendaDummy("Line 2"), EventoLegendaDummy("Line 3")]

    await _executar_lote(servico, subs)

    assert mock_engine.translate.call_count == 2
    assert [s.text for s in subs] == ["Line 1 traduzida", "Line 2", "Line 3"]


@pytest.mark.asyncio
async def test_fallback_aplica_pausa_anti_rate_limit(servico_setup, mocker):
    """Cada linha do fallback é seguida da pausa configurada (AGENTS.md §5.4)."""
    servico, mock_engine, _, _ = servico_setup
    mocker.patch.object(GerenciadorConfig, 'PAUSA_FALLBACK_SEGUNDOS', 0.5)
    pausa = mocker.patch('tradutor.servico_traducao.asyncio.sleep', new_callable=AsyncMock)
    mock_engine.translate.side_effect = ["Lote dessincronizado", "A", "B"]
    subs = [EventoLegendaDummy("Line 1"), EventoLegendaDummy("Line 2")]

    await _executar_lote(servico, subs)

    assert pausa.await_args_list == [call(0.5), call(0.5)]


@pytest.mark.asyncio
async def test_progresso_reporta_lote_inteiro_apos_fallback(servico_setup):
    servico, mock_engine, _, mock_progress = servico_setup
    mock_engine.translate.side_effect = ["Lote dessincronizado", "A", "B", "C"]
    subs = [EventoLegendaDummy("1"), EventoLegendaDummy("2"), EventoLegendaDummy("3")]

    await _executar_lote(servico, subs)

    mock_progress.assert_called_once_with(3, 0)


@pytest.mark.asyncio
async def test_chave_de_cache_usa_texto_mascarado_do_bloco(servico_setup):
    """A chave do cache deve continuar sendo o bloco unido por \\n e já mascarado."""
    servico, mock_engine, _, _ = servico_setup
    servico._glossary.proteger.side_effect = lambda texto, id_linha=0: LinhaProtegida(
        id_linha=id_linha, texto_original=texto, texto_mascarado=f"<{texto}>"
    )
    servico._glossary.restaurar.side_effect = lambda texto, payload: texto.strip("<>")
    mock_engine.translate.return_value = "<X\nY>"
    subs = [EventoLegendaDummy("A"), EventoLegendaDummy("B")]

    await _executar_lote(servico, subs)

    servico._cache.get.assert_called_once_with("<A\nB>", "auto", "pt")
    servico._cache.put.assert_called_once_with("<A\nB>", "auto", "pt", "<X\nY>")
    assert [s.text for s in subs] == ["X", "Y"]


def test_pausa_padrao_do_fallback_respeita_rate_limit():
    assert GerenciadorConfig.PAUSA_FALLBACK_SEGUNDOS == 0.5


def test_servico_traducao_repassa_auto_alimentar_para_glossario(mocker):
    """Garante que o ServicoTraducao repassa a flag habilitar_auto_alimentar ao GerenciadorGlossario."""
    mocker.patch("tradutor.servico_traducao.CacheTraducoes")
    mock_gg = mocker.patch("tradutor.servico_traducao.GerenciadorGlossario")

    ServicoTraducao(
        logger=MagicMock(),
        progress_callback=MagicMock(),
        engine=MagicMock(),
        video_filename="Bleach_01.mkv",
        habilitar_auto_alimentar=True,
    )

    mock_gg.assert_called_once_with(
        video_filename="Bleach_01.mkv",
        habilitar_auto_alimentar=True,
    )


@pytest.mark.asyncio
async def test_cache_get_many_evita_rede_quando_linhas_ja_cacheadas(servico_setup):
    """Se o bloco inteiro der cache miss, mas todas as linhas individuais já estiverem no
    cache via get_many (ex: abertura repetida entre episódios), não deve chamar a rede."""
    servico, mock_engine, _, _ = servico_setup
    servico._cache.get.return_value = None
    servico._cache.get_many.return_value = {
        "Opening line 1": "Linha de abertura 1",
        "Opening line 2": "Linha de abertura 2",
    }

    subs = [
        EventoLegendaDummy("Opening line 1"),
        EventoLegendaDummy("Opening line 2"),
    ]

    await _executar_lote(servico, subs)

    assert mock_engine.translate.call_count == 0
    assert [s.text for s in subs] == ["Linha de abertura 1", "Linha de abertura 2"]

