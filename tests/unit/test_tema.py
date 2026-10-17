import os
import re
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from tradutor.ui import tema as modulo_tema
from tradutor.ui.tema import (
    TEMAS,
    CORES,
    definir_tema,
    obter_tema_ativo,
    inicializar_tema,
)

TEMAS_ESPERADOS = ("escuro", "claro", "alto_contraste", "ms_dos")

TOKENS_OBRIGATORIOS = {
    "nome",
    "ctk_mode",
    "bg_janela",
    "bg_sidebar",
    "bg_card",
    "bg_card_hover",
    "borda_card",
    "borda_largura",
    "raio_card",
    "fonte_ui",
    "destaque_azul",
    "destaque_azul_hover",
    "destaque_verde",
    "destaque_verde_hover",
    "destaque_vermelho",
    "destaque_vermelho_hover",
    "btn_destaque_txt",
    "texto_principal",
    "texto_secundario",
    "texto_escuro",
    "bg_console",
    "combo_bg",
    "combo_btn",
    "progressbar_bg",
    "badge_ext_mkv_bg",
    "badge_ext_mkv_txt",
    "badge_ext_outros_bg",
    "badge_ext_outros_txt",
    "badge_fluxo_bg",
    "badge_fluxo_txt",
}

CHAVES_NAO_HEX = {"nome", "ctk_mode", "borda_largura", "raio_card", "fonte_ui"}
PADRAO_HEX = re.compile(r"^#[0-9a-fA-F]{6}$")


def calcular_luminancia_relativa(hex_cor: str) -> float:
    """Calcula a luminância relativa (WCAG 2.x) de uma cor hexadecimal #RRGGBB."""
    hex_limpo = hex_cor.lstrip("#")
    r, g, b = (int(hex_limpo[i : i + 2], 16) / 255.0 for i in (0, 2, 4))

    def linearizar(canal: float) -> float:
        return canal / 12.92 if canal <= 0.04045 else ((canal + 0.055) / 1.055) ** 2.4

    r_lin, g_lin, b_lin = linearizar(r), linearizar(g), linearizar(b)
    return 0.2126 * r_lin + 0.7152 * g_lin + 0.0722 * b_lin


def calcular_razao_contraste(hex_cor1: str, hex_cor2: str) -> float:
    """Retorna a razão de contraste WCAG (1.0 a 21.0) entre duas cores hexadecimais."""
    lum1 = calcular_luminancia_relativa(hex_cor1)
    lum2 = calcular_luminancia_relativa(hex_cor2)
    mais_clara = max(lum1, lum2)
    mais_escura = min(lum1, lum2)
    return (mais_clara + 0.05) / (mais_escura + 0.05)


@pytest.mark.parametrize("nome_tema", TEMAS_ESPERADOS)
def test_presenca_todos_tokens_obrigatorios(nome_tema):
    """Garante que nenhum tema omita chaves semânticas exigidas pelos componentes visuais."""
    assert nome_tema in TEMAS, f"Tema '{nome_tema}' ausente do dicionário TEMAS."
    paleta = TEMAS[nome_tema]
    chaves_faltantes = TOKENS_OBRIGATORIOS - set(paleta.keys())
    assert not chaves_faltantes, f"Tema '{nome_tema}' está sem os tokens: {chaves_faltantes}"


@pytest.mark.parametrize("nome_tema", TEMAS_ESPERADOS)
def test_formato_hexadecimal_e_tipos_validos(nome_tema):
    """Valida se todas as cores seguem #RRGGBB e se parâmetros numéricos/modo são válidos."""
    paleta = TEMAS[nome_tema]
    assert paleta["ctk_mode"] in ("Dark", "Light")
    assert isinstance(paleta["borda_largura"], int) and paleta["borda_largura"] >= 1
    assert isinstance(paleta["raio_card"], int) and paleta["raio_card"] >= 0
    assert isinstance(paleta["fonte_ui"], str) and len(paleta["fonte_ui"].strip()) > 0

    for chave, valor in paleta.items():
        if chave not in CHAVES_NAO_HEX:
            assert isinstance(valor, str) and PADRAO_HEX.match(valor), (
                f"Cor inválida em TEMAS['{nome_tema}']['{chave}']: {valor}"
            )


def test_identidade_visual_ms_dos_retro():
    """Garante que o tema MS-DOS Retrô use fonte monoespaçada, cantos retos e vídeo inverso."""
    ms_dos = TEMAS["ms_dos"]
    assert ms_dos["fonte_ui"] == "Consolas"
    assert ms_dos["raio_card"] == 0
    assert ms_dos["borda_largura"] >= 2
    assert ms_dos["btn_destaque_txt"] == "#000000"
    assert ms_dos["destaque_azul"].lower() != ms_dos["destaque_verde"].lower(), (
        "MS-DOS deve diferenciar destaque_azul (âmbar) de destaque_verde (fósforo verde)."
    )


@pytest.mark.parametrize("nome_tema", TEMAS_ESPERADOS)
@pytest.mark.parametrize("superficie", ["bg_janela", "bg_sidebar", "bg_card", "bg_console", "combo_bg"])
def test_contraste_wcag_texto_principal(nome_tema, superficie):
    """Garante contraste AAA (>= 7.0:1) para o texto principal em todas as superfícies de leitura."""
    paleta = TEMAS[nome_tema]
    razao = calcular_razao_contraste(paleta["texto_principal"], paleta[superficie])
    assert razao >= 7.0, (
        f"Contraste insuficiente ({razao:.2f}:1) em '{nome_tema}' "
        f"entre texto_principal ({paleta['texto_principal']}) e {superficie} ({paleta[superficie]})."
    )


@pytest.mark.parametrize("nome_tema", TEMAS_ESPERADOS)
@pytest.mark.parametrize("superficie", ["bg_sidebar", "bg_card"])
def test_contraste_wcag_texto_secundario(nome_tema, superficie):
    """Valida contraste mínimo AA (>= 4.5:1) geral e AAA (>= 7.0:1) no Alto Contraste para texto secundário."""
    paleta = TEMAS[nome_tema]
    minimo = 7.0 if nome_tema == "alto_contraste" else 4.5
    razao = calcular_razao_contraste(paleta["texto_secundario"], paleta[superficie])
    assert razao >= minimo, (
        f"Contraste insuficiente ({razao:.2f}:1 < {minimo}:1) em '{nome_tema}' "
        f"entre texto_secundario ({paleta['texto_secundario']}) e {superficie} ({paleta[superficie]})."
    )


@pytest.mark.parametrize(
    "nome_tema, minimo_esperado",
    [
        ("claro", 3.5),
        ("alto_contraste", 7.0),
        ("ms_dos", 7.0),
    ],
)
@pytest.mark.parametrize("cor_fundo_btn", ["destaque_azul", "destaque_verde"])
def test_contraste_botoes_acao_primaria(nome_tema, minimo_esperado, cor_fundo_btn):
    """Impede texto ilegível sobre botões de destaque nos temas Claro, Alto Contraste e MS-DOS."""
    paleta = TEMAS[nome_tema]
    razao = calcular_razao_contraste(paleta["btn_destaque_txt"], paleta[cor_fundo_btn])
    assert razao >= minimo_esperado, (
        f"Contraste de botão reprovado ({razao:.2f}:1 < {minimo_esperado}:1) em '{nome_tema}' "
        f"({paleta['btn_destaque_txt']} sobre {paleta[cor_fundo_btn]})."
    )


@pytest.mark.parametrize("nome_tema", TEMAS_ESPERADOS)
@pytest.mark.parametrize(
    "par_badge",
    [
        ("badge_ext_mkv_txt", "badge_ext_mkv_bg"),
        ("badge_ext_outros_txt", "badge_ext_outros_bg"),
        ("badge_fluxo_txt", "badge_fluxo_bg"),
    ],
)
def test_contraste_badges_fila(nome_tema, par_badge):
    """Verifica a legibilidade das pills de formato (MKV/SRT) e indicador de fluxo de idioma."""
    paleta = TEMAS[nome_tema]
    chave_txt, chave_bg = par_badge
    minimo = 7.0 if nome_tema in ("alto_contraste", "ms_dos") else 4.5
    razao = calcular_razao_contraste(paleta[chave_txt], paleta[chave_bg])
    assert razao >= minimo, (
        f"Contraste de badge insuficiente ({razao:.2f}:1 < {minimo}:1) em '{nome_tema}' "
        f"para {chave_txt} ({paleta[chave_txt]}) sobre {chave_bg} ({paleta[chave_bg]})."
    )


def test_troca_dinamica_preserva_referencia_dict_cores(mocker):
    """
    Garante que definir_tema() atualiza CORES in-place (sem reatribuir a referência de memória),
    sincroniza o modo do CustomTkinter e persiste a escolha em PreferenciasUsuario.
    """
    mock_definir_pref = mocker.patch("tradutor.ui.tema.PreferenciasUsuario.definir")
    mock_ctk_mode = mocker.patch("tradutor.ui.tema.ctk.set_appearance_mode")
    mocker.patch("tradutor.ui.tema.PreferenciasUsuario.obter", return_value="alto_contraste")

    id_original = id(CORES)

    try:
        definir_tema("claro")
        assert obter_tema_ativo() == "claro"
        assert id(CORES) == id_original
        assert CORES["bg_sidebar"] == TEMAS["claro"]["bg_sidebar"]
        mock_ctk_mode.assert_called_with("Light")
        mock_definir_pref.assert_called_with("tema", "claro")

        inicializar_tema()
        assert obter_tema_ativo() == "alto_contraste"
        assert id(CORES) == id_original
        assert CORES["btn_destaque_txt"] == "#000000"
        mock_ctk_mode.assert_called_with("Dark")
    finally:
        definir_tema("escuro")
