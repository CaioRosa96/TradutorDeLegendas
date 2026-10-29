"""Testes unitários para o módulo de transcrição de áudio (Whisperfile) e extração de áudio MKV."""

import json
import os
import subprocess
from dataclasses import FrozenInstanceError
from types import SimpleNamespace

import pytest

from tradutor.config import GerenciadorConfig
from tradutor.config_usuario import PreferenciasUsuario
from tradutor.estrategias.processador_mkv import ProcessadorMkv
from tradutor.manipulador_mkv import ManipuladorMkv
from tradutor.transcritores import (
    DiagnosticoAudioWhisper,
    ITranscritor,
    MotorWhisperfile,
    RecomendadorModeloWhisper,
    ResultadoTranscricao,
    StatusWhisper,
)


def test_resultado_transcricao_imutavel():
    """Garante que ResultadoTranscricao é um Value Object congelado (frozen=True)."""
    res = ResultadoTranscricao(caminho_srt="teste.srt", idioma_detectado="ja", duracao_segundos=1.5)
    assert res.caminho_srt == "teste.srt"
    assert res.idioma_detectado == "ja"
    assert res.duracao_segundos == 1.5
    assert StatusWhisper.PRONTO.value == "pronto"

    with pytest.raises(FrozenInstanceError):
        res.caminho_srt = "outro.srt"  # type: ignore[misc]


@pytest.mark.parametrize(
    "entrada,esperado",
    [
        ("jpn", "ja"),
        ("eng", "en"),
        ("por", "pt"),
        ("chi", "zh"),
        ("zho", "zh"),
        ("und", "auto"),
        (None, "auto"),
    ],
)
def test_normalizar_idioma_whisper(entrada, esperado):
    """Converte códigos ISO-639-2 do MKV para códigos ISO-639-1 esperados pelo whisper.cpp."""
    assert MotorWhisperfile._normalizar_idioma_whisper(entrada) == esperado


def test_resolver_executavel_em_diretorio_execucao(tmp_path, mocker):
    """Localiza o binário whisper-small.exe dentro da subpasta bin/ do projeto respeitando o modelo preferido."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    fake_tiny = bin_dir / "whisper-tiny.exe"
    fake_tiny.write_text("t" * 2048, encoding="utf-8")
    fake_small = bin_dir / "whisper-small.exe"
    fake_small.write_text("s" * 2048, encoding="utf-8")

    mocker.patch.object(GerenciadorConfig, "DIRETORIO_EXECUCAO", str(tmp_path))
    mocker.patch.object(GerenciadorConfig, "DIRETORIO_RECURSOS", str(tmp_path))
    mocker.patch.object(
        PreferenciasUsuario,
        "obter",
        side_effect=lambda chave, padrao=None: "small" if chave == "modelo_whisper" else "",
    )

    motor = MotorWhisperfile()
    assert motor.esta_disponivel() is True
    assert motor.resolver_executavel() == os.path.abspath(str(fake_small))
    assert MotorWhisperfile.esta_modelo_instalado("small") is True
    assert MotorWhisperfile.esta_modelo_instalado("medium") is False


def test_transcrever_sucesso_com_flag_idioma_e_create_no_window(tmp_path, mocker):
    """Executa o Whisperfile gerando .srt com flag -l convertida e sem abrir janela de console."""
    fake_exe = tmp_path / "whisper-base.exe"
    fake_exe.write_text("exe", encoding="utf-8")
    fake_audio = tmp_path / "episodio_ORIGINAL_AUDIO.wav"
    fake_audio.write_text("wav", encoding="utf-8")
    fake_srt = tmp_path / "episodio_ORIGINAL_AUDIO.wav.srt"
    fake_srt.write_text("1\n00:00:01,000 --> 00:00:02,000\nOlá\n", encoding="utf-8")

    mock_run = mocker.patch(
        "subprocess.run",
        return_value=SimpleNamespace(returncode=0, stdout="ok", stderr=""),
    )

    motor = MotorWhisperfile(caminho_executavel=str(fake_exe))
    resultado = motor.transcrever(str(fake_audio), idioma="jpn")

    assert isinstance(motor, ITranscritor)
    assert resultado.caminho_srt == str(fake_srt)
    assert resultado.idioma_detectado == "ja"

    mock_run.assert_called_once()
    args_chamada, kwargs_chamada = mock_run.call_args
    comando = args_chamada[0]
    assert comando == [str(fake_exe.resolve()), "-f", str(fake_audio), "-osrt", "-l", "ja", "-mc", "0"]
    if os.name == "nt":
        assert kwargs_chamada.get("creationflags") == subprocess.CREATE_NO_WINDOW


def test_transcrever_fallback_nome_srt_sem_extensao_audio(tmp_path, mocker):
    """Aceita o arquivo <base>.srt quando o Whisperfile não concatena .wav.srt."""
    fake_exe = tmp_path / "whisper-base.exe"
    fake_exe.write_text("exe", encoding="utf-8")
    fake_audio = tmp_path / "audio_temp.wav"
    fake_audio.write_text("wav", encoding="utf-8")
    fake_srt_alternativo = tmp_path / "audio_temp.srt"
    fake_srt_alternativo.write_text("1\n00:00:01,000 --> 00:00:02,000\nTeste\n", encoding="utf-8")

    mocker.patch(
        "subprocess.run",
        return_value=SimpleNamespace(returncode=0, stdout="ok", stderr=""),
    )

    motor = MotorWhisperfile(caminho_executavel=str(fake_exe))
    resultado = motor.transcrever(str(fake_audio), idioma="auto")

    assert resultado.caminho_srt == str(fake_srt_alternativo)
    assert resultado.idioma_detectado == "auto"


def test_transcrever_erros_binario_ausente_e_returncode(tmp_path, mocker):
    """Levanta FileNotFoundError sem binário e RuntimeError se o subprocesso falhar."""
    mocker.patch.object(GerenciadorConfig, "DIRETORIO_EXECUCAO", str(tmp_path))
    mocker.patch.object(GerenciadorConfig, "DIRETORIO_RECURSOS", str(tmp_path))
    mocker.patch.object(PreferenciasUsuario, "obter", return_value="")
    mocker.patch("shutil.which", return_value=None)

    motor_sem_bin = MotorWhisperfile()
    with pytest.raises(FileNotFoundError, match="Whisperfile"):
        motor_sem_bin.transcrever(str(tmp_path / "inexistente.wav"))

    fake_exe = tmp_path / "whisper-base.exe"
    fake_exe.write_text("exe", encoding="utf-8")
    fake_audio = tmp_path / "audio.wav"
    fake_audio.write_text("wav", encoding="utf-8")

    mocker.patch(
        "subprocess.run",
        return_value=SimpleNamespace(returncode=2, stdout="", stderr="formato invalido"),
    )
    motor = MotorWhisperfile(caminho_executavel=str(fake_exe))
    with pytest.raises(RuntimeError, match="formato invalido"):
        motor.transcrever(str(fake_audio), idioma="eng")


def test_manipulador_mkv_extrair_audio_com_ffmpeg_converte_para_wav_16khz(tmp_path, mocker):
    """Converte áudio AAC/Opus do MKV para WAV 16 kHz mono quando o FFmpeg está disponível."""
    mocker.patch.object(GerenciadorConfig, "get_mkv_bins", return_value=("mkvmerge.exe", "mkvextract.exe"))
    mocker.patch.object(ManipuladorMkv, "_localizar_ffmpeg", return_value="C:/ffmpeg/ffmpeg.exe")

    info_mkv = {
        "tracks": [
            {"id": 0, "type": "video", "codec": "HEVC", "properties": {"language": "jpn"}},
            {
                "id": 1,
                "type": "audio",
                "codec": "AAC",
                "properties": {"codec_id": "A_AAC", "language": "jpn"},
            },
        ]
    }

    mock_run = mocker.patch(
        "subprocess.run",
        side_effect=[
            SimpleNamespace(returncode=0, stdout=json.dumps(info_mkv), stderr=""),
            SimpleNamespace(returncode=0, stdout="", stderr=""),
        ],
    )

    caminho_mkv = str(tmp_path / "Anime_Ep01.mkv")
    caminho_audio, idioma_real = ManipuladorMkv.extrair_audio(
        caminho_mkv, str(tmp_path), "jpn", lambda msg: None
    )

    assert idioma_real == "jpn"
    assert caminho_audio.endswith("Anime_Ep01_ORIGINAL_AUDIO.wav")
    cmd_ffmpeg = mock_run.call_args_list[1][0][0]
    assert cmd_ffmpeg[0] == "C:/ffmpeg/ffmpeg.exe"
    assert "-ar" in cmd_ffmpeg and "16000" in cmd_ffmpeg
    assert "-ac" in cmd_ffmpeg and "1" in cmd_ffmpeg
    assert "pcm_s16le" in cmd_ffmpeg


def test_manipulador_mkv_embutir_legenda_define_default_track_flag(tmp_path, mocker):
    """Garante que embutir_legenda marca a nova legenda traduzida como faixa padrão (0:yes)."""
    mocker.patch.object(GerenciadorConfig, "get_mkv_bins", return_value=("mkvmerge.exe", "mkvextract.exe"))
    mock_run = mocker.patch(
        "subprocess.run",
        return_value=SimpleNamespace(returncode=0, stdout="", stderr=""),
    )

    saida = ManipuladorMkv.embutir_legenda(
        "video.mkv", "legenda_PT.srt", str(tmp_path / "video_PT.mkv"), "pt-br", lambda msg: None
    )

    assert saida == str(tmp_path / "video_PT.mkv")
    cmd_mux = mock_run.call_args[0][0]
    assert "--default-track-flag" in cmd_mux
    idx = cmd_mux.index("--default-track-flag")
    assert cmd_mux[idx + 1] == "0:yes"


def test_processador_mkv_fallback_whisper_quando_sem_legenda(tmp_path, mocker):
    """Aciona extração de áudio e transcrição Whisperfile quando o MKV não possui legendas."""
    mocker.patch.object(GerenciadorConfig, "check_dependencies", return_value=True)
    mocker.patch.object(
        ManipuladorMkv,
        "extrair_legenda",
        side_effect=ValueError("Nenhuma legenda (.ass ou .srt) encontrada neste MKV."),
    )

    audio_temp = tmp_path / "Ep01_ORIGINAL_AUDIO.wav"
    audio_temp.write_text("audio bruto", encoding="utf-8")
    srt_gerado = tmp_path / "Ep01_ORIGINAL_AUDIO.wav.srt"
    srt_gerado.write_text("1\n00:00:01,000 --> 00:00:02,000\nKonnichiwa\n", encoding="utf-8")

    mocker.patch.object(
        ManipuladorMkv,
        "extrair_audio",
        return_value=(str(audio_temp), "jpn"),
    )

    def _obter_pref(chave, padrao=None):
        mapa = {
            "transcricao_habilitada": True,
            "forcar_transcricao": False,
            "caminho_whisperfile": "",
        }
        return mapa.get(chave, padrao)

    mocker.patch.object(PreferenciasUsuario, "obter", side_effect=_obter_pref)
    mocker.patch.object(MotorWhisperfile, "esta_disponivel", return_value=True)
    mocker.patch.object(
        MotorWhisperfile,
        "transcrever",
        return_value=ResultadoTranscricao(caminho_srt=str(srt_gerado), idioma_detectado="ja", duracao_segundos=2.1),
    )

    proc = ProcessadorMkv(
        log_cb=lambda m: None,
        progress_cb=lambda p: None,
        ask_overwrite_cb=lambda f: True,
        is_running_cb=lambda: True,
    )

    caminho_mkv = str(tmp_path / "Ep01.mkv")
    arq_trabalho, idioma_detectado = proc.prepare(caminho_mkv, "jpn")

    assert idioma_detectado == "jpn"
    assert arq_trabalho == str(tmp_path / "Ep01_ORIGINAL.srt")
    assert os.path.exists(arq_trabalho)
    assert not os.path.exists(str(audio_temp)), "O arquivo de áudio temporário deve ser removido após a transcrição"



def test_manipulador_mkv_extrair_audio_fallback_mkvextract_sem_ffmpeg(tmp_path, mocker):
    """Usa mkvextract diretamente quando o FFmpeg não está disponível no sistema."""
    mocker.patch.object(GerenciadorConfig, "get_mkv_bins", return_value=("mkvmerge.exe", "mkvextract.exe"))
    mocker.patch.object(ManipuladorMkv, "_localizar_ffmpeg", return_value=None)

    info_mkv = {
        "tracks": [
            {
                "id": 2,
                "type": "audio",
                "codec": "FLAC",
                "properties": {"codec_id": "A_FLAC", "language": "eng"},
            }
        ]
    }

    mock_run = mocker.patch(
        "subprocess.run",
        side_effect=[
            SimpleNamespace(returncode=0, stdout=json.dumps(info_mkv), stderr=""),
            SimpleNamespace(returncode=0, stdout="", stderr=""),
        ],
    )

    caminho_mkv = str(tmp_path / "Filme.mkv")
    caminho_audio, idioma_real = ManipuladorMkv.extrair_audio(
        caminho_mkv, str(tmp_path), "eng", lambda msg: None
    )

    assert idioma_real == "eng"
    assert caminho_audio.endswith("Filme_ORIGINAL_AUDIO.flac")
    cmd_extract = mock_run.call_args_list[1][0][0]
    assert cmd_extract[0] == "mkvextract.exe"
    assert cmd_extract[1] == "tracks"


def test_processador_mkv_rejeita_video_sem_legenda_quando_transcricao_desativada(tmp_path, mocker):
    """Propaga ValueError quando o vídeo não tem legenda e transcricao_habilitada é False."""
    mocker.patch.object(GerenciadorConfig, "check_dependencies", return_value=True)
    mocker.patch.object(
        ManipuladorMkv,
        "extrair_legenda",
        side_effect=ValueError("Nenhuma legenda (.ass ou .srt) encontrada neste MKV."),
    )
    mocker.patch.object(PreferenciasUsuario, "obter", return_value=False)

    proc = ProcessadorMkv(
        log_cb=lambda m: None,
        progress_cb=lambda p: None,
        ask_overwrite_cb=lambda f: True,
        is_running_cb=lambda: True,
    )

    with pytest.raises(ValueError, match="Nenhuma legenda"):
        proc.prepare(str(tmp_path / "SemLegenda.mkv"), "jpn")



def test_processador_mkv_solicita_permissao_previa_usuario_para_ia_local(tmp_path, mocker):
    """Pede permissão via callback ask_whisper_cb antes de usar a IA local e aborta se recusado."""
    mocker.patch.object(GerenciadorConfig, "check_dependencies", return_value=True)
    mocker.patch.object(
        ManipuladorMkv,
        "extrair_legenda",
        side_effect=ValueError("Nenhuma legenda (.ass ou .srt) encontrada neste MKV."),
    )
    mocker.patch.object(PreferenciasUsuario, "obter", return_value=False)

    chamadas_permissao = []

    def _recusar_ia(nome_arquivo):
        chamadas_permissao.append(nome_arquivo)
        return False

    proc = ProcessadorMkv(
        log_cb=lambda m: None,
        progress_cb=lambda p: None,
        ask_overwrite_cb=lambda f: True,
        is_running_cb=lambda: True,
        ask_whisper_cb=_recusar_ia,
    )

    arq_trabalho, idioma = proc.prepare(str(tmp_path / "Replay_TFT.mkv"), "auto")
    assert chamadas_permissao == ["Replay_TFT.mkv"]
    assert arq_trabalho is None
    assert idioma is None


def test_recomendador_whisper_analisa_video_com_musica_e_und(tmp_path, mocker):
    """Recomenda Small ou Medium (descartando Tiny) quando detecta música de fundo e idioma indefinido."""
    video_fake = tmp_path / "Replay_TFT.mkv"
    video_fake.write_text("mkv", encoding="utf-8")

    mocker.patch.object(GerenciadorConfig, "get_mkv_bins", return_value=("mkvmerge.exe", "mkvextract.exe"))
    mocker.patch.object(ManipuladorMkv, "_localizar_ffmpeg", return_value="C:/ffmpeg/ffmpeg.exe")
    mocker.patch.object(RecomendadorModeloWhisper, "obter_recursos_sistema", return_value=(12.0, 8))

    info_mkv = {
        "container": {"properties": {"duration": 62_000_000_000}},
        "tracks": [{"id": 1, "type": "audio", "properties": {"language": "und", "audio_channels": 2}}],
    }
    saida_ffmpeg = "[silencedetect @ 001] silence_start: 10.0\n[silencedetect @ 001] silence_end: 11.5 | silence_duration: 1.5\n"

    mocker.patch(
        "subprocess.run",
        side_effect=[
            SimpleNamespace(returncode=0, stdout=json.dumps(info_mkv), stderr=""),
            SimpleNamespace(returncode=0, stdout="", stderr=saida_ffmpeg),
        ],
    )

    diag = RecomendadorModeloWhisper.analisar_arquivo(str(video_fake))
    assert isinstance(diag, DiagnosticoAudioWhisper)
    assert diag.duracao_segundos == 62.0
    assert diag.idioma_audio == "und"
    assert diag.possui_fundo_musical is True
    assert diag.modelo_recomendado == "small"
    assert diag.modelo_alternativo == "medium"


def test_recomendador_whisper_decisao_voz_limpa_e_ram_baixa():
    """Recomenda Tiny para vídeos longos com voz limpa ou computadores com pouca memória RAM livre."""
    mod_limpo, alt_limpo, motivo_limpo = RecomendadorModeloWhisper._decidir_modelo(
        duracao_segundos=1500.0,
        idioma_audio="eng",
        canais_audio=2,
        possui_fundo_musical=False,
        proporcao_silencio=0.35,
        ram_livre_gb=8.0,
    )
    assert mod_limpo == "tiny"
    assert alt_limpo == "small"
    assert motivo_limpo == "diag_motivo_voz_limpa_longo"

    mod_ram, _, motivo_ram = RecomendadorModeloWhisper._decidir_modelo(
        duracao_segundos=120.0,
        idioma_audio="jpn",
        canais_audio=2,
        possui_fundo_musical=True,
        proporcao_silencio=0.05,
        ram_livre_gb=1.8,
    )
    assert mod_ram == "tiny"
    assert motivo_ram == "diag_motivo_ram_baixa"


def test_identificar_mkvs_sem_legenda_filtra_apenas_videos_que_usarao_ia(mocker):
    """Identifica exatamente quais arquivos MKV da fila não possuem legenda embutida."""
    mocker.patch.object(GerenciadorConfig, "check_dependencies", return_value=True)
    mocker.patch.object(GerenciadorConfig, "get_mkv_bins", return_value=("mkvmerge.exe", "mkvextract.exe"))

    mkv_com_legenda = {
        "tracks": [
            {"id": 0, "type": "video", "codec": "HEVC"},
            {"id": 1, "type": "subtitles", "codec": "SubRip/SRT", "properties": {"codec_id": "S_TEXT/UTF8"}},
        ]
    }
    mkv_sem_legenda = {
        "tracks": [
            {"id": 0, "type": "video", "codec": "AVC"},
            {"id": 1, "type": "audio", "codec": "AAC", "properties": {"codec_id": "A_AAC", "language": "und"}},
        ]
    }

    mocker.patch(
        "subprocess.run",
        side_effect=[
            SimpleNamespace(returncode=0, stdout=json.dumps(mkv_com_legenda), stderr=""),
            SimpleNamespace(returncode=0, stdout=json.dumps(mkv_sem_legenda), stderr=""),
        ],
    )

    sem_legenda = ManipuladorMkv.identificar_mkvs_sem_legenda(["Anime_Ep01.mkv", "Replay_TFT.mkv"])
    assert sem_legenda == {"Replay_TFT.mkv"}


@pytest.mark.parametrize("ext", [".mkv", ".mp4", ".webm", ".avi", ".wmv"])
def test_fabrica_suporta_todos_conteineres_de_video(ext):
    """Garante que FabricaProcessadores roteia .mkv, .mp4, .webm, .avi e .wmv para ProcessadorMkv."""
    from tradutor.estrategias.fabrica import FabricaProcessadores

    proc = FabricaProcessadores.get_processor(
        f"video_teste{ext}",
        log_cb=lambda m: None,
        progress_cb=lambda c, t: None,
        ask_overwrite_cb=lambda n: True,
        is_running_cb=lambda: True,
    )
    assert isinstance(proc, ProcessadorMkv)


def test_politica_formato_saida_mp4_webm_avi_wmv(tmp_path, mocker):
    """Valida as 3 opções de saída ('converter_mkv', 'manter_original', 'perguntar') para formatos não-MKV."""
    arq_trabalho = str(tmp_path / "clipe_ORIGINAL.ass")

    # 1. Modo converter_mkv (MP4 -> MKV preservando .ass)
    mocker.patch.object(PreferenciasUsuario, "obter", return_value="converter_mkv")
    proc = ProcessadorMkv(lambda m: None, lambda c, t: None, lambda n: True, lambda: True)
    caminhos_mkv = proc.get_output_paths(str(tmp_path / "clipe.mp4"), "pt", arq_trabalho)
    assert caminhos_mkv["video"].endswith("clipe_PT.mkv")
    assert caminhos_mkv["legenda"].endswith("clipe_PT.ass")

    # 2. Modo manter_original para MP4 (converte legenda para .srt e saída .mp4)
    mocker.patch.object(PreferenciasUsuario, "obter", return_value="manter_original")
    caminhos_mp4 = proc.get_output_paths(str(tmp_path / "clipe.mp4"), "pt", arq_trabalho)
    assert caminhos_mp4["video"].endswith("clipe_PT.mp4")
    assert caminhos_mp4["legenda"].endswith("clipe_PT.srt")

    # 3. Modo manter_original para AVI/WMV (mantém apenas legenda .srt externa, video=None)
    caminhos_wmv = proc.get_output_paths(str(tmp_path / "clipe.wmv"), "pt", arq_trabalho)
    assert caminhos_wmv["video"] is None
    assert caminhos_wmv["legenda"].endswith("clipe_PT.srt")

    # 4. Modo perguntar delegando ao callback ask_output_format_cb
    mocker.patch.object(PreferenciasUsuario, "obter", return_value="perguntar")
    proc_ask = ProcessadorMkv(
        lambda m: None,
        lambda c, t: None,
        lambda n: True,
        lambda: True,
        ask_output_format_cb=lambda nome, ext: "manter_original",
    )
    caminhos_webm = proc_ask.get_output_paths(str(tmp_path / "clipe.webm"), "pt", arq_trabalho)
    assert caminhos_webm["video"].endswith("clipe_PT.webm")


def test_embutir_legenda_mp4_e_webm_usa_codecs_corretos_ffmpeg(tmp_path, mocker):
    """Garante que embutir_legenda usa mov_text para .mp4 e webvtt para .webm via FFmpeg."""
    mocker.patch.object(ManipuladorMkv, "_localizar_ffmpeg", return_value="C:/ffmpeg/ffmpeg.exe")
    mock_run = mocker.patch(
        "subprocess.run",
        return_value=SimpleNamespace(returncode=0, stdout="", stderr=""),
    )

    saida_mp4 = str(tmp_path / "video_PT.mp4")
    ManipuladorMkv.embutir_legenda("video.mp4", "leg_PT.srt", saida_mp4, "pt-br", lambda m: None)
    cmd_mp4 = mock_run.call_args_list[0][0][0]
    assert "mov_text" in cmd_mp4

    saida_webm = str(tmp_path / "video_PT.webm")
    ManipuladorMkv.embutir_legenda("video.webm", "leg_PT.srt", saida_webm, "pt-br", lambda m: None)
    cmd_webm = mock_run.call_args_list[1][0][0]
    assert "webvtt" in cmd_webm


