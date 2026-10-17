import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from tradutor.idiomas import Idiomas

@pytest.mark.parametrize("entrada, esperado", [
    ("jpn", "ja"), ("eng", "en"), ("por", "pt"), ("fra", "fr"), # ISO -> Google
    ("und", "auto"), ("mul", "auto"), ("zzz", "auto"), ("", "auto"), # Fallbacks e vazios
    ("pt", "pt"), ("ja", "ja"), ("auto", "auto") # Já estão no padrão do Google
])
def test_para_google(entrada, esperado):
    assert Idiomas.para_google(entrada) == esperado

@pytest.mark.parametrize("entrada, esperado", [
    ("pt", ("por", "Português (Brasil)")),
    ("ja", ("jpn", "日本語")),
    ("en", ("eng", "English")),
    ("xyz", ("xyz", "XYZ")) # Destino desconhecido
])
def test_destino_para_mkv(entrada, esperado):
    assert Idiomas.destino_para_mkv(entrada) == esperado

def test_nomes_amigaveis_e_codigos():
    opcoes = Idiomas.opcoes_destino_exibicao()
    assert "Português (pt)" in opcoes
    assert "Inglês (en)" in opcoes
    assert "Japonês (ja)" in opcoes

    assert Idiomas.nome_para_codigo_destino("Português (pt)") == "pt"
    assert Idiomas.nome_para_codigo_destino("Inglês (en)") == "en"
    assert Idiomas.nome_para_codigo_destino("pt") == "pt"

    assert Idiomas.rotular_origem("jpn") == "Japonês (jpn)"
    assert Idiomas.rotular_origem("auto") == "Automático (auto)"
    assert Idiomas.rotular_origem("xyz") == "XYZ (xyz)"

    assert Idiomas.nome_para_codigo_origem("Japonês (jpn)") == "jpn"
    assert Idiomas.nome_para_codigo_origem("Automático (auto)") == "auto"
    assert Idiomas.nome_para_codigo_origem("auto") == "auto"

