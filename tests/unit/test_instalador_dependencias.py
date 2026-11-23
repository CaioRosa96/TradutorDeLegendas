"""Testes unitarios para resolucao de pasta customizada, instalacao via winget e contrato de dependencias GPLv2."""

import os
import sys
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


def test_instalacao_automatica_via_winget_sem_url_quebrada(tmp_path, monkeypatch, mocker):
    """Garante que a instalacao automatica usa winget sem URL HTTP quebrada."""
    arq_prefs = str(tmp_path / "preferencias.json")
    monkeypatch.setattr(PreferenciasUsuario, "ARQUIVO_PREFERENCIAS", arq_prefs)
    PreferenciasUsuario._dados = None

    assert not hasattr(InstaladorDependencias, "URL_PACOTE_PORTATIL")

    pasta_instalada = str(tmp_path / "MKVToolNix")
    mocker.patch("tradutor.instalador_dependencias.shutil.which", return_value="winget.exe")
    mock_run = mocker.patch(
        "tradutor.instalador_dependencias.subprocess.run",
        return_value=mocker.MagicMock(returncode=0),
    )
    mocker.patch.object(GerenciadorConfig, "check_dependencies", side_effect=[False, True])
    mocker.patch.object(GerenciadorConfig, "get_mkvtoolnix_path", return_value=pasta_instalada)

    caminho_retornado = InstaladorDependencias.baixar_dependencias()

    assert caminho_retornado == pasta_instalada
    mock_run.assert_called_once()
    cmd_executado = mock_run.call_args[0][0]
    assert cmd_executado[0] == "winget"
    assert "install" in cmd_executado
    assert InstaladorDependencias.WINGET_ID_MKVTOOLNIX in cmd_executado


def test_instalacao_falha_quando_winget_indisponivel(monkeypatch, mocker):
    """Garante erro explicito orientando download manual quando winget nao estiver disponivel."""
    mocker.patch.object(GerenciadorConfig, "check_dependencies", return_value=False)
    mocker.patch("tradutor.instalador_dependencias.shutil.which", return_value=None)

    with pytest.raises(RuntimeError, match="winget"):
        InstaladorDependencias.baixar_dependencias()


def test_instalacao_respeita_cancelamento(mocker):
    """Garante que cancelado_cb interrompe o fluxo levantando InterruptedError."""
    mocker.patch.object(GerenciadorConfig, "check_dependencies", return_value=False)

    with pytest.raises(InterruptedError):
        InstaladorDependencias.baixar_dependencias(cancelado_cb=lambda: True)


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

