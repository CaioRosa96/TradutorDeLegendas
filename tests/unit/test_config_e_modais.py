"""Testes unitários para Preferências de Usuário, i18n, Temas e lógica de dados do Grimório."""

import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from tradutor.config_usuario import PreferenciasUsuario
from tradutor.i18n import I18n
from tradutor.ui.tema import definir_tema, obter_tema_ativo, TEMAS
from tradutor.config import GerenciadorConfig


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


def test_propagacao_tema_e_idioma_interface():
    """Garante que a propagacao de tema e a mudanca de idioma ocorrem sem falhas."""
    from tradutor.interface import InterfaceGrafica

    app = InterfaceGrafica()
    try:
        # 1. Testa temas
        for tema in ["claro", "alto_contraste", "ms_dos", "escuro"]:
            definir_tema(tema)
            app._aplicar_novo_tema(tema)

        # 2. Testa mudanca de idioma para ingles
        I18n.definir_idioma("en")
        app._aplicar_novo_idioma("en")
        assert "Taradutor Subtitle Translator" in app.title()
        assert "Subtitles" in app.header.lbl_sub.cget("text")
        assert "TRANSLATION PARAMETERS" in app.sidebar.lbl_secao.cget("text")
        assert "Portuguese (pt)" in app.sidebar.combo_lang_dest.get()
        assert "Auto (auto)" in app.sidebar.combo_lang.get()
        assert "Processing Queue (0 files)" in app.fila.lbl_titulo.cget("text")
        assert "START TRANSLATION" in app.footer.btn_run.cget("text")

        # 3. Testa mudanca de idioma de volta para portugues
        I18n.definir_idioma("pt-br")
        app._aplicar_novo_idioma("pt-br")
        assert "Taradutor de Legendas" in app.title()
        assert "Legendas" in app.header.lbl_sub.cget("text")
        assert "PARÂMETROS DE TRADUÇÃO" in app.sidebar.lbl_secao.cget("text")
        assert "Português (pt)" in app.sidebar.combo_lang_dest.get()
        assert "Automático (auto)" in app.sidebar.combo_lang.get()
        assert "Fila de Processamento (0 arquivos)" in app.fila.lbl_titulo.cget("text")
        assert "INICIAR TRADUÇÃO" in app.footer.btn_run.cget("text")
    finally:
        app.destroy()
