"""Testes de regressão cobrindo os 10 pontos de correção identificados pelo /boost."""
from __future__ import annotations

import json
import logging
import os
import sys
import threading
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from tradutor.anilist import limpar_nome_anime, salvar_glossario_arquivo
from tradutor.cache import CacheTraducoes
from tradutor.cli import CodigoSaidaCli, executar_cli
from tradutor.config import GerenciadorConfig
from tradutor.config_usuario import PreferenciasUsuario
from tradutor.estrategias.processador_base import ProcessadorArquivoBase
from tradutor.estrategias.processador_mkv import ProcessadorMkv
from tradutor.estrategias.processador_srt import ProcessadorSrt
from tradutor.glossario_port import AdaptadorAniListGraphQL
from tradutor.logger import _LazyLogger, setup_logger
from tradutor.orquestrador import OrquestradorTraducoes
from tradutor.servico_traducao import ServicoTraducao
from tradutor.tradutores.base import ExcecaoDisjuntorAberto
from tradutor.transcritores.whisperfile import MotorWhisperfile


# ---------------------------------------------------------------------------
# 1. Bug 1.1: limpar_nome_anime com caminhos absolutos
# ---------------------------------------------------------------------------
def test_regressao_limpar_nome_anime_com_caminhos_absolutos_e_diretorios():
    """Garante que limpar_nome_anime remove diretórios absolutos (Windows e Unix)."""
    caminho_win = r"C:\Animes\Bleach\[SubsPlease] Bleach - Thousand-Year Blood War - 30 (1080p).mkv"
    assert limpar_nome_anime(caminho_win) == "Bleach Thousand Year Blood War"

    caminho_unix = "/media/storage/animes/[Erai-raws] One Piece - 1098 [1080p][Multiple Subtitle].mkv"
    assert limpar_nome_anime(caminho_unix) == "One Piece"

    caminho_misto = "D:/Downloads\\Animes/[Judas] TenKen - S02E07.mkv"
    assert limpar_nome_anime(caminho_misto) == "TenKen"

    # Suporte a Path e caminhos com barra final
    caminho_path = Path(r"C:\Animes\Bleach\[SubsPlease] Bleach - 01.mkv")
    assert limpar_nome_anime(caminho_path) == "Bleach"

    caminho_barra_final = "C:/Animes/Bleach/"
    assert limpar_nome_anime(caminho_barra_final) == "Bleach"


# ---------------------------------------------------------------------------
# 2. Bug 1.2: os.makedirs('') com arquivo no diretório atual
# ---------------------------------------------------------------------------
def test_regressao_makedirs_diretorio_vazio_nao_lanca_winerror_3(mocker, tmp_path, monkeypatch):
    """Garante que processadores não chamam os.makedirs com string vazia."""
    spy_makedirs = mocker.spy(os, "makedirs")

    proc_mkv = ProcessadorMkv(
        log_cb=lambda _: None,
        progress_cb=lambda *_: None,
        ask_overwrite_cb=lambda _: True,
        is_running_cb=lambda: True,
        output_dir=None,
    )
    caminhos_mkv = proc_mkv.get_output_paths("video.mkv", "pt", "video_ORIGINAL.srt")
    assert caminhos_mkv["legenda"] == "video_PT.srt"
    assert caminhos_mkv["video"] == "video_PT.mkv"

    proc_srt = ProcessadorSrt(
        log_cb=lambda _: None,
        progress_cb=lambda *_: None,
        ask_overwrite_cb=lambda _: True,
        is_running_cb=lambda: True,
        output_dir=None,
    )
    caminhos_srt = proc_srt.get_output_paths("legenda.srt", "pt", "legenda.srt")
    assert caminhos_srt["legenda"] == "legenda_PT.srt"

    # Valida que salvar_glossario_arquivo com pasta_destino vazia não quebra
    monkeypatch.chdir(tmp_path)
    arq_gloss = salvar_glossario_arquivo(
        pasta_destino="",
        titulo="Anime Vazio",
        anime_id=999,
        nome_limpo="Anime Vazio",
        nomes=["Hero"],
    )
    assert arq_gloss is not None
    assert os.path.isfile(arq_gloss)

    for chamada in spy_makedirs.call_args_list:
        caminho_passado = chamada[0][0]
        assert caminho_passado != "", "os.makedirs não deve ser chamado com string vazia"


# ---------------------------------------------------------------------------
# 3. Bug 1.3: Metadados CLI --keep-external-sub reportando legenda correta
# ---------------------------------------------------------------------------
def test_regressao_cli_keep_external_sub_retorna_caminho_legenda_correto(tmp_path, capsys):
    """Garante que o CLI reporta extensão de legenda (.srt/.ass), nunca .mkv, quando --keep-external-sub."""
    mkv_fake = tmp_path / "filme.mkv"
    mkv_fake.write_bytes(b"dummy")

    mock_proc = MagicMock()
    mock_proc.process.return_value = True
    # O processador real preenche ultimos_caminhos_saida
    mock_proc.ultimos_caminhos_saida = {
        "video": str(tmp_path / "filme_PT.mkv"),
        "legenda": str(tmp_path / "filme_PT.srt"),
    }
    mock_proc.get_output_paths.return_value = mock_proc.ultimos_caminhos_saida

    with patch("tradutor.estrategias.fabrica.FabricaProcessadores.get_processor", return_value=mock_proc), \
         patch("tradutor.config.GerenciadorConfig.check_dependencies", return_value=True), \
         patch("tradutor.manipulador_mkv.ManipuladorMkv.listar_idiomas_legendas", return_value=["eng"]), \
         patch("tradutor.manipulador_mkv.ManipuladorMkv.identificar_mkvs_sem_legenda", return_value=set()):

        ret = executar_cli([
            "--headless",
            "-i", str(mkv_fake),
            "-d", "pt",
            "--keep-external-sub",
            "--json-output",
        ])

        assert ret == CodigoSaidaCli.SUCESSO
        captured = capsys.readouterr()
        payload = json.loads(captured.out.strip())
        assert payload["output_subtitle_path"] == str(tmp_path / "filme_PT.srt")
        assert not payload["output_subtitle_path"].endswith(".mkv")


def test_regressao_cli_legenda_avulsa_sem_keep_external_sub_retorna_caminho_legenda(tmp_path, capsys):
    """Garante que para legendas avulsas (.srt), o CLI reporta output_subtitle_path mesmo sem --keep-external-sub."""
    srt_fake = tmp_path / "legenda.srt"
    srt_fake.write_text("1\n00:00:00,000 --> 00:00:01,000\nHello\n", encoding="utf-8")

    mock_proc = MagicMock()
    mock_proc.process.return_value = True
    mock_proc.ultimos_caminhos_saida = {
        "video": None,
        "legenda": str(tmp_path / "legenda_PT.srt"),
    }
    mock_proc.get_output_paths.return_value = mock_proc.ultimos_caminhos_saida

    with patch("tradutor.estrategias.fabrica.FabricaProcessadores.get_processor", return_value=mock_proc):
        ret = executar_cli([
            "--headless",
            "-i", str(srt_fake),
            "-d", "pt",
            "--json-output",
        ])

        assert ret == CodigoSaidaCli.SUCESSO
        captured = capsys.readouterr()
        payload = json.loads(captured.out.strip())
        assert payload["output_subtitle_path"] == str(tmp_path / "legenda_PT.srt")
        assert payload["output_video_path"] is None


# ---------------------------------------------------------------------------
# 4. Bug 1.4: Limpeza de temporários ao cancelar ou falhar no processador base
# ---------------------------------------------------------------------------
class DummyProcessador(ProcessadorArquivoBase):
    def prepare(self, origem, idioma_origem):
        return self._temp_sub, "en"

    def should_skip_if_same_language(self):
        return False

    def cleanup_temporary(self, arq_trabalho):
        self.cleanup_chamado = True
        if arq_trabalho and "_ORIGINAL" in arq_trabalho and os.path.exists(arq_trabalho):
            os.remove(arq_trabalho)

    def get_output_paths(self, origem, idioma_destino, arq_trabalho):
        return {
            "legenda": self._final_sub,
            "video": None,
        }

    def get_translation_message(self):
        return "Traduzindo..."

    def finalize(self, origem, legenda_traduzida, caminhos_saida, idioma_destino, arq_trabalho, manter_legenda):
        pass


def test_regressao_cancelamento_limpa_arquivos_temporarios_processador_base(tmp_path, mocker):
    """Garante que cancelamento antes da finalização remove arquivos temporários."""
    mocker.patch("tradutor.glossario_port.AdaptadorAniListGraphQL.buscar_nomes_proprios", return_value=[])
    temp_orig = str(tmp_path / "teste_ORIGINAL.srt")
    with open(temp_orig, "w", encoding="utf-8") as f:
        f.write("1\n00:00:00,000 --> 00:00:01,000\nHello\n")

    final_sub = str(tmp_path / "teste_PT.srt")

    def _is_running():
        # Cancela logo após a tradução quando a legenda temporária da execução foi salva
        if os.path.exists(final_sub):
            return False
        return True

    proc = DummyProcessador(
        log_cb=lambda _: None,
        progress_cb=lambda *_: None,
        ask_overwrite_cb=lambda _: True,
        is_running_cb=_is_running,
    )
    proc._temp_sub = temp_orig
    proc._final_sub = final_sub
    proc.cleanup_chamado = False

    mock_engine = MagicMock()
    mock_engine.translate.return_value = "Olá"
    proc.engine = mock_engine

    resultado = proc.process(
        origem=str(tmp_path / "video.mkv"),
        idioma_origem="en",
        idioma_destino="pt",
        manter_legenda=False,
    )

    assert resultado is False
    assert proc.cleanup_chamado is True
    assert not os.path.exists(temp_orig)
    assert not os.path.exists(final_sub)


def test_regressao_cancelamento_preserva_legenda_preexistente(tmp_path, mocker):
    """Garante que cancelamento antes da gravação NÃO apaga legenda preexistente no destino."""
    mocker.patch("tradutor.glossario_port.AdaptadorAniListGraphQL.buscar_nomes_proprios", return_value=[])
    temp_orig = str(tmp_path / "teste_ORIGINAL.srt")
    with open(temp_orig, "w", encoding="utf-8") as f:
        f.write("1\n00:00:00,000 --> 00:00:01,000\nHello\n")

    final_sub = str(tmp_path / "teste_PT.srt")
    with open(final_sub, "w", encoding="utf-8") as f:
        f.write("Legenda preexistente do usuario intocada")

    proc = DummyProcessador(
        log_cb=lambda _: None,
        progress_cb=lambda *_: None,
        ask_overwrite_cb=lambda _: True,
        is_running_cb=lambda: False,  # Cancela antes de iniciar a tradução
    )
    proc._temp_sub = temp_orig
    proc._final_sub = final_sub
    proc.cleanup_chamado = False

    mock_engine = MagicMock()
    proc.engine = mock_engine

    resultado = proc.process(
        origem=str(tmp_path / "video.mkv"),
        idioma_origem="en",
        idioma_destino="pt",
        manter_legenda=False,
    )

    assert resultado is False
    assert proc.cleanup_chamado is True
    assert not os.path.exists(temp_orig)
    # A legenda preexistente do usuário NÃO deve ser apagada!
    assert os.path.exists(final_sub)
    with open(final_sub, "r", encoding="utf-8") as f:
        assert f.read() == "Legenda preexistente do usuario intocada"


def test_regressao_cancelamento_nao_deleta_origem_se_legenda_coincidir(tmp_path):
    """Garante que se caminho_legenda_final for idêntico a origem, a origem NUNCA é deletada."""
    arquivo_legenda = str(tmp_path / "mesmo_arquivo.srt")
    with open(arquivo_legenda, "w", encoding="utf-8") as f:
        f.write("1\n00:00:00,000 --> 00:00:01,000\nOriginal intacto\n")

    proc = DummyProcessador(
        log_cb=lambda _: None,
        progress_cb=lambda *_: None,
        ask_overwrite_cb=lambda _: True,
        is_running_cb=lambda: False,  # Simula cancelamento
    )
    proc._temp_sub = arquivo_legenda
    proc._final_sub = arquivo_legenda  # Mesmo caminho de origem
    proc.cleanup_chamado = False
    proc.engine = MagicMock()

    resultado = proc.process(
        origem=arquivo_legenda,
        idioma_origem="en",
        idioma_destino="pt",
        manter_legenda=False,
    )
    assert resultado is False
    # O arquivo de origem deve continuar existindo!
    assert os.path.exists(arquivo_legenda)


# ---------------------------------------------------------------------------
# 5. Bug 1.5: Orquestrador interrompe fila quando disjuntor abre
# ---------------------------------------------------------------------------
def test_regressao_orquestrador_aborta_fila_ao_disparar_disjuntor(mocker):
    """Garante que ExcecaoDisjuntorAberto interrompe o restante da fila sem tentar outros arquivos."""
    orquestrador = OrquestradorTraducoes()
    logs = []
    orquestrador.set_callbacks(
        log_cb=logs.append,
        progress_cb=lambda *_: None,
        ask_overwrite_cb=lambda _: True,
        finish_cb=lambda: None,
    )

    mock_proc1 = MagicMock()
    mock_proc1.process.side_effect = ExcecaoDisjuntorAberto("Circuit Breaker Aberto")

    mock_proc2 = MagicMock()
    mock_proc3 = MagicMock()

    mocker.patch(
        "tradutor.estrategias.fabrica.FabricaProcessadores.get_processor",
        side_effect=[mock_proc1, mock_proc2, mock_proc3],
    )

    fila = ["video1.mkv", "video2.mkv", "video3.mkv"]
    # Ativa flag de execução e processa sincronamente para teste
    orquestrador._is_running = True
    orquestrador._process_files(fila, "en", "pt", False)

    # Apenas o primeiro arquivo deve ter sido processado
    assert mock_proc1.process.call_count == 1
    assert mock_proc2.process.call_count == 0
    assert mock_proc3.process.call_count == 0
    assert any("Disjuntor aberto" in msg for msg in logs)


# ---------------------------------------------------------------------------
# 6. Bug 1.6: Contaminação do SQLite com TKGLOSS
# ---------------------------------------------------------------------------
def test_regressao_cache_nao_persiste_tokens_tkgloss(tmp_path):
    """Garante que tokens TKGLOSS são bloqueados em _salvar_cache_seguro e _salvar_lote_cache_seguro."""
    db_file = str(tmp_path / "cache_teste.db")
    cache = CacheTraducoes(db_file)

    servico = ServicoTraducao(
        logger=lambda _: None,
        progress_callback=lambda *_: None,
        is_cancelled_callback=lambda: False,
        engine=MagicMock(),
    )
    servico._cache = cache

    # 1. Tentativa unitária com TKGLOSS na chave ou no valor
    servico._salvar_cache_seguro("Texto com TKGLOSS0T", "en", "pt", "Texto traduzido")
    servico._salvar_cache_seguro("Texto original", "en", "pt", "Texto com TKGLOSS0T")
    assert cache.get("Texto com TKGLOSS0T", "en", "pt") is None
    assert cache.get("Texto original", "en", "pt") is None

    # 2. Tentativa em lote com itens limpos e itens contaminados
    lote = {
        "Frase limpa 1": "Traducao limpa 1",
        "Frase com TKGLOSS1T": "Traducao suja",
        "Outra frase limpa": "Outra traducao limpa",
        "Frase normal": "Traducao com TKGLOSS2T",
    }
    servico._salvar_lote_cache_seguro(lote, "en", "pt")

    assert cache.get("Frase limpa 1", "en", "pt") == "Traducao limpa 1"
    assert cache.get("Outra frase limpa", "en", "pt") == "Outra traducao limpa"
    assert cache.get("Frase com TKGLOSS1T", "en", "pt") is None
    assert cache.get("Frase normal", "en", "pt") is None


# ---------------------------------------------------------------------------
# 7. Bug 1.7: Cancelamento cooperativo e término de processo no MotorWhisperfile
# ---------------------------------------------------------------------------
def test_regressao_motor_whisperfile_cancelamento_cooperativo(tmp_path, mocker):
    """Garante cancelamento cooperativo via cancelado_cb e encerramento de processo."""
    fake_exe = tmp_path / "whisper.exe"
    fake_exe.write_text("bin", encoding="utf-8")
    fake_audio = tmp_path / "audio.wav"
    fake_audio.write_text("wav", encoding="utf-8")

    motor = MotorWhisperfile(caminho_executavel=str(fake_exe))

    mock_proc = MagicMock()
    mock_proc.poll.side_effect = [None, None]  # Processo ativo
    mock_proc.pid = 9999

    mocker.patch("subprocess.Popen", return_value=mock_proc)
    spy_encerrar = mocker.spy(MotorWhisperfile, "_encerrar_processo")

    cancelado = [False]

    def _cancelar_apos_primeira_checagem():
        if not cancelado[0]:
            cancelado[0] = True
            return False
        return True

    with pytest.raises(RuntimeError, match="cancelada pelo usuário"):
        motor.transcrever(
            str(fake_audio),
            idioma="ja",
            cancelado_cb=_cancelar_apos_primeira_checagem,
        )

    spy_encerrar.assert_called_once_with(mock_proc)


def test_regressao_motor_whisperfile_saida_extensa_sem_deadlock(tmp_path):
    """Garante que MotorWhisperfile não sofre deadlock quando o processo gera mais de 64KB de saída."""
    audio_fake = tmp_path / "audio_longo.wav"
    audio_fake.write_text("dummy", encoding="utf-8")

    script_fake = tmp_path / "fake_whisper.py"
    script_fake.write_text(
        'import sys\n'
        'sys.stdout.write("x" * 150000)\n'
        'sys.stdout.flush()\n'
        'with open(sys.argv[2] + ".srt", "w", encoding="utf-8") as f:\n'
        '    f.write("1\\n00:00:00,000 --> 00:00:01,000\\nFala\\n")\n',
        encoding="utf-8",
    )

    cmd_wrapper = tmp_path / "fake_whisper.bat"
    cmd_wrapper.write_text(f'"{sys.executable}" "{script_fake}" %*\n', encoding="utf-8")

    motor = MotorWhisperfile(caminho_executavel=str(cmd_wrapper), timeout_segundos=5)
    resultado = motor.transcrever(str(audio_fake), idioma="auto", cancelado_cb=lambda: False)

    assert resultado.caminho_srt == str(audio_fake) + ".srt"
    assert os.path.isfile(resultado.caminho_srt)


# ---------------------------------------------------------------------------
# 8. Bug 1.8: PRAGMA synchronous=NORMAL em conexões de trabalho
# ---------------------------------------------------------------------------
def test_regressao_cache_synchronous_normal_em_todas_conexoes(tmp_path):
    """Garante que conexões criadas por _get_connection executam PRAGMA synchronous=NORMAL (1)."""
    db_file = str(tmp_path / "cache_wal.db")
    cache = CacheTraducoes(db_file)

    conn = cache._get_connection()
    try:
        cursor = conn.execute("PRAGMA synchronous;")
        val = cursor.fetchone()[0]
        # SQLite: 1 = NORMAL
        assert val == 1, f"PRAGMA synchronous esperado 1 (NORMAL), obtido {val}"
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# 9. Bug 1.9: Thread safety e escrita atômica em PreferenciasUsuario
# ---------------------------------------------------------------------------
def test_regressao_preferencias_usuario_thread_safe_e_escrita_atomica(tmp_path):
    """Garante atomicidade com os.replace e ausência de corrupção sob concorrência."""
    arquivo_prefs = str(tmp_path / "preferencias_teste.json")
    PreferenciasUsuario.ARQUIVO_PREFERENCIAS = arquivo_prefs
    PreferenciasUsuario._dados = None

    def _trabalhador(thread_id: int):
        for i in range(20):
            chave = f"chave_{thread_id}_{i}"
            PreferenciasUsuario.definir(chave, f"valor_{thread_id}_{i}")
            val = PreferenciasUsuario.obter(chave)
            assert val == f"valor_{thread_id}_{i}"

    threads = [threading.Thread(target=_trabalhador, args=(t,)) for t in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # O arquivo final deve ser um JSON válido sem arquivo .tmp residual
    assert os.path.isfile(arquivo_prefs)
    assert not os.path.exists(f"{arquivo_prefs}.tmp")
    with open(arquivo_prefs, "r", encoding="utf-8") as f:
        dados = json.load(f)
    assert len(dados) >= 100


# ---------------------------------------------------------------------------
# 10. Code Smells e Acoplamentos: DRY AniList, Logger sem efeitos e Fila desacoplada
# ---------------------------------------------------------------------------
def test_regressao_dry_anilist_e_adaptador_graphql(tmp_path):
    """Valida que salvar_glossario_arquivo unifica a persistência entre anilist e glossario_port."""
    pasta = str(tmp_path / "glossarios")
    caminho = salvar_glossario_arquivo(
        pasta_destino=pasta,
        titulo="Anime Teste",
        anime_id=123,
        nome_limpo="Anime Teste",
        nomes=["Ichigo", "Rukia"],
    )
    assert os.path.isfile(caminho)
    with open(caminho, "r", encoding="utf-8") as f:
        conteudo = f.read()
    assert "Ichigo" in conteudo
    assert "Rukia" in conteudo


def test_regressao_logger_lazy_sem_efeito_colateral_ao_importar(tmp_path, monkeypatch):
    """Garante que a classe _LazyLogger não executa I/O na instanciação e que escolher_diretorio_logs cria o diretório."""
    from tradutor.logger import escolher_diretorio_logs

    pasta_isolada = str(tmp_path / "logs_lazy_teste")
    monkeypatch.setenv("TRADUTOR_LOG_DIR", pasta_isolada)

    # Instanciação lazy não cria pasta em disco
    logger_lazy = _LazyLogger("Tradutor")
    assert not os.path.exists(pasta_isolada)

    # Chamada explícita para seleção de diretório cria a pasta
    escolhido = escolher_diretorio_logs(pasta_isolada)
    assert os.path.isdir(pasta_isolada)
    assert escolhido == pasta_isolada


def test_regressao_acoplamento_fila_defensiva_e_orquestrador():
    """Garante que a UI expõe cópia defensiva da fila e o Orquestrador copia no start."""
    orquestrador = OrquestradorTraducoes()
    fila_externa = ["a.mkv", "b.mkv"]

    with patch.object(threading, "Thread") as mock_thread:
        mock_instance = MagicMock()
        mock_thread.return_value = mock_instance

        orquestrador.start(fila_externa, "en", "pt", False)

        args_passados = mock_thread.call_args[1]["args"]
        fila_passada = args_passados[0]

        # Modifica a fila original externamente
        fila_externa.append("c.mkv")

        # A fila passada para a thread do orquestrador não deve ter sido mutada
        assert fila_passada == ["a.mkv", "b.mkv"]
        assert len(fila_passada) == 2


def test_regressao_orquestrador_remover_arquivo_fila_dinamico(mocker):
    """Garante que remover_arquivo_fila remove dinamicamente o arquivo pendente e a execução pula com log."""
    orquestrador = OrquestradorTraducoes()
    logs = []
    orquestrador.set_callbacks(
        log_cb=logs.append,
        progress_cb=lambda *_: None,
        ask_overwrite_cb=lambda _: True,
        finish_cb=lambda: None,
    )

    mock_proc1 = MagicMock()
    # Durante o processamento do primeiro arquivo, o usuário remove o segundo da fila
    def _process_side_effect(*_args, **_kwargs):
        orquestrador.remover_arquivo_fila("video2.mkv")
        return True

    mock_proc1.process.side_effect = _process_side_effect
    mock_proc2 = MagicMock()

    mocker.patch(
        "tradutor.estrategias.fabrica.FabricaProcessadores.get_processor",
        side_effect=[mock_proc1, mock_proc2],
    )

    fila = ["video1.mkv", "video2.mkv"]
    orquestrador._is_running = True
    orquestrador._process_files(fila, "en", "pt", False)

    assert mock_proc1.process.call_count == 1
    # video2 foi removido dinamicamente da fila de trabalho e não foi processado
    assert mock_proc2.process.call_count == 0
    assert any("removido da fila, pulando" in msg for msg in logs)


# ---------------------------------------------------------------------------
# 11. Regressões Pente Fino: Orquestrador, Glossários, Textos Extensos e UI
# ---------------------------------------------------------------------------
def test_regressao_orquestrador_idioma_destino_invalido_reseta_is_running_e_chama_finish():
    """Garante que idioma_destino inválido ou 'auto' reseta _is_running=False e chama finish_cb."""
    orquestrador = OrquestradorTraducoes()
    logs = []
    finish_chamado = [False]

    orquestrador.set_callbacks(
        log_cb=logs.append,
        progress_cb=lambda *_: None,
        ask_overwrite_cb=lambda _: True,
        finish_cb=lambda: finish_chamado.__setitem__(0, True),
    )

    orquestrador._is_running = True
    orquestrador._process_files(["video1.mkv"], "en", "idioma_invalido_xyz", False)

    assert orquestrador._is_running is False
    assert finish_chamado[0] is True
    assert any("Idioma de destino inválido" in msg for msg in logs)

    finish_chamado[0] = False
    orquestrador._is_running = True
    orquestrador._process_files(["video1.mkv"], "en", "auto", False)

    assert orquestrador._is_running is False
    assert finish_chamado[0] is True


def test_regressao_auto_alimentar_preserva_alias_video_quando_anime_title_informado(tmp_path, mocker):
    """Garante que auto_alimentar preserva o alias do vídeo original quando anime_title for informado."""
    from tradutor.anilist import auto_alimentar

    mocker.patch(
        "tradutor.anilist.buscar_anime",
        return_value=[{"id": 42, "title": {"romaji": "Tensei Shitara Ken Deshita"}}],
    )
    mocker.patch(
        "tradutor.anilist.buscar_personagens",
        return_value=[{"name": {"first": "Fran", "last": None, "full": "Fran"}}],
    )

    caminho = auto_alimentar(
        nome_video="[Judas] TenKen - S02E07.mkv",
        pasta_destino=str(tmp_path),
        anime_title="Tensei Shitara Ken Deshita",
    )
    assert caminho is not None
    assert os.path.isfile(caminho)
    conteudo = Path(caminho).read_text(encoding="utf-8")
    assert "# Alias: TenKen" in conteudo


def test_regressao_glossario_normalizacao_hifen_e_underline(tmp_path, mocker):
    """Garante normalização de '_' e '-' para espaço na leitura do glossário e no AdaptadorMemoriaGlossario."""
    from tradutor.glossario import GerenciadorGlossario
    from tradutor.glossario_port import AdaptadorMemoriaGlossario

    # 1. GerenciadorGlossario.load com arquivo contendo hífen e vídeo com underline
    dir_gloss = tmp_path / "glossarios"
    dir_gloss.mkdir(parents=True, exist_ok=True)
    (dir_gloss / "Solo-Leveling.txt").write_text("Sung Jin-Woo\n", encoding="utf-8")

    arq_global = tmp_path / "glossario.txt"
    arq_global.write_text("", encoding="utf-8")
    mocker.patch.object(GerenciadorConfig, "DIRETORIO_GLOSSARIOS", str(dir_gloss))

    gg = GerenciadorGlossario(
        filepath=str(arq_global),
        video_filename="Solo_Leveling_S01E01.mkv",
        habilitar_auto_alimentar=False,
    )
    gg.load()
    assert "Sung Jin-Woo" in gg.glossario_map

    # 2. AdaptadorMemoriaGlossario com chave com underline e busca com hífen
    adaptador = AdaptadorMemoriaGlossario({
        "Attack_on_Titan": ["Eren Yeager", "Mikasa"],
    })
    termos = adaptador.buscar_nomes_proprios("Attack-on-Titan S04")
    assert "Eren Yeager" in termos


@pytest.mark.asyncio
async def test_regressao_servico_textos_extensos_fallback_e_cancelamento_cache(tmp_path):
    """Garante que fallback não quebra com len(sub_blocos) <= 1, cancelamento é respeitado e falha não suja cache."""
    from tradutor.cache import CacheTraducoes
    from tradutor.servico_textos_extensos import TradutorTextosExtensos
    from tradutor.tradutores.base import ITradutor

    db_cache = str(tmp_path / "cache_textos.db")
    cache = CacheTraducoes(db_cache)

    class MotorFalha(ITradutor):
        def __init__(self):
            self.chamadas = []

        def translate(self, text: str, src_lang: str, dest_lang: str) -> str:
            self.chamadas.append(text)
            if "Primeira frase" in text and "Segunda frase" in text:
                raise RuntimeError("Falha de bloco grande")
            if "Erro" in text:
                raise RuntimeError("Falha individual")
            return f"[OK] {text}"

    motor = MotorFalha()
    tradutor = TradutorTextosExtensos(
        tradutor=motor,
        cache=cache,
        limite_caracteres=100,
    )

    # Texto onde o primeiro delimitador (\n\n) só tem 1 split real após strip/filter
    # mas o segundo delimitador (. ) particiona com sucesso
    texto = "\n\nPrimeira frase sem quebra. Segunda frase sem quebra.\n\n"
    res = await tradutor.traduzir(texto, "en", "pt")
    assert "[OK]" in res
    assert "Primeira frase" in res
    assert "Segunda frase" in res
    assert cache.get(texto, "en", "pt") is not None

    # Teste com falha parcial: um dos sub-blocos falha
    # Não deve persistir a tradução parcial/híbrida no cache
    texto_parcial = "\n\nPrimeira frase sem quebra. Segunda frase com Erro.\n\n"
    res_parcial = await tradutor.traduzir(texto_parcial, "en", "pt")
    assert "[OK]" in res_parcial
    assert "Segunda frase com Erro" in res_parcial
    assert cache.get(texto_parcial, "en", "pt") is None


def test_regressao_modal_whisper_filtros_e_rotulacao():
    """Valida rotulação com Idiomas.rotular_origem e filtro *.wmv / ausência de *.mov."""
    import inspect
    from tradutor.i18n import I18n
    from tradutor.transcritores import DiagnosticoAudioWhisper
    from tradutor.ui import modal_whisper

    I18n.inicializar()

    codigo_fonte = inspect.getsource(modal_whisper)
    assert "*.wmv" in codigo_fonte
    assert "*.mov" not in codigo_fonte

    diag = DiagnosticoAudioWhisper(
        modelo_recomendado="small",
        modelo_alternativo=None,
        duracao_segundos=120.0,
        idioma_audio="jpn",
        canais_audio=2,
        possui_fundo_musical=True,
        proporcao_silencio=0.1,
        ram_livre_gb=8.0,
        nucleos_cpu=8,
        chave_motivo="diag_motivo_fundo_musical",
    )

    painel = modal_whisper.PainelSeletorWhisper.__new__(modal_whisper.PainelSeletorWhisper)
    painel.lbl_diagnostico = MagicMock()
    painel._ao_mudar_estado_cb = None
    painel.atualizar_opcoes = MagicMock()

    with patch("tradutor.config_usuario.PreferenciasUsuario.definir"):
        painel._exibir_resultado_diagnostico("anime.mkv", diag)

    texto_lbl = painel.lbl_diagnostico.configure.call_args[1]["text"]
    assert "Japonês (jap)" in texto_lbl or "Japanese (jap)" in texto_lbl


def test_regressao_pontos_de_entrada_inicializacao(mocker):
    """Garante que TradutorLegendas26.py e TradutorLegendas26_Classico.py chamam setup_logger, inicializar_tema e I18n.inicializar."""
    import TradutorLegendas26 as main_moderno
    import TradutorLegendas26_Classico as main_classico

    for modulo in (main_moderno, main_classico):
        ordem = []
        mocker.patch.object(modulo, "setup_logger", side_effect=lambda: ordem.append("logger"))
        mocker.patch.object(modulo, "inicializar_tema", side_effect=lambda: ordem.append("tema"))
        mocker.patch.object(modulo.I18n, "inicializar", side_effect=lambda: ordem.append("i18n"))
        mocker.patch.object(modulo, "OrquestradorTraducoes")
        mocker.patch.object(modulo, "ControladorApp")
        mock_view = mocker.MagicMock()
        mocker.patch.object(modulo, "InterfaceGrafica", return_value=mock_view)

        modulo.main()

        assert "logger" in ordem
        assert "tema" in ordem
        assert "i18n" in ordem
        mock_view.mainloop.assert_called_once()


def test_etapa1_orcamento_caracteres_divide_lote_grande(tmp_path):
    import pysubs2
    from tradutor.servico_traducao import ServicoTraducao

    subs = pysubs2.SSAFile()
    for _ in range(10):
        subs.append(pysubs2.SSAEvent(start=0, end=1000, text="A" * 600))

    indices = list(range(len(subs)))
    lotes = ServicoTraducao._montar_lotes(subs, indices)
    assert len(lotes) >= 2
    for lote in lotes:
        assert sum(len(subs[i].text) for i in lote) <= 3500


def test_etapa1_escudo_remove_espaco_antes_de_ponto_e_tags_html(tmp_path):
    from tradutor.glossario import GerenciadorGlossario

    arq_gloss = tmp_path / "glossario.txt"
    arq_gloss.write_text("Goku\n", encoding="utf-8")
    g = GerenciadorGlossario(filepath=str(arq_gloss))

    payload = g.proteger("<i>Goku</i>.")
    restaurado = g.restaurar(payload.texto_mascarado, payload)
    assert restaurado == "<i>Goku</i>."


def test_etapa1_particionador_preserva_interrogacao_no_bloco():
    from tradutor.particionador_texto import ParticionadorTexto

    p = ParticionadorTexto(limite_caracteres=18)
    texto = "Voce esta bem? Eu estou otimo!"
    blocos = p.particionar(texto)
    assert blocos[0].endswith("?")
    assert p.recompor_texto(texto, blocos, blocos) == texto


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


def test_etapa3_textos_extensos_nao_chama_get_unitario_quando_get_many_disponivel():
    from tradutor.servico_textos_extensos import TradutorTextosExtensos
    from tradutor.tradutores.base import ITradutor

    class FakeTradutor(ITradutor):
        def translate(self, text: str, src_lang: str, dest_lang: str) -> str:
            return f"[PT]{text}"

    class SpyCache:
        def __init__(self):
            self.chamadas_get_many = 0
            self.chamadas_get = 0
            self.salvos = {}

        def get_many(self, textos, src_lang, dest_lang):
            self.chamadas_get_many += 1
            return {}

        def get(self, texto, src_lang, dest_lang):
            self.chamadas_get += 1
            return None

        def put(self, texto, src_lang, dest_lang, texto_traduzido):
            self.salvos[texto] = texto_traduzido

    spy_cache = SpyCache()
    servico = TradutorTextosExtensos(tradutor=FakeTradutor(), cache=spy_cache, limite_caracteres=20)
    resultado = servico.traduzir_sincrono("Primeiro bloco.\n\nSegundo bloco.", "en", "pt")
    assert "[PT]" in resultado
    assert spy_cache.chamadas_get_many == 1
    assert spy_cache.chamadas_get == 0


# ---------------------------------------------------------------------------
# 12. Regressões v2.9.3: Contratos, CLI sem mutação em disco e Regex Única
# ---------------------------------------------------------------------------
def test_v293_configuracao_pipeline_propaga_todos_campos_ate_processador_mkv(tmp_path, monkeypatch, mocker):
    """Todos os campos de ConfiguracaoPipeline devem reger o ProcessadorMkv sem depender de PreferenciasUsuario."""
    from tradutor.contratos import ConfiguracaoPipeline
    from tradutor.manipulador_midia import FakeManipuladorMidia
    from tradutor.transcritores.base import ResultadoTranscricao

    arq_prefs = str(tmp_path / "preferencias.json")
    monkeypatch.setattr(PreferenciasUsuario, "ARQUIVO_PREFERENCIAS", arq_prefs)
    PreferenciasUsuario._dados = {
        **PreferenciasUsuario.PADRAO,
        "forcar_transcricao": False,
        "transcricao_habilitada": False,
        "formato_saida_video": "converter_mkv",
        "modelo_whisper": "tiny",
    }

    cfg = ConfiguracaoPipeline(
        idioma_destino="pt",
        idioma_origem="ja",
        politica_sobrescrita="sobrescrever",
        formato_saida_video="manter_original",
        manter_legenda_externa=True,
        habilitar_whisper=True,
        forcar_whisper=True,
        modelo_whisper_padrao="medium",
    )

    ask_overwrite = MagicMock(return_value=False)
    ask_output_format = MagicMock(return_value="converter_mkv")
    fake_midia = FakeManipuladorMidia()

    proc = ProcessadorMkv(
        log_cb=lambda _: None,
        progress_cb=lambda *_: None,
        ask_overwrite_cb=ask_overwrite,
        is_running_cb=lambda: True,
        ask_output_format_cb=ask_output_format,
        output_dir=str(tmp_path),
        manipulador_midia=fake_midia,
        config=cfg,
    )

    # 1. formato_saida_video vem de cfg sem chamar ask_output_format nem PreferenciasUsuario
    assert proc._resolver_politica_saida_video("video.mp4") == "manter_original"
    assert ask_output_format.call_count == 0

    # 2. politica_sobrescrita='sobrescrever' e 'pular' não chamam ask_overwrite
    arq_existente = tmp_path / "existente.srt"
    arq_existente.write_text("conteudo", encoding="utf-8")
    assert proc._check_conflicts({"legenda": str(arq_existente)}, str(tmp_path / "tmp.srt")) is True
    assert ask_overwrite.call_count == 0

    cfg_pular = ConfiguracaoPipeline(politica_sobrescrita="pular")
    proc_pular = ProcessadorMkv(
        log_cb=lambda _: None,
        progress_cb=lambda *_: None,
        ask_overwrite_cb=ask_overwrite,
        is_running_cb=lambda: True,
        output_dir=str(tmp_path),
        manipulador_midia=fake_midia,
        config=cfg_pular,
    )
    assert proc_pular._check_conflicts({"legenda": str(arq_existente)}, str(tmp_path / "tmp.srt")) is False
    assert ask_overwrite.call_count == 0

    # 3. forcar_whisper=True e modelo_whisper_padrao='medium' são repassados ao MotorWhisperfile
    srt_gerado = tmp_path / "ep_audio.srt"
    srt_gerado.write_text("1\n00:00:01,000 --> 00:00:02,000\nOla\n", encoding="utf-8")

    mock_motor_inst = MagicMock()
    mock_motor_inst.esta_disponivel.return_value = True
    mock_motor_inst.transcrever.return_value = ResultadoTranscricao(
        caminho_srt=str(srt_gerado),
        idioma_detectado="ja",
        duracao_segundos=1.2,
    )
    mock_motor_cls = mocker.patch(
        "tradutor.estrategias.processador_mkv.MotorWhisperfile",
        return_value=mock_motor_inst,
    )

    arq_trab, idioma_ret = proc.prepare(str(tmp_path / "ep.mkv"), "ja")
    assert arq_trab is not None
    assert idioma_ret == "ja"
    mock_motor_cls.assert_called_once_with(id_modelo="medium")


def test_v293_cli_force_whisper_nao_muta_preferencias_em_disco(tmp_path, capsys, mocker):
    """CLI --force-whisper não deve chamar PreferenciasUsuario.definir e deve propagar ConfiguracaoPipeline."""
    from tradutor.contratos import ConfiguracaoPipeline

    mkv_fake = tmp_path / "video.mkv"
    mkv_fake.write_bytes(b"dummy")

    spy_definir = mocker.patch.object(PreferenciasUsuario, "definir")
    mocker.patch.object(GerenciadorConfig, "check_dependencies", return_value=True)

    kwargs_capturados = {}
    mock_proc = MagicMock()
    mock_proc.process.return_value = True
    mock_proc.ultimo_idioma_detectado = "jpn"
    mock_proc.ultimos_caminhos_saida = {"video": str(tmp_path / "video_PT.mkv"), "legenda": None}

    def fake_get_processor(*args, **kwargs):
        kwargs_capturados.update(kwargs)
        return mock_proc

    mocker.patch("tradutor.estrategias.fabrica.FabricaProcessadores.get_processor", side_effect=fake_get_processor)

    ret = executar_cli(["--headless", "-i", str(mkv_fake), "-d", "pt", "--force-whisper", "--json"])
    assert ret == CodigoSaidaCli.SUCESSO
    assert spy_definir.call_count == 0
    cfg = kwargs_capturados.get("config")
    assert isinstance(cfg, ConfiguracaoPipeline)
    assert cfg.forcar_whisper is True
    assert cfg.habilitar_whisper is True


def test_v293_cli_tolera_stdout_stderr_none(tmp_path, monkeypatch, mocker):
    """CLI deve executar sem AttributeError quando sys.stdout e sys.stderr forem None (--windowed)."""
    srt_fake = tmp_path / "legenda.srt"
    srt_fake.write_text("1\n00:00:01,000 --> 00:00:02,000\nHello\n", encoding="utf-8")

    mock_proc = MagicMock()
    mock_proc.process.return_value = True
    mock_proc.ultimo_idioma_detectado = "eng"
    mock_proc.ultimos_caminhos_saida = {"video": None, "legenda": str(tmp_path / "legenda_PT.srt")}
    mocker.patch("tradutor.estrategias.fabrica.FabricaProcessadores.get_processor", return_value=mock_proc)

    monkeypatch.setattr(sys, "stdout", None)
    monkeypatch.setattr(sys, "stderr", None)

    ret = executar_cli(["--headless", "-i", str(srt_fake), "-d", "pt", "--json"])
    assert ret == CodigoSaidaCli.SUCESSO


def test_v293_orquestrador_compartilha_mesma_instancia_cache_na_fila(tmp_path, mocker):
    """O OrquestradorTraducoes deve instanciar CacheTraducoes uma única vez e injetá-lo em toda a fila."""
    arq1 = str(tmp_path / "ep1.srt")
    arq2 = str(tmp_path / "ep2.srt")
    for p in (arq1, arq2):
        with open(p, "w", encoding="utf-8") as f:
            f.write("1\n00:00:01,000 --> 00:00:02,000\nHello\n\n")

    caches_injetados = []

    class FakeServicoTraducao:
        def __init__(self, logger, progress_callback, is_cancelled_callback=None, engine=None, video_filename=None, cache=None, **_kwargs):
            caches_injetados.append(cache)

        async def pipeline(self, origem, destino, idioma_preferido="auto", idioma_destino="pt"):
            with open(destino, "w", encoding="utf-8") as f:
                f.write("1\n00:00:01,000 --> 00:00:02,000\nOlá\n\n")
            return True

    mocker.patch("tradutor.estrategias.processador_base.ServicoTraducao", FakeServicoTraducao)

    orq = OrquestradorTraducoes()
    orq.set_callbacks(lambda _m: None, lambda _c, _t: None, lambda _n: True, lambda: None)
    orq._is_running = True
    orq._process_files([arq1, arq2], "en", "pt", True)

    assert len(caches_injetados) == 2
    assert caches_injetados[0] is not None
    assert caches_injetados[0] is caches_injetados[1]


def test_v293_processador_srt_mesmo_idioma_nao_loga_embutindo_transcrita(tmp_path, mocker):
    """ProcessadorSrt com origem == destino não deve registrar mensagem falsa de embutir transcrição."""
    srt = tmp_path / "Portugues.srt"
    srt.write_text("1\n00:00:01,000 --> 00:00:02,000\nOlá\n\n", encoding="utf-8")

    class FakeServico:
        def __init__(self, **_kwargs):
            pass

        async def pipeline(self, origem, destino, idioma_preferido="auto", idioma_destino="pt"):
            with open(destino, "w", encoding="utf-8") as f:
                f.write("1\n00:00:01,000 --> 00:00:02,000\nOlá\n\n")
            return True

    mocker.patch("tradutor.estrategias.processador_base.ServicoTraducao", FakeServico)

    logs = []
    proc = ProcessadorSrt(
        log_cb=logs.append,
        progress_cb=lambda *_: None,
        ask_overwrite_cb=lambda _: True,
        is_running_cb=lambda: True,
        output_dir=str(tmp_path),
    )
    assert proc.process(str(srt), "por", "pt", True) is True
    assert not any("Embutindo legenda transcrita" in msg for msg in logs)


def test_v293_glossario_compila_regex_unica_preservando_golden_sha256(tmp_path):
    """GerenciadorGlossario deve compilar uma única regex combinada em cache e preservar o SHA-256 Golden Master."""
    import hashlib
    import re
    from tradutor.glossario import GerenciadorGlossario

    arq_gloss = tmp_path / "glossario_vazio.txt"
    arq_gloss.write_text("", encoding="utf-8")
    gg = GerenciadorGlossario(filepath=str(arq_gloss))
    gg.glossario_map = {
        "The Force": "A Força",
        "Hogwarts": "Hogwarts",
        "Goku": "Goku",
        "Master Chief": "Chief",
    }

    regex1, mapa1 = gg._obter_regex_termos()
    assert isinstance(regex1, re.Pattern)
    regex2, mapa2 = gg._obter_regex_termos()
    assert regex1 is regex2
    assert mapa1 is mapa2

    gg.glossario_map["Naruto"] = "Naruto"
    regex3, _ = gg._obter_regex_termos()
    assert isinstance(regex3, re.Pattern)
    assert regex3 is not regex1

    gg.glossario_map.pop("Naruto")
    texto_mascarado, _ = gg.apply_shield("The Force is strong with Goku in Hogwarts.")
    assert texto_mascarado == " TKGLOSS0T  is strong with  TKGLOSS2T  in  TKGLOSS1T ."
    assert hashlib.sha256(f"en_pt_{texto_mascarado}".encode("utf-8")).hexdigest() == (
        "8cfd5a02f8169d7d28fff5c6dc8d4b1694f2be14350a015a2c599ee6607cd51b"
    )




