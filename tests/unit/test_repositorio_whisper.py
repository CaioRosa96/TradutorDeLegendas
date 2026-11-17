"""Testes unitários do repositório de modelos Whisperfile e perfis de hardware."""

import os
from unittest.mock import MagicMock
import pytest

from tradutor.transcritores.repositorio_modelos import RepositorioModelosWhisper
from tradutor.transcritores.recomendador import (
    PerfilHardwareMidia,
    RecomendadorModeloWhisper,
)


def test_catalogo_modelos_whisper_estrutura():
    """Valida que todos os modelos homologados contêm metadados válidos."""
    catalogo = RepositorioModelosWhisper.CATALOGO_MODELOS
    assert len(catalogo) >= 4
    for mod_id in ("tiny", "small", "medium", "large-v3"):
        assert mod_id in catalogo
        info = catalogo[mod_id]
        assert info["id"] == mod_id
        assert info["executavel"].endswith(".exe")
        assert info["url"].startswith("https://huggingface.co/")
        assert "MB" in info["tamanho_aprox"] or "GB" in info["tamanho_aprox"]


def test_caminho_e_instalacao_modelo(tmp_path, mocker):
    """Verifica detecção de binário instalado no diretório bin."""
    mocker.patch.object(RepositorioModelosWhisper, "obter_pasta_bin", return_value=str(tmp_path))
    mocker.patch(
        "tradutor.config.GerenciadorConfig.DIRETORIO_EXECUCAO",
        str(tmp_path),
    )
    mocker.patch(
        "tradutor.config.GerenciadorConfig.DIRETORIO_RECURSOS",
        str(tmp_path),
    )

    assert RepositorioModelosWhisper.esta_modelo_instalado("tiny") is False
    assert RepositorioModelosWhisper.caminho_modelo("tiny") is None

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    fake_tiny = bin_dir / "whisper-tiny.exe"
    fake_tiny.write_bytes(b"x" * 2048)

    assert RepositorioModelosWhisper.esta_modelo_instalado("tiny") is True
    assert RepositorioModelosWhisper.caminho_modelo("tiny") == os.path.abspath(str(fake_tiny))


def test_baixar_modelo_modelo_invalido_lanca_excecao():
    """Tentar baixar um modelo não cadastrado lança ValueError imediatamente."""
    with pytest.raises(ValueError, match="Modelo Whisperfile desconhecido"):
        RepositorioModelosWhisper.baixar_modelo("modelo_fantasma_xyz")


def test_baixar_modelo_sucesso_atomico(tmp_path, mocker):
    """Download cria temporário .part e conclui com rename atômico para o destino."""
    mocker.patch.object(RepositorioModelosWhisper, "obter_pasta_bin", return_value=str(tmp_path))

    mock_resp = MagicMock()
    mock_resp.headers = {"content-length": "100"}
    mock_resp.iter_content.return_value = [b"bloco_1", b"bloco_2"]
    mock_resp.__enter__.return_value = mock_resp

    mocker.patch("requests.get", return_value=mock_resp)

    progresso = []
    caminho = RepositorioModelosWhisper.baixar_modelo(
        "tiny",
        progresso_cb=lambda baixado, total: progresso.append((baixado, total)),
    )

    assert os.path.isfile(caminho)
    assert not os.path.exists(f"{caminho}.part")
    assert len(progresso) == 2


def test_baixar_modelo_cancelamento_limpa_part(tmp_path, mocker):
    """Cancelamento pelo usuário aborta o fluxo e exclui o arquivo intermediário .part."""
    mocker.patch.object(RepositorioModelosWhisper, "obter_pasta_bin", return_value=str(tmp_path))

    mock_resp = MagicMock()
    mock_resp.headers = {"content-length": "100"}
    mock_resp.iter_content.return_value = [b"bloco_1", b"bloco_2"]
    mock_resp.__enter__.return_value = mock_resp

    mocker.patch("requests.get", return_value=mock_resp)

    cancelado_chamado = [False]

    def _cancelado():
        if cancelado_chamado[0]:
            return True
        cancelado_chamado[0] = True
        return False

    with pytest.raises(InterruptedError, match="cancelado"):
        RepositorioModelosWhisper.baixar_modelo("tiny", cancelado_cb=_cancelado)

    destino_part = tmp_path / "whisper-tiny.exe.part"
    assert not destino_part.exists()


def test_perfil_hardware_midia_decisao_pura():
    """Valida a árvore de decisão pura com instâncias de PerfilHardwareMidia."""
    perfil_ram_baixa = PerfilHardwareMidia(ram_livre_gb=1.5)
    rec, _, motivo = RecomendadorModeloWhisper.decidir_modelo_perfil(perfil_ram_baixa)
    assert rec == "tiny"
    assert motivo == "diag_motivo_ram_baixa"

    perfil_voz_limpa = PerfilHardwareMidia(
        duracao_segundos=1200.0,
        idioma_audio="en",
        canais_audio=2,
        possui_fundo_musical=False,
        proporcao_silencio=0.30,
        ram_livre_gb=8.0,
    )
    rec, alt, motivo = RecomendadorModeloWhisper.decidir_modelo_perfil(perfil_voz_limpa)
    assert rec == "tiny"
    assert alt == "small"
    assert motivo == "diag_motivo_voz_limpa_longo"

    perfil_curto_denso = PerfilHardwareMidia(
        duracao_segundos=60.0,
        canais_audio=6,
        proporcao_silencio=0.02,
        ram_livre_gb=8.0,
    )
    rec, _, motivo = RecomendadorModeloWhisper.decidir_modelo_perfil(perfil_curto_denso)
    assert rec == "medium"
    assert motivo == "diag_motivo_fundo_denso_curto"
