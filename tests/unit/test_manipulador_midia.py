"""Testes unitários da porta ManipuladorMidiaPort, seus adaptadores e integração."""
from __future__ import annotations

import dataclasses
import os
import subprocess
from unittest.mock import MagicMock, patch

import pytest

from tradutor.config import GerenciadorConfig
from tradutor.config_usuario import PreferenciasUsuario
from tradutor.estrategias.fabrica import FabricaProcessadores
from tradutor.estrategias.processador_mkv import ProcessadorMkv
from tradutor.manipulador_midia import (
    AdaptadorMkvToolNixFFmpeg,
    FakeManipuladorMidia,
    ManipuladorMidiaPort,
    TrilhaMidia,
)
from tradutor.manipulador_mkv import ManipuladorMkv
from tradutor.transcritores import MotorWhisperfile, ResultadoTranscricao


class ObjetoIncompletoSemEmbutir:
    """Objeto que implementa apenas parte da porta para validação de runtime_checkable."""

    def listar_trilhas(self, arquivo: str) -> list[TrilhaMidia]:
        return []

    def extrair_legenda(self, arquivo: str, id_trilha: int, destino: str) -> str:
        return destino

    def extrair_audio(self, arquivo: str, destino: str) -> str:
        return destino


class TestContratoManipuladorMidia:
    """Testes formais do contrato ManipuladorMidiaPort e do Value Object TrilhaMidia."""

    def test_trilha_midia_imutavel(self):
        trilha = TrilhaMidia(id=0, tipo="subtitles", idioma="ja", codec="SubRip/SRT", formato=".srt")
        assert trilha.id == 0
        assert trilha.tipo == "subtitles"
        assert trilha.idioma == "ja"
        assert trilha.formato == ".srt"

        with pytest.raises(dataclasses.FrozenInstanceError):
            trilha.idioma = "pt"  # type: ignore

    def test_trilha_midia_valores_padrao(self):
        trilha = TrilhaMidia(id=1, tipo="audio")
        assert trilha.idioma == "und"
        assert trilha.codec == ""
        assert trilha.formato == ""
        assert trilha.nome == ""

    def test_fake_manipulador_satisfaz_protocolo(self):
        fake = FakeManipuladorMidia()
        assert isinstance(fake, ManipuladorMidiaPort)

    def test_adaptador_real_satisfaz_protocolo(self):
        adaptador = AdaptadorMkvToolNixFFmpeg()
        assert isinstance(adaptador, ManipuladorMidiaPort)

    def test_objeto_incompleto_rejeitado_pelo_protocolo(self):
        incompleto = ObjetoIncompletoSemEmbutir()
        assert not isinstance(incompleto, ManipuladorMidiaPort)


class TestFakeManipuladorMidia:
    """Testes da implementação em memória para testes determinísticos sem binários externos."""

    def test_listar_trilhas_padrao(self):
        fake = FakeManipuladorMidia()
        trilhas = fake.listar_trilhas("video.mkv")
        assert len(trilhas) == 3
        assert fake.chamadas_listar_trilhas == ["video.mkv"]
        assert any(t.tipo == "video" for t in trilhas)
        assert any(t.tipo == "audio" for t in trilhas)
        assert any(t.tipo == "subtitles" for t in trilhas)

    def test_listar_trilhas_configuradas_lista(self):
        trilhas_custom = [TrilhaMidia(id=0, tipo="subtitles", idioma="pt", formato=".srt")]
        fake = FakeManipuladorMidia(trilhas=trilhas_custom)
        resultado = fake.listar_trilhas("qualquer.mkv")
        assert resultado == trilhas_custom

    def test_listar_trilhas_configuradas_por_arquivo(self):
        mapa = {
            "anime.mkv": [TrilhaMidia(id=2, tipo="subtitles", idioma="ja", formato=".ass")],
            "filme.mkv": [TrilhaMidia(id=1, tipo="subtitles", idioma="en", formato=".srt")],
        }
        fake = FakeManipuladorMidia(trilhas=mapa)
        assert fake.listar_trilhas("C:/videos/anime.mkv")[0].idioma == "ja"
        assert fake.listar_trilhas("filme.mkv")[0].idioma == "en"
        assert fake.listar_trilhas("desconhecido.mkv") == []

    def test_simular_erro_listar_trilhas(self):
        fake = FakeManipuladorMidia()
        fake.simular_erro_listar_trilhas = RuntimeError("Falha de I/O simulada")
        with pytest.raises(RuntimeError, match="Falha de I/O simulada"):
            fake.listar_trilhas("video.mkv")

    def test_extrair_legenda_em_arquivo_e_diretorio(self, tmp_path):
        fake = FakeManipuladorMidia()
        destino_arq = str(tmp_path / "extraida.srt")
        res1 = fake.extrair_legenda("video.mkv", 2, destino_arq)
        assert res1 == destino_arq
        assert os.path.exists(destino_arq)
        with open(destino_arq, encoding="utf-8") as f:
            assert "Linha fake de teste" in f.read()

        pasta_dest = str(tmp_path / "subpasta")
        res2 = fake.extrair_legenda("video.mkv", 5, pasta_dest)
        assert os.path.exists(res2)
        assert "legenda_extraida_5.srt" in res2

        assert len(fake.chamadas_extrair_legenda) == 2

    def test_simular_erro_extrair_legenda(self, tmp_path):
        fake = FakeManipuladorMidia()
        fake.simular_erro_extrair_legenda = ValueError("Trilha corrompida")
        with pytest.raises(ValueError, match="Trilha corrompida"):
            fake.extrair_legenda("video.mkv", 0, str(tmp_path / "out.srt"))

    def test_extrair_audio_gera_cabecalho_wav(self, tmp_path):
        fake = FakeManipuladorMidia()
        destino_wav = str(tmp_path / "audio.wav")
        res = fake.extrair_audio("video.mkv", destino_wav)
        assert res == destino_wav
        assert os.path.exists(destino_wav)
        with open(destino_wav, "rb") as f:
            assert f.read(4) == b"RIFF"

    def test_simular_erro_extrair_audio(self, tmp_path):
        fake = FakeManipuladorMidia()
        fake.simular_erro_extrair_audio = RuntimeError("Codec de audio incompativel")
        with pytest.raises(RuntimeError, match="Codec de audio incompativel"):
            fake.extrair_audio("video.mkv", str(tmp_path / "audio.wav"))

    def test_embutir_legenda_gera_arquivo_final(self, tmp_path):
        fake = FakeManipuladorMidia()
        saida_mkv = str(tmp_path / "video_saida.mkv")
        res = fake.embutir_legenda("origem.mkv", "legenda.srt", saida_mkv, idioma="pt-br")
        assert res == saida_mkv
        assert os.path.exists(saida_mkv)
        with open(saida_mkv, "rb") as f:
            assert f.read() == b"VIDEO_CONTAINER_FAKE"
        assert fake.chamadas_embutir_legenda == [("origem.mkv", "legenda.srt", saida_mkv, "pt-br")]

    def test_simular_erro_embutir_legenda(self, tmp_path):
        fake = FakeManipuladorMidia()
        fake.simular_erro_embutir_legenda = RuntimeError("Espaço em disco insuficiente")
        with pytest.raises(RuntimeError, match="Espaço em disco insuficiente"):
            fake.embutir_legenda("video.mkv", "legenda.srt", str(tmp_path / "out.mkv"))


class TestAdaptadorMkvToolNixFFmpeg:
    """Testes do adaptador de infraestrutura com isolamento de processos externos."""

    def test_listar_trilhas_delega_para_manipulador_mkv(self, mocker):
        mock_listar = mocker.patch.object(
            ManipuladorMkv,
            "listar_trilhas",
            return_value=[
                TrilhaMidia(id=0, tipo="video", codec="HEVC"),
                TrilhaMidia(id=1, tipo="subtitles", idioma="por", formato=".srt"),
            ],
        )
        adaptador = AdaptadorMkvToolNixFFmpeg()
        trilhas = adaptador.listar_trilhas("arquivo.mkv")
        mock_listar.assert_called_once_with("arquivo.mkv")
        assert len(trilhas) == 2
        assert trilhas[1].idioma == "por"

    def test_listar_trilhas_via_subprocess_mkvmerge(self, mocker):
        mocker.patch.object(GerenciadorConfig, "check_dependencies", return_value=True)
        mocker.patch.object(GerenciadorConfig, "get_mkv_bins", return_value=("mkvmerge.exe", "mkvextract.exe"))

        saida_json = (
            '{"tracks": ['
            '{"id": 0, "type": "video", "codec": "MPEG-4p10", "properties": {}},'
            '{"id": 1, "type": "audio", "codec": "AAC", "properties": {"language": "jpn"}},'
            '{"id": 2, "type": "subtitles", "codec": "SubStationAlpha", "properties": {"language": "por", "codec_id": "S_TEXT/ASS"}}'
            ']}'
        )
        mock_run = mocker.patch(
            "subprocess.run",
            return_value=subprocess.CompletedProcess(args=["mkvmerge"], returncode=0, stdout=saida_json),
        )

        adaptador = AdaptadorMkvToolNixFFmpeg()
        trilhas = adaptador.listar_trilhas("Episodio.mkv")
        assert len(trilhas) == 3
        assert trilhas[0].tipo == "video"
        assert trilhas[1].tipo == "audio"
        assert trilhas[1].idioma == "jpn"
        assert trilhas[2].tipo == "subtitles"
        assert trilhas[2].idioma == "por"
        assert trilhas[2].formato == ".ass"

    def test_extrair_legenda_delega_para_extrair_trilha(self, mocker, tmp_path):
        mock_extrair = mocker.patch.object(
            ManipuladorMkv,
            "extrair_trilha",
            return_value=str(tmp_path / "saida.ass"),
        )
        adaptador = AdaptadorMkvToolNixFFmpeg()
        destino = str(tmp_path / "saida.ass")
        resultado = adaptador.extrair_legenda("video.mkv", 3, destino)

        mock_extrair.assert_called_once_with("video.mkv", 3, destino)
        assert resultado == destino

    def test_extrair_legenda_em_diretorio_constroi_nome_arquivo(self, mocker, tmp_path):
        mock_extrair = mocker.patch.object(
            ManipuladorMkv,
            "extrair_trilha",
            side_effect=lambda arq, id_t, dest: dest,
        )
        adaptador = AdaptadorMkvToolNixFFmpeg()
        destino_dir = str(tmp_path / "pasta_extraida")
        resultado = adaptador.extrair_legenda("C:/videos/Ep01.mkv", 2, destino_dir)

        assert resultado.endswith("Ep01_trilha_2.ass")
        assert os.path.dirname(resultado) == os.path.abspath(destino_dir)

    def test_extrair_audio_delega_para_manipulador_mkv(self, mocker, tmp_path):
        audio_gerado = str(tmp_path / "temp_audio.wav")
        with open(audio_gerado, "w", encoding="utf-8") as f:
            f.write("audio")

        mock_extrair = mocker.patch.object(
            ManipuladorMkv,
            "extrair_audio",
            return_value=(audio_gerado, "jpn"),
        )
        adaptador = AdaptadorMkvToolNixFFmpeg()
        destino_final = str(tmp_path / "Ep01_AUDIO.wav")
        res = adaptador.extrair_audio("Ep01.mkv", destino_final)

        assert res == destino_final
        assert os.path.exists(destino_final)

    def test_embutir_legenda_delega_para_manipulador_mkv(self, mocker, tmp_path):
        saida_esperada = str(tmp_path / "video_final.mkv")
        mock_embutir = mocker.patch.object(
            ManipuladorMkv,
            "embutir_legenda",
            return_value=saida_esperada,
        )
        logs = []
        adaptador = AdaptadorMkvToolNixFFmpeg(logger=logs.append)
        res = adaptador.embutir_legenda("video.mkv", "legenda.srt", saida_esperada, idioma="pt-br")

        mock_embutir.assert_called_once_with(
            caminho_mkv_original="video.mkv",
            caminho_legenda_traduzida="legenda.srt",
            caminho_saida=saida_esperada,
            idioma_destino="pt-br",
            logger=adaptador._logger,
        )
        assert res == saida_esperada


class TestIntegracaoProcessadorMkvComManipuladorMidia:
    """Testes de integração do ProcessadorMkv com a porta ManipuladorMidiaPort e Fake."""

    def test_processador_mkv_instancia_adaptador_padrao_quando_none(self):
        proc = ProcessadorMkv(
            log_cb=lambda m: None,
            progress_cb=lambda p: None,
            ask_overwrite_cb=lambda f: True,
            is_running_cb=lambda: True,
        )
        assert isinstance(proc.manipulador_midia, AdaptadorMkvToolNixFFmpeg)

    def test_processador_mkv_aceita_fake_injetado(self):
        fake = FakeManipuladorMidia()
        proc = ProcessadorMkv(
            log_cb=lambda m: None,
            progress_cb=lambda p: None,
            ask_overwrite_cb=lambda f: True,
            is_running_cb=lambda: True,
            manipulador_midia=fake,
        )
        assert proc.manipulador_midia is fake

    def test_fabrica_processadores_injeta_manipulador_midia(self):
        fake = FakeManipuladorMidia()
        proc = FabricaProcessadores.get_processor(
            filepath="video.mkv",
            log_cb=lambda m: None,
            progress_cb=lambda p: None,
            ask_overwrite_cb=lambda f: True,
            is_running_cb=lambda: True,
            manipulador_midia=fake,
        )
        assert isinstance(proc, ProcessadorMkv)
        assert proc.manipulador_midia is fake

    def test_prepare_com_fake_extrai_legenda_sem_binarios(self, tmp_path, mocker):
        mocker.patch.object(GerenciadorConfig, "check_dependencies", return_value=True)
        mocker.patch.object(PreferenciasUsuario, "obter", return_value=False)

        trilhas = [
            TrilhaMidia(id=0, tipo="video"),
            TrilhaMidia(id=1, tipo="subtitles", idioma="ja", formato=".ass"),
            TrilhaMidia(id=2, tipo="subtitles", idioma="por", formato=".srt"),
        ]
        fake = FakeManipuladorMidia(trilhas=trilhas)
        proc = ProcessadorMkv(
            log_cb=lambda m: None,
            progress_cb=lambda p: None,
            ask_overwrite_cb=lambda f: True,
            is_running_cb=lambda: True,
            manipulador_midia=fake,
            output_dir=str(tmp_path),
        )

        caminho_extraido, idioma = proc.prepare("anime_ep01.mkv", "por")
        assert idioma == "por"
        assert caminho_extraido.endswith("anime_ep01_ORIGINAL.srt")
        assert os.path.exists(caminho_extraido)
        assert len(fake.chamadas_extrair_legenda) == 1
        assert fake.chamadas_extrair_legenda[0][1] == 2

    def test_prepare_com_fake_rejeita_video_sem_legenda(self, tmp_path, mocker):
        mocker.patch.object(GerenciadorConfig, "check_dependencies", return_value=True)
        mocker.patch.object(PreferenciasUsuario, "obter", return_value=False)

        trilhas_apenas_audio = [
            TrilhaMidia(id=0, tipo="video"),
            TrilhaMidia(id=1, tipo="audio", idioma="ja"),
        ]
        fake = FakeManipuladorMidia(trilhas=trilhas_apenas_audio)
        proc = ProcessadorMkv(
            log_cb=lambda m: None,
            progress_cb=lambda p: None,
            ask_overwrite_cb=lambda f: True,
            is_running_cb=lambda: True,
            manipulador_midia=fake,
            output_dir=str(tmp_path),
        )

        with pytest.raises(ValueError, match="Nenhuma legenda"):
            proc.prepare("video_mudo.mkv", "auto")

    def test_finalize_com_fake_chama_embutir_legenda(self, tmp_path):
        fake = FakeManipuladorMidia()
        proc = ProcessadorMkv(
            log_cb=lambda m: None,
            progress_cb=lambda p: None,
            ask_overwrite_cb=lambda f: True,
            is_running_cb=lambda: True,
            manipulador_midia=fake,
        )

        caminhos_saida = {
            "legenda": str(tmp_path / "legenda_traduzida.srt"),
            "video": str(tmp_path / "video_saida.mkv"),
        }
        with open(caminhos_saida["legenda"], "w", encoding="utf-8") as f:
            f.write("legenda traduzida")

        proc.finalize(
            origem="video.mkv",
            legenda_traduzida=caminhos_saida["legenda"],
            caminhos_saida=caminhos_saida,
            idioma_destino="pt-br",
            arq_trabalho=None,
            manter_legenda=True,
        )

        assert len(fake.chamadas_embutir_legenda) == 1
        chamada = fake.chamadas_embutir_legenda[0]
        assert chamada[0] == "video.mkv"
        assert chamada[1] == caminhos_saida["legenda"]
        assert chamada[2] == caminhos_saida["video"]
        assert chamada[3] == "pt-br"
