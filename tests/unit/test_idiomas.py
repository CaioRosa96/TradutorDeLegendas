import os
import re
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from tradutor.idiomas import Idiomas


@pytest.mark.parametrize("entrada, esperado", [
    ("jpn", "ja"), ("eng", "en"), ("por", "pt"), ("fra", "fr"),  # ISO -> Google
    ("und", "auto"), ("mul", "auto"), ("zzz", "auto"), ("", "auto"),  # Fallbacks e vazios
    ("pt", "pt"), ("ja", "ja"), ("auto", "auto")  # Já estão no padrão do Google
])
def test_para_google(entrada, esperado):
    assert Idiomas.para_google(entrada) == esperado


@pytest.mark.parametrize("entrada, esperado", [
    ("pt", ("por", "Português (Brasil)")),
    ("ja", ("jpn", "日本語")),
    ("en", ("eng", "English")),
    ("xyz", ("xyz", "XYZ"))  # Destino desconhecido
])
def test_destino_para_mkv(entrada, esperado):
    assert Idiomas.destino_para_mkv(entrada) == esperado


def test_nomes_amigaveis_e_codigos():
    opcoes = Idiomas.opcoes_destino_exibicao("pt-br")
    assert "Português (pt)" in opcoes
    assert "Inglês (ing)" in opcoes
    assert "Japonês (jap)" in opcoes
    assert "Alemão (ale)" in opcoes

    assert Idiomas.nome_para_codigo_destino("Português (pt)") == "pt"
    assert Idiomas.nome_para_codigo_destino("Inglês (ing)") == "en"
    assert Idiomas.nome_para_codigo_destino("Japonês (jap)") == "ja"
    assert Idiomas.nome_para_codigo_destino("pt") == "pt"

    assert Idiomas.rotular_origem("jpn", "pt-br") == "Japonês (jap)"
    assert Idiomas.rotular_origem("eng", "pt-br") == "Inglês (ing)"
    assert Idiomas.rotular_origem("und", "pt-br") == "Indefinido no vídeo (ind)"
    assert Idiomas.rotular_origem("und", "en") == "Undefined in video (und)"
    assert Idiomas.rotular_origem("auto", "pt-br") == "Automático (auto)"
    assert Idiomas.rotular_origem("xyz", "pt-br") == "XYZ (xyz)"

    assert Idiomas.nome_para_codigo_origem("Japonês (jap)") == "jpn"
    assert Idiomas.nome_para_codigo_origem("Inglês (ing)") == "eng"
    assert Idiomas.nome_para_codigo_origem("Indefinido no vídeo (ind)") == "und"
    assert Idiomas.nome_para_codigo_origem("Automático (auto)") == "auto"
    assert Idiomas.nome_para_codigo_origem("auto") == "auto"


def test_abreviacoes_nativas_sem_ingles_em_japones_e_chines():
    """Garante que os idiomas japones (ja) e chines (zh-cn) nao usam abreviacoes em alfabeto latino."""
    for idioma_cjk in ("ja", "zh-cn"):
        for cod, rotulo in Idiomas._NOMES_DESTINO_MULTI[idioma_cjk].items():
            assert re.search(r"[a-zA-Z]", rotulo) is None, f"Abreviação latina encontrada em {idioma_cjk}: {rotulo}"
            assert Idiomas.nome_para_codigo_destino(rotulo) == cod

        for cod, rotulo in Idiomas._NOMES_ORIGEM_MULTI[idioma_cjk].items():
            assert re.search(r"[a-zA-Z]", rotulo) is None, f"Abreviação latina encontrada em {idioma_cjk}: {rotulo}"
            codigo_reverso = Idiomas.nome_para_codigo_origem(rotulo)
            if cod in ("deu", "ger"):
                assert codigo_reverso in ("deu", "ger")
            elif cod in ("chi", "zho"):
                assert codigo_reverso in ("chi", "zho")
            else:
                assert codigo_reverso == cod
