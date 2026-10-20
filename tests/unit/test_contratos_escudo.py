"""Testes da Fase 1: contratos imutáveis e fachada LinhaProtegida do escudo.

Os casos "golden master" fixam a saída byte a byte do apply_shield anterior à
refatoração. Como a chave do cache SQLite é o SHA-256 de `src_dest_textoMascarado`,
qualquer divergência aqui invalidaria os registros existentes na tabela `traducoes`.
"""
import dataclasses
import hashlib
import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from tradutor.contratos import EscudoTagsPort, LinhaProtegida, ResultadoTraducaoLinha
from tradutor.glossario import GerenciadorGlossario


@pytest.fixture
def glossario(tmp_path):
    """Gerenciador isolado com dicionário injetado, sem acesso a glossários reais."""
    gg = GerenciadorGlossario(filepath=str(tmp_path / "glossario_fake.txt"))
    gg.glossario_map = {
        "The Force": "A Força",
        "Hogwarts": "Hogwarts",
        "Goku": "Goku",
        "Master Chief": "Chief",
    }
    return gg


CASOS_GOLDEN = [
    pytest.param(
        "The Force is strong with Goku in Hogwarts.",
        " TKGLOSS0T  is strong with  TKGLOSS2T  in  TKGLOSS1T .",
        {"TKGLOSS0T": "A Força", "TKGLOSS1T": "Hogwarts", "TKGLOSS2T": "Goku"},
        "8cfd5a02f8169d7d28fff5c6dc8d4b1694f2be14350a015a2c599ee6607cd51b",
        id="somente_glossario",
    ),
    pytest.param(
        r"{\an8}Olá mundo! <i>Goku</i> {\c&H00FFFF&}atacou!",
        " TKGLOSS0T Olá mundo!  TKGLOSS1T  TKGLOSS4T  TKGLOSS2T   TKGLOSS3T atacou!",
        {
            "TKGLOSS0T": r"{\an8}",
            "TKGLOSS1T": "<i>",
            "TKGLOSS2T": "</i>",
            "TKGLOSS3T": r"{\c&H00FFFF&}",
            "TKGLOSS4T": "Goku",
        },
        "0680f509d698492f802e5f1aad19a35b08dde068674d438022882e893d8bc4db",
        id="tags_ass_html_e_glossario",
    ),
    pytest.param(
        "Linha um com Goku \\N quebra\nLinha dois sem termos\n\nGOKU e the force",
        "Linha um com  TKGLOSS1T  \\N quebra\nLinha dois sem termos\n\n TKGLOSS2T  e  TKGLOSS0T ",
        {"TKGLOSS0T": "A Força", "TKGLOSS1T": "Goku", "TKGLOSS2T": "Goku"},
        "1cbca232054bfd3c5ae471cc0740b7edc1dfb2702fe46615c2e1c08afd4fc5d5",
        id="lote_multilinha_com_quebra_ass_preservada",
    ),
    pytest.param(
        "Texto sem nada",
        "Texto sem nada",
        {},
        "bc8111bc532c0c392a090713ba8ee9f2a70cea03466b8eed53af2ca84208cf25",
        id="sem_tokens",
    ),
]


class TestCompatibilidadeCache:
    @pytest.mark.parametrize("entrada, mascarado, mapa, sha", CASOS_GOLDEN)
    def test_apply_shield_mantem_saida_identica(self, glossario, entrada, mascarado, mapa, sha):
        """O texto mascarado e o hash do cache devem ser idênticos aos da versão anterior."""
        texto, mapeamento = glossario.apply_shield(entrada)
        assert texto == mascarado
        assert mapeamento == mapa
        assert hashlib.sha256(f"en_pt_{texto}".encode("utf-8")).hexdigest() == sha

    @pytest.mark.parametrize("entrada, mascarado, mapa, sha", CASOS_GOLDEN)
    def test_proteger_equivale_ao_apply_shield(self, glossario, entrada, mascarado, mapa, sha):
        """A fachada LinhaProtegida não pode alterar a string usada como chave de cache."""
        payload = glossario.proteger(entrada, id_linha=7)
        assert payload.id_linha == 7
        assert payload.texto_original == entrada
        assert payload.texto_mascarado == mascarado
        assert dict(payload.mapa_tokens) == mapa


class TestLinhaProtegida:
    def test_value_object_imutavel(self, glossario):
        payload = glossario.proteger(r"{\an8}Goku", id_linha=5)
        with pytest.raises(dataclasses.FrozenInstanceError):
            payload.id_linha = 99  # type: ignore[misc]

    def test_mapa_tokens_imutavel_mesmo_quando_origem_e_dict(self):
        """Alterar o dict de origem ou o mapa exposto não pode corromper o payload."""
        origem = {"TKGLOSS0T": "Goku"}
        payload = LinhaProtegida(id_linha=1, texto_original="Goku",
                                 texto_mascarado=" TKGLOSS0T ", mapa_tokens=origem)
        origem["TKGLOSS0T"] = "Vegeta"
        assert payload.mapa_tokens["TKGLOSS0T"] == "Goku"
        with pytest.raises(TypeError):
            payload.mapa_tokens["TKGLOSS0T"] = "Vegeta"  # type: ignore[index]

    def test_possui_tokens(self, glossario):
        assert glossario.proteger("Goku venceu").possui_tokens is True
        assert glossario.proteger("Texto comum").possui_tokens is False

    def test_restaurar_tolera_corrupcao_do_google(self, glossario):
        payload = glossario.proteger(r"{\an8}The Force acordou Goku", id_linha=3)
        saida_api = "t K GLoss 0 T  A tkgloss1t  despertou  T K G L O S S 2 t"
        assert glossario.restaurar(saida_api, payload) == r"{\an8}A A Força despertou Goku"

    def test_gerenciador_satisfaz_porta_do_escudo(self, glossario):
        assert isinstance(glossario, EscudoTagsPort)


class TestResultadoTraducaoLinha:
    def test_valores_padrao_e_imutabilidade(self):
        resultado = ResultadoTraducaoLinha(id_linha=10, texto_traduzido="Olá", sucesso=True)
        assert resultado.origem_cache is False
        assert resultado.usou_fallback is False
        assert resultado.erro is None
        with pytest.raises(dataclasses.FrozenInstanceError):
            resultado.sucesso = False  # type: ignore[misc]
