"""Testes unitários para o contrato de versão e integridade da Fonte Única da Verdade (InfoVersao)."""
import json
import os
import pytest

from tradutor.versao import InfoVersao
from tradutor.atualizador import VerificadorAtualizacao
from tradutor.logger import VERSAO_APP
from tradutor.i18n import I18n


def test_contrato_info_versao_valores_e_formatadores():
    """Valida os valores base e os métodos auxiliares de formatação de InfoVersao."""
    assert InfoVersao.NUMERO == "2.9.3"
    assert InfoVersao.NOME_EDICAO == "Lossless Modern UI"
    assert InfoVersao.tag() == "v2.9.3"
    assert InfoVersao.completa() == "v2.9.3 (Lossless Modern UI)"
    assert InfoVersao.titulo_janela("Tradutor") == "Tradutor — v2.9.3"
    assert InfoVersao.formatar_rotulo_sobre("Versão {0}") == "Versão 2.9.3 (Lossless Modern UI)"


def test_sincronizacao_consumidores_de_versao():
    """Garante que Atualizador e Logger consomem estritamente a mesma versão de InfoVersao."""
    assert VerificadorAtualizacao.VERSAO_ATUAL == InfoVersao.NUMERO
    assert VERSAO_APP == InfoVersao.NUMERO


def test_i18n_locales_parametrizados_com_placeholder():
    """Garante que todos os arquivos de tradução possuem {0} na chave 'lbl_versao' e suportam formatação."""
    pasta_locales = I18n._diretorio_locales
    for codigo in I18n.IDIOMAS_SUPORTADOS:
        caminho = os.path.join(pasta_locales, f"{codigo}.json")
        with open(caminho, "r", encoding="utf-8") as f:
            dados = json.load(f)

        assert "lbl_versao" in dados, f"Chave 'lbl_versao' ausente em {codigo}.json"
        template = dados["lbl_versao"]
        assert "{0}" in template, f"Template 'lbl_versao' em {codigo}.json não contém placeholder {{0}}: '{template}'"

        resultado = InfoVersao.formatar_rotulo_sobre(template)
        assert InfoVersao.NUMERO in resultado
        assert InfoVersao.NOME_EDICAO in resultado
