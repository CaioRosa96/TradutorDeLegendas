"""Testes unitarios para a interface de linha de comando (CLI Headless) do TradutorLegendas26."""
from __future__ import annotations

import os
import sys
import json
from unittest.mock import MagicMock, patch
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from tradutor.cli import CodigoSaidaCli, construir_parser, executar_cli
from tradutor.tradutores.base import ExcecaoDisjuntorAberto


def test_parser_argumentos():
    parser = construir_parser()
    args = parser.parse_args([
        "--headless",
        "-i", "video.mkv",
        "-o", "output/dir",
        "-s", "en",
        "-d", "pt-br",
        "--anime-title", "Anime Teste",
        "--anilist-id", "12345",
        "--skip-if-target-exists",
        "--enable-whisper",
        "-y",
        "--json-output",
    ])
    assert args.headless is True
    assert args.input == "video.mkv"
    assert args.output_dir == "output/dir"
    assert args.src == "en"
    assert args.dest == "pt-br"
    assert args.anime_title == "Anime Teste"
    assert args.anilist_id == 12345
    assert args.skip_if_target_exists is True
    assert args.enable_whisper is True
    assert args.overwrite is True
    assert args.json_output is True


def test_cli_arquivo_inexistente_retorna_codigo_1(capsys):
    ret = executar_cli(["--headless", "-i", "arquivo_que_nao_existe.mkv", "--json-output"])
    assert ret == CodigoSaidaCli.ERRO_FATAL_ARQUIVO
    captured = capsys.readouterr()
    payload = json.loads(captured.out.strip())
    assert payload["exit_code"] == 1
    assert payload["status"] == "ERRO_FATAL_ARQUIVO"
    assert "inexistente" in payload["error_message"]


def test_cli_dependencia_ausente_retorna_codigo_5(tmp_path, capsys):
    mkv_fake = tmp_path / "teste.mkv"
    mkv_fake.write_bytes(b"dummy mkv data")

    with patch("tradutor.config.GerenciadorConfig.check_dependencies", return_value=False):
        ret = executar_cli(["--headless", "-i", str(mkv_fake), "--json-output"])
        assert ret == CodigoSaidaCli.DEPENDENCIA_AUSENTE
        captured = capsys.readouterr()
        payload = json.loads(captured.out.strip())
        assert payload["exit_code"] == 5
        assert payload["status"] == "DEPENDENCIA_AUSENTE"


def test_cli_skip_if_target_exists_retorna_codigo_2(tmp_path, capsys):
    mkv_fake = tmp_path / "teste.mkv"
    mkv_fake.write_bytes(b"dummy mkv data")

    with patch("tradutor.config.GerenciadorConfig.check_dependencies", return_value=True), \
         patch("tradutor.manipulador_mkv.ManipuladorMkv.listar_idiomas_legendas", return_value=["por", "eng"]):
        ret = executar_cli([
            "--headless",
            "-i", str(mkv_fake),
            "-d", "pt-br",
            "--skip-if-target-exists",
            "--json-output"
        ])
        assert ret == CodigoSaidaCli.IGNORADO_IDIOMA_EXISTENTE
        captured = capsys.readouterr()
        payload = json.loads(captured.out.strip())
        assert payload["exit_code"] == 2
        assert payload["status"] == "IGNORADO_IDIOMA_EXISTENTE"
        assert payload["output_video_path"] == str(mkv_fake)


def test_cli_sem_legenda_sem_whisper_retorna_codigo_4(tmp_path, capsys):
    mkv_fake = tmp_path / "sem_sub.mkv"
    mkv_fake.write_bytes(b"dummy mkv data")

    with patch("tradutor.config.GerenciadorConfig.check_dependencies", return_value=True), \
         patch("tradutor.manipulador_mkv.ManipuladorMkv.listar_idiomas_legendas", return_value=[]), \
         patch("tradutor.manipulador_mkv.ManipuladorMkv.identificar_mkvs_sem_legenda", return_value={str(mkv_fake)}):
        ret = executar_cli([
            "--headless",
            "-i", str(mkv_fake),
            "-d", "pt-br",
            "--json-output"
        ])
        assert ret == CodigoSaidaCli.SEM_LEGENDA_DISPONIVEL
        captured = capsys.readouterr()
        payload = json.loads(captured.out.strip())
        assert payload["exit_code"] == 4
        assert payload["status"] == "SEM_LEGENDA_DISPONIVEL"


def test_cli_sucesso_com_json_output(tmp_path, capsys):
    srt_fake = tmp_path / "legenda.srt"
    srt_fake.write_text("1\n00:00:01,000 --> 00:00:02,000\nHello\n", encoding="utf-8")

    mock_proc = MagicMock()
    mock_proc.process.return_value = True
    mock_proc.get_output_paths.return_value = {
        "video": None,
        "legenda": str(tmp_path / "legenda_PT-BR.srt")
    }

    with patch("tradutor.estrategias.fabrica.FabricaProcessadores.get_processor", return_value=mock_proc):
        ret = executar_cli([
            "--headless",
            "-i", str(srt_fake),
            "-d", "pt-br",
            "--keep-external-sub",
            "--json-output"
        ])
        assert ret == CodigoSaidaCli.SUCESSO
        captured = capsys.readouterr()
        payload = json.loads(captured.out.strip())
        assert payload["exit_code"] == 0
        assert payload["status"] == "SUCESSO"
        assert payload["target_lang"] == "pt"
        assert payload["output_subtitle_path"] == str(tmp_path / "legenda_PT-BR.srt")


def test_cli_idioma_destino_invalido_retorna_codigo_1(tmp_path, capsys):
    srt_fake = tmp_path / "legenda.srt"
    srt_fake.write_text("1\n00:00:01,000 --> 00:00:02,000\nHello\n", encoding="utf-8")

    ret = executar_cli([
        "--headless",
        "-i", str(srt_fake),
        "-d", "invalido_xyz",
        "--json-output"
    ])
    assert ret == CodigoSaidaCli.ERRO_FATAL_ARQUIVO
    captured = capsys.readouterr()
    payload = json.loads(captured.out.strip())
    assert payload["exit_code"] == 1
    assert "invalido" in payload["error_message"].lower()


def test_cli_disjuntor_aberto_retorna_codigo_3(tmp_path, capsys):
    srt_fake = tmp_path / "legenda.srt"
    srt_fake.write_text("1\n00:00:01,000 --> 00:00:02,000\nHello\n", encoding="utf-8")

    mock_proc = MagicMock()
    mock_proc.process.side_effect = ExcecaoDisjuntorAberto("Circuit Breaker Aberto")

    with patch("tradutor.estrategias.fabrica.FabricaProcessadores.get_processor", return_value=mock_proc):
        ret = executar_cli([
            "--headless",
            "-i", str(srt_fake),
            "-d", "pt-br",
            "--json-output"
        ])
        assert ret == CodigoSaidaCli.ERRO_REDE_OU_DISJUNTOR
        captured = capsys.readouterr()
        payload = json.loads(captured.out.strip())
        assert payload["exit_code"] == 3
        assert payload["status"] == "ERRO_REDE_OU_DISJUNTOR"


def test_cli_alias_json_e_force_whisper_e_source_lang_detected(tmp_path, capsys):
    """Garante funcionamento do alias --json, da flag --force-whisper e propagacao de ultimo_idioma_detectado."""
    mkv_fake = tmp_path / "video.mkv"
    mkv_fake.write_bytes(b"dummy")

    mock_proc = MagicMock()
    mock_proc.process.return_value = True
    mock_proc.ultimo_idioma_detectado = "jpn"
    mock_proc.ultimos_caminhos_saida = {
        "video": str(tmp_path / "video_PT.mkv"),
        "legenda": None,
    }
    mock_proc.get_output_paths.return_value = mock_proc.ultimos_caminhos_saida

    with patch("tradutor.estrategias.fabrica.FabricaProcessadores.get_processor", return_value=mock_proc), \
         patch("tradutor.config.GerenciadorConfig.check_dependencies", return_value=True):
        ret = executar_cli([
            "--headless",
            "-i", str(mkv_fake),
            "-d", "pt",
            "--force-whisper",
            "--json",
        ])
        assert ret == CodigoSaidaCli.SUCESSO
        captured = capsys.readouterr()
        payload = json.loads(captured.out.strip())
        assert payload["source_lang_detected"] == "jpn"
        assert payload["exit_code"] == 0
