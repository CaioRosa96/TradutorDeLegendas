"""Testes unitarios para resolucao de pasta customizada, download sob demanda e contrato de dependencias GPLv2."""

import io
import os
import sys
import zipfile
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from tradutor.config import GerenciadorConfig
from tradutor.config_usuario import PreferenciasUsuario
from tradutor.estrategias.processador_mkv import ProcessadorMkv
from tradutor.instalador_dependencias import InstaladorDependencias, StatusDependencias


def test_deteccao_prioriza_pasta_customizada_usuario(tmp_path, monkeypatch):
    """Garante que uma pasta externa escolhida pelo usuario tem prioridade sobre local e sistema."""
    arq_prefs = str(tmp_path / "preferencias.json")
    monkeypatch.setattr(PreferenciasUsuario, "ARQUIVO_PREFERENCIAS", arq_prefs)
    PreferenciasUsuario._dados = None

    pasta_usuario = tmp_path / "meus_programas_video"
    pasta_usuario.mkdir()
    (pasta_usuario / "mkvmerge.exe").write_bytes(b"MZ_FAKE_MKVMERGE")
    (pasta_usuario / "mkvextract.exe").write_bytes(b"MZ_FAKE_MKVEXTRACT")
    (pasta_usuario / "ffmpeg.exe").write_bytes(b"MZ_FAKE_FFMPEG")

    sucesso, caminho_salvo = InstaladorDependencias.definir_pasta_existente(str(pasta_usuario))
    assert sucesso is True
    assert caminho_salvo == str(pasta_usuario)
    assert PreferenciasUsuario.obter("mkvtoolnix_custom") == str(pasta_usuario)
    assert PreferenciasUsuario.obter("ffmpeg_custom") == str(pasta_usuario)

    status = InstaladorDependencias.diagnosticar()
    assert isinstance(status, StatusDependencias)
    assert status.mkvtoolnix_ok is True
    assert status.ffmpeg_ok is True
    assert status.caminho_mkvtoolnix == str(pasta_usuario)
    assert status.caminho_ffmpeg == str(pasta_usuario / "ffmpeg.exe")


def test_validacao_pasta_invalida_rejeita_diretorio_sem_executaveis(tmp_path, monkeypatch):
    """Garante que selecionar uma pasta sem mkvmerge.exe e mkvextract.exe retorna False."""
    arq_prefs = str(tmp_path / "preferencias.json")
    monkeypatch.setattr(PreferenciasUsuario, "ARQUIVO_PREFERENCIAS", arq_prefs)
    PreferenciasUsuario._dados = None

    pasta_vazia = tmp_path / "pasta_sem_mkvtoolnix"
    pasta_vazia.mkdir()

    sucesso, caminho = InstaladorDependencias.definir_pasta_existente(str(pasta_vazia))
    assert sucesso is False
    assert caminho == ""
    assert PreferenciasUsuario.obter("mkvtoolnix_custom") == ""


def test_download_sob_demanda_extrai_zip_na_pasta_local(tmp_path, monkeypatch, mocker):
    """Valida o download sob demanda de pacote .zip portatil e extracao atomica para mkvtoolnix/."""
    arq_prefs = str(tmp_path / "preferencias.json")
    monkeypatch.setattr(PreferenciasUsuario, "ARQUIVO_PREFERENCIAS", arq_prefs)
    PreferenciasUsuario._dados = None
    monkeypatch.setattr(GerenciadorConfig, "DIRETORIO_EXECUCAO", str(tmp_path))

    # Gera um pacote .zip valido em memoria contendo mkvmerge.exe e mkvextract.exe dentro de subpasta
    buffer_zip = io.BytesIO()
    with zipfile.ZipFile(buffer_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("mkvtoolnix-portable/mkvmerge.exe", b"MZ_PORTABLE_MERGE")
        zf.writestr("mkvtoolnix-portable/mkvextract.exe", b"MZ_PORTABLE_EXTRACT")
    conteudo_zip = buffer_zip.getvalue()

    resposta_mock = mocker.MagicMock()
    resposta_mock.__enter__.return_value = resposta_mock
    resposta_mock.headers = {"content-length": str(len(conteudo_zip))}
    resposta_mock.iter_content.return_value = [conteudo_zip]
    resposta_mock.raise_for_status.return_value = None
    mocker.patch("tradutor.instalador_dependencias.requests.get", return_value=resposta_mock)

    progresso_chamadas = []
    caminho_instalado = InstaladorDependencias.baixar_dependencias(
        progresso_cb=lambda b, t: progresso_chamadas.append((b, t))
    )

    pasta_esperada = str(tmp_path / "mkvtoolnix")
    assert caminho_instalado == pasta_esperada
    assert (tmp_path / "mkvtoolnix" / "mkvmerge.exe").is_file()
    assert (tmp_path / "mkvtoolnix" / "mkvextract.exe").is_file()
    assert len(progresso_chamadas) == 1
    assert progresso_chamadas[0] == (len(conteudo_zip), len(conteudo_zip))


def test_processador_mkv_solicita_dependencias_quando_ausentes(mocker):
    """Garante que ProcessadorMkv.prepare aciona o callback ask_dependencies quando MKVToolNix nao existe."""
    logs = []
    mocker.patch.object(GerenciadorConfig, "check_dependencies", return_value=False)

    chamou_modal = []

    def _ask_dep_recusado():
        chamou_modal.append(True)
        return False

    proc = ProcessadorMkv(
        log_cb=logs.append,
        progress_cb=lambda c, t: None,
        ask_overwrite_cb=lambda n: True,
        is_running_cb=lambda: True,
        ask_dependencies_cb=_ask_dep_recusado,
    )
    arq, lang = proc.prepare("episodio.mkv", "jpn")
    assert arq is None
    assert lang is None
    assert len(chamou_modal) == 1
    assert any("não configurado" in msg or "não encontrado" in msg for msg in logs)

