"""Testes unitarios para o Logger de producao, Verificador de Atualizacoes e Som sintetizado."""

from datetime import datetime
import io
import logging
import os
import sys
import wave
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from tradutor.logger import (
    HandlerArquivoComTeto,
    detectar_sistema_operacional,
    escolher_diretorio_logs,
    expurgar_logs_antigos,
    gerar_cabecalho_sessao,
)
from tradutor.atualizador import ResultadoAtualizacao, VerificadorAtualizacao
from tradutor.som import gerar_wav_acorde_conclusao, tocar_som_conclusao


def test_escolher_diretorio_logs_primario_e_fallback(tmp_path, monkeypatch):
    """Usa a pasta preferida quando gravavel e faz fallback para LOCALAPPDATA se bloqueada."""
    preferido = str(tmp_path / "logs_primario")
    escolhido = escolher_diretorio_logs(preferido)
    assert escolhido == preferido
    assert os.path.isdir(preferido)
    assert not os.path.exists(os.path.join(preferido, ".sonda_escrita"))

    fallback_base = tmp_path / "local_appdata"
    monkeypatch.setenv("LOCALAPPDATA", str(fallback_base))

    pasta_bloqueada = str(tmp_path / "protegido" / "logs")
    makedirs_original = os.makedirs

    def _makedirs_bloqueado(caminho, *args, **kwargs):
        if os.path.abspath(caminho).startswith(os.path.abspath(pasta_bloqueada)):
            raise PermissionError("Acesso negado em Program Files")
        return makedirs_original(caminho, *args, **kwargs)

    monkeypatch.setattr(os, "makedirs", _makedirs_bloqueado)
    escolhido_fb = escolher_diretorio_logs(pasta_bloqueada)
    esperado_fb = os.path.join(str(fallback_base), "TradutorLegendas26", "logs")
    assert escolhido_fb == esperado_fb
    assert os.path.isdir(esperado_fb)


def test_expurgar_logs_antigos_mantem_7_dias(tmp_path):
    """Remove apenas arquivos tradutor_YYYYMMDD.log anteriores a janela de 7 dias."""
    datas = [
        "20261108",  # hoje (dia 0)
        "20261105",  # 3 dias atras (manter)
        "20261102",  # 6 dias atras -> 7o dia contando com hoje (manter)
        "20261101",  # 7 dias atras -> fora da janela de 7 dias (apagar)
        "20261020",  # antigo (apagar)
    ]
    for d in datas:
        (tmp_path / f"tradutor_{d}.log").write_text("log", encoding="utf-8")

    # Arquivo nao relacionado nao deve ser tocado
    outro_arq = tmp_path / "notas.txt"
    outro_arq.write_text("manter", encoding="utf-8")

    ref = datetime(2026, 11, 8, 12, 0, 0)
    removidos = expurgar_logs_antigos(str(tmp_path), dias_retencao=7, referencia=ref)

    assert removidos == 2
    assert (tmp_path / "tradutor_20261108.log").exists()
    assert (tmp_path / "tradutor_20261105.log").exists()
    assert (tmp_path / "tradutor_20261102.log").exists()
    assert not (tmp_path / "tradutor_20261101.log").exists()
    assert not (tmp_path / "tradutor_20261020.log").exists()
    assert outro_arq.exists()


def test_handler_arquivo_com_teto_suprime_apos_limite(tmp_path):
    """Garante que o HandlerArquivoComTeto para de gravar ao atingir max_bytes."""
    caminho_log = str(tmp_path / "tradutor_20261108.log")
    logger_teste = logging.getLogger("TradutorTesteTeto")
    logger_teste.setLevel(logging.INFO)
    logger_teste.handlers.clear()
    logger_teste.propagate = False

    handler = HandlerArquivoComTeto(caminho_log, max_bytes=120, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger_teste.addHandler(handler)

    try:
        logger_teste.info("A" * 80)
        logger_teste.info("B" * 80)  # Ultrapassa 120 bytes ao final desta escrita
        logger_teste.info("C" * 80)  # Deve acionar o bloqueio e nao gravar os 'C'
        logger_teste.info("D" * 80)  # Ignorado imediatamente
    finally:
        handler.close()
        logger_teste.removeHandler(handler)

    conteudo = (tmp_path / "tradutor_20261108.log").read_text(encoding="utf-8")
    assert "A" * 80 in conteudo
    assert "B" * 80 in conteudo
    assert "Limite diario de log atingido" in conteudo
    assert "C" * 80 not in conteudo
    assert "D" * 80 not in conteudo


def test_cabecalho_sessao_e_deteccao_windows(monkeypatch):
    """Verifica a formatacao do cabecalho de sessao com versao e sistema operacional."""
    cabecalho = gerar_cabecalho_sessao()
    assert "Tradutor de Legendas v2.8.0" in cabecalho
    assert "Python" in cabecalho
    assert detectar_sistema_operacional() in cabecalho


def test_verificador_atualizacao_normalizacao_e_comparacao(mocker):
    """Valida comparacao semantica de tags e tratamento de respostas da API do GitHub."""
    assert VerificadorAtualizacao.normalizar_versao("v2.8.0") == (2, 8, 0)
    assert VerificadorAtualizacao.normalizar_versao("v2.6-classic") == (2, 6, 0)
    assert VerificadorAtualizacao.normalizar_versao("2.9") == (2, 9, 0)

    # 1. Caso: Nova versao disponivel (v2.9.0 > v2.8.0)
    resp_nova = mocker.MagicMock(status_code=200)
    resp_nova.json.return_value = {
        "tag_name": "v2.9.0",
        "html_url": "https://github.com/CaioRosa96/TradutorDeLegendas/releases/tag/v2.9.0",
    }
    mocker.patch("tradutor.atualizador.requests.get", return_value=resp_nova)
    res1 = VerificadorAtualizacao.verificar(versao_atual="2.8.0")
    assert isinstance(res1, ResultadoAtualizacao)
    assert res1.sucesso is True
    assert res1.atualizacao_disponivel is True
    assert res1.versao_remota == "v2.9.0"

    # 2. Caso: Mesma versao (v2.8.0 == v2.8.0)
    resp_igual = mocker.MagicMock(status_code=200)
    resp_igual.json.return_value = {
        "tag_name": "v2.8.0",
        "html_url": "https://github.com/CaioRosa96/TradutorDeLegendas/releases/tag/v2.8.0",
    }
    mocker.patch("tradutor.atualizador.requests.get", return_value=resp_igual)
    res2 = VerificadorAtualizacao.verificar(versao_atual="2.8.0")
    assert res2.sucesso is True
    assert res2.atualizacao_disponivel is False

    # 3. Caso: Falha de rede ou rate-limit HTTP 403
    resp_erro = mocker.MagicMock(status_code=403)
    mocker.patch("tradutor.atualizador.requests.get", return_value=resp_erro)
    res3 = VerificadorAtualizacao.verificar(versao_atual="2.8.0")
    assert res3.sucesso is False
    assert res3.atualizacao_disponivel is False
    assert "403" in res3.erro


def test_sintese_wav_acorde_conclusao_e_reproducao_memoria(mocker):
    """Garante que o acorde sintetizado gera um buffer WAV PCM 16-bit valido e usa SND_MEMORY."""
    wav_bytes = gerar_wav_acorde_conclusao()
    assert wav_bytes.startswith(b"RIFF")
    assert b"WAVE" in wav_bytes[:16]

    with wave.open(io.BytesIO(wav_bytes), "rb") as w:
        assert w.getnchannels() == 1
        assert w.getsampwidth() == 2
        assert w.getframerate() == 22050
        assert w.getnframes() > 4000

    mock_winsound = mocker.MagicMock()
    mock_winsound.SND_MEMORY = 4
    mock_winsound.SND_ASYNC = 1
    mock_winsound.SND_NODEFAULT = 2
    mocker.patch("tradutor.som.winsound", mock_winsound)

    assert tocar_som_conclusao() is True
    mock_winsound.PlaySound.assert_called_once()
    args, _ = mock_winsound.PlaySound.call_args
    assert args[0] == wav_bytes
    assert args[1] & mock_winsound.SND_MEMORY

