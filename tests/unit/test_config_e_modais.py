"""Testes unitários para Preferências de Usuário, i18n, Temas e lógica de dados do Grimório."""

import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from tradutor.config_usuario import PreferenciasUsuario
from tradutor.i18n import I18n
from tradutor.ui.tema import definir_tema, obter_tema_ativo, TEMAS
from tradutor.config import GerenciadorConfig


@pytest.fixture(scope="module")
def app_interface():
    """Instância compartilhada de InterfaceGrafica para os testes do módulo."""
    import tradutor.interface as mod_interface
    from tradutor.interface import InterfaceGrafica

    original_dnd = mod_interface.HAS_DND
    mod_interface.HAS_DND = False
    I18n.definir_idioma("pt-br")
    definir_tema("escuro")
    app = InterfaceGrafica()
    try:
        yield app
    finally:
        try:
            app.update_idletasks()
            app.destroy()
        except Exception:
            pass
        mod_interface.HAS_DND = original_dnd


def test_preferencias_usuario_padrao_e_modificacao(tmp_path):
    """Garante que as preferencias carregam padroes e persistem novos valores."""
    arquivo_temp = str(tmp_path / "pref_teste.json")
    PreferenciasUsuario.ARQUIVO_PREFERENCIAS = arquivo_temp
    PreferenciasUsuario._dados = None

    dados = PreferenciasUsuario.carregar()
    assert dados["idioma_app"] == "pt-br"
    assert dados["tema"] == "escuro"
    assert dados["tocar_som"] is True

    PreferenciasUsuario.definir("tema", "ms_dos")
    assert PreferenciasUsuario.obter("tema") == "ms_dos"
    assert os.path.exists(arquivo_temp)

    # Recarrega do arquivo
    PreferenciasUsuario._dados = None
    assert PreferenciasUsuario.obter("tema") == "ms_dos"


def test_i18n_traducoes_e_fallback():
    """Valida dicionarios de traducao e fallback seguro para chaves ausentes."""
    I18n.definir_idioma("en")
    assert I18n.t("btn_grimorio") == "Grimoire"
    assert I18n.t("btn_config") == "Settings"

    I18n.definir_idioma("es")
    assert I18n.t("btn_grimorio") == "Grimorio"

    I18n.definir_idioma("ja")
    assert I18n.t("btn_grimorio") == "魔導書"

    I18n.definir_idioma("zh-cn")
    assert I18n.t("btn_grimorio") == "魔导书"
    assert I18n.t("btn_config") == "设置"

    I18n.definir_idioma("pt-br")
    assert I18n.t("btn_grimorio") == "Grimório"

    # Chave inexistente deve retornar a propria chave
    assert I18n.t("chave_inexistente_123") == "chave_inexistente_123"


def test_alternancia_de_temas():
    """Verifica que a alternancia entre os 4 temas atualiza a paleta ativa."""
    for nome_tema in ["escuro", "claro", "alto_contraste", "ms_dos"]:
        paleta = definir_tema(nome_tema)
        assert obter_tema_ativo() == nome_tema
        assert paleta["bg_janela"] == TEMAS[nome_tema]["bg_janela"]


def test_leitura_glossarios_grimorio():
    """Verifica se os arquivos da pasta glossarios/ sao acessiveis e legiveis."""
    pasta = GerenciadorConfig.DIRETORIO_GLOSSARIOS
    assert os.path.exists(pasta)

    arquivos = [f for f in os.listdir(pasta) if f.endswith(".txt")]
    assert len(arquivos) >= 10, "Esperado ao menos 10 arquivos de glossario de animes."

    caminho_primeiro = os.path.join(pasta, arquivos[0])
    with open(caminho_primeiro, "r", encoding="utf-8") as f:
        linhas = [l.strip() for l in f if l.strip()]
    assert len(linhas) > 0, "O arquivo de glossario nao deve estar vazio."


def test_propagacao_tema_e_idioma_interface(app_interface):
    """Garante que a propagacao de tema e a mudanca de idioma ocorrem sem falhas."""
    app = app_interface
    app.files = []
    app._sincronizar_fila()

    # 1. Testa temas
    for tema in ["claro", "alto_contraste", "ms_dos", "escuro"]:
        definir_tema(tema)
        app._aplicar_novo_tema(tema)

    # 2. Testa mudanca de idioma para ingles
    I18n.definir_idioma("en")
    app._aplicar_novo_idioma("en")
    assert "Tradutor Subtitle Translator" in app.title()
    assert "Subtitles" in app.header.lbl_sub.cget("text")
    assert "TRANSLATION PARAMETERS" in app.sidebar.lbl_secao.cget("text")
    assert "Portuguese (pt)" in app.sidebar.combo_lang_dest.get()
    assert "Auto (auto)" in app.sidebar.combo_lang.get()
    assert "Processing Queue (0 files)" in app.fila.lbl_titulo.cget("text")
    assert "START TRANSLATION" in app.footer.btn_run.cget("text")

    # 3. Testa mudanca de idioma de volta para portugues
    I18n.definir_idioma("pt-br")
    app._aplicar_novo_idioma("pt-br")
    assert "Tradutor de Legendas" in app.title()
    assert "Legendas" in app.header.lbl_sub.cget("text")
    assert "PARÂMETROS DE TRADUÇÃO" in app.sidebar.lbl_secao.cget("text")
    assert "Português (pt)" in app.sidebar.combo_lang_dest.get()
    assert "Automático (auto)" in app.sidebar.combo_lang.get()
    assert "Fila de Processamento (0 arquivos)" in app.fila.lbl_titulo.cget("text")
    assert "INICIAR TRADUÇÃO" in app.footer.btn_run.cget("text")


def test_header_redefinir_textos_mantem_consistencia_com_inicializacao(app_interface):
    """Garante que redefinir_textos() no HeaderView nao injeta prefixos inexistentes na criacao."""
    app = app_interface
    I18n.definir_idioma("pt-br")
    app._aplicar_novo_idioma("pt-br")
    texto_inicial_tema = app.header.btn_tema.cget("text")
    texto_inicial_grimorio = app.header.btn_grimorio.cget("text")
    app.header.redefinir_textos()
    assert app.header.btn_tema.cget("text") == texto_inicial_tema
    assert app.header.btn_grimorio.cget("text") == texto_inicial_grimorio


def test_remover_item_durante_execucao_nao_reativa_botao_iniciar_nem_duplica_processo(app_interface, mocker):
    """Regressão: remover item da fila com tradução em andamento não pode voltar o botão
    para 'INICIAR TRADUÇÃO' nem permitir que duas threads do Orquestrador rodem em paralelo."""
    import threading
    from tradutor.orquestrador import OrquestradorTraducoes
    from tradutor.controlador import ControladorApp

    app = app_interface
    I18n.definir_idioma("pt-br")
    orq = OrquestradorTraducoes()
    ctrl = ControladorApp(app, orq)
    mocker.patch.object(ctrl, "on_files_selected")

    app.files = ["video_sem_legenda.mkv", "video_com_legenda.mkv"]
    app._sincronizar_fila()

    # Simula início do processamento do primeiro vídeo (lote em andamento)
    evento_bloqueio = threading.Event()
    evento_concluido = threading.Event()
    contagem_execucoes = []

    def fake_process_files(files, *_args):
        contagem_execucoes.append(list(files))
        evento_bloqueio.wait(timeout=2.0)
        orq._is_running = False
        evento_concluido.set()

    mocker.patch.object(orq, "_process_files", side_effect=fake_process_files)

    try:
        ctrl.start_translation(app.files, "auto", "pt", False)
        assert bool(app.footer.btn_cancelar.winfo_manager()) is True
        assert bool(app.footer.btn_run.winfo_manager()) is False

        # Usuário tenta remover o segundo vídeo enquanto o primeiro ainda está processando
        app._remover_arquivo("video_com_legenda.mkv")

        # 1. O botão NÃO pode voltar para INICIAR TRADUÇÃO enquanto o lote estiver rodando
        assert bool(app.footer.btn_run.winfo_manager()) is False, (
            "O botão 'INICIAR TRADUÇÃO' reapareceu indevidamente durante a execução!"
        )
        assert bool(app.footer.btn_cancelar.winfo_manager()) is True

        # 2. Tentativa de chamar start() novamente enquanto já está rodando deve ser ignorada
        orq.start(app.files, "auto", "pt", False)
        evento_bloqueio.set()
        evento_concluido.wait(timeout=2.0)

        assert len(contagem_execucoes) == 1, "O Orquestrador permitiu duas execuções simultâneas em paralelo!"
    finally:
        evento_bloqueio.set()
        app._em_execucao = False
        app.footer.configurar_modo_pronto(False)
        app.files = []
        app._sincronizar_fila()


def test_inicializacao_interface_classica(app_interface, mocker):
    """Garante que a interface clássica pode ser instanciada e configurada com o Controller."""
    import tradutor.interface_classica as mod_classica
    from tradutor.interface_classica import InterfaceGrafica as InterfaceClassica
    from tradutor.orquestrador import OrquestradorTraducoes
    from tradutor.controlador import ControladorApp

    # Encerra limpa a janela moderna antes de instanciar a janela clássica
    app_interface.update_idletasks()
    app_interface.destroy()

    mocker.patch.object(mod_classica, "HAS_DND", False)
    app = InterfaceClassica()
    try:
        model = OrquestradorTraducoes()
        controller = ControladorApp(app, model)
        assert app._controller is controller
        assert "Tradutor" in app.title()
    finally:
        app.update_idletasks()
        app.destroy()
