import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from tradutor.glossario import GerenciadorGlossario

@pytest.fixture
def gerenciador_mock(tmp_path, mocker):
    """
    Cria uma instância do GerenciadorGlossario isolada.
    Impede que ele tente acessar a pasta real 'glossarios' e disparar a API.
    """
    # Impede disparar o script de busca automática se ele não achar o específico
    mocker.patch('alimentar_glossario.auto_alimentar', return_value=None)
    
    # Cria o gerenciador sem carregar nada automático
    gg = GerenciadorGlossario(filepath=str(tmp_path / "fake_glossario.txt"))
    # Injetamos manualmente o dicionário para testar a lógica pura de tokenização
    gg.glossario_map = {
        "The Force": "A Força",
        "Hogwarts": "Hogwarts",
        "Goku": "Goku",
        "Master Chief": "Chief"
    }
    return gg

def test_apply_shield(gerenciador_mock):
    """Garante que as palavras chave são tokenizadas corretamente (isoladas de contexto)."""
    texto_original = "The Force is strong with Goku in Hogwarts."
    
    texto_protegido, mapping = gerenciador_mock.apply_shield(texto_original)
    
    # As chaves mais longas ganham tokens menores primeiro.
    # The Force -> TKGLOSS0T
    # Master Chief -> TKGLOSS1T
    # Hogwarts -> TKGLOSS2T
    # Goku -> TKGLOSS3T
    
    assert "The Force" not in texto_protegido
    assert "Hogwarts" not in texto_protegido
    assert "Goku" not in texto_protegido
    
    # Valida se os tokens foram inseridos
    assert "TKGLOSS" in texto_protegido
    
    # Valida se o dicionário de mapeamento foi gerado corretamente
    valores = list(mapping.values())
    assert "A Força" in valores
    assert "Hogwarts" in valores
    assert "Goku" in valores

def test_remove_shield(gerenciador_mock):
    """Garante que os tokens alienígenas são revertidos para a tradução desejada sem deixar lixo."""
    texto_protegido = "O TKGLOSS0T é forte com o TKGLOSS3T em TKGLOSS2T."
    mapping = {
        "TKGLOSS0T": "A Força",
        "TKGLOSS3T": "Goku",
        "TKGLOSS2T": "Hogwarts"
    }
    
    texto_restaurado = gerenciador_mock.remove_shield(texto_protegido, mapping)
    
    assert texto_restaurado == "O A Força é forte com o Goku em Hogwarts."

def test_remove_shield_resiliencia_ao_google(gerenciador_mock):
    """
    O Google Translate muitas vezes mexe na capitalização e coloca espaços indevidos
    em palavras que ele não entende (nossos tokens). O regex deve cobrir isso.
    """
    texto_maltratado_pelo_google = "O t K GLoss 0 T é forte com tKgLoSs3T em T K G L O S S 2 t."
    mapping = {
        "TKGLOSS0T": "A Força",
        "TKGLOSS3T": "Goku",
        "TKGLOSS2T": "Hogwarts"
    }
    
    texto_restaurado = gerenciador_mock.remove_shield(texto_maltratado_pelo_google, mapping)
    
    assert texto_restaurado == "O A Força é forte com Goku em Hogwarts."


def test_apply_e_remove_shield_tags_ass_e_html(gerenciador_mock):
    """Verifica se tags ASS (como {\\an8}, {\\i1}) e HTML (<i>) são mascaradas e restauradas com precisão."""
    texto_com_tags = r"{\an8}Olá mundo! <i>Goku</i> {\c&H00FFFF&}atacou!"
    protegido, mapping = gerenciador_mock.apply_shield(texto_com_tags)

    # Nenhuma tag original deve estar no texto protegido
    assert r"{\an8}" not in protegido
    assert "<i>" not in protegido
    assert r"{\c&H00FFFF&}" not in protegido

    # A restauração devolve as tags originais com integridade
    restaurado = gerenciador_mock.remove_shield(protegido, mapping)
    assert r"{\an8}" in restaurado
    assert "<i>" in restaurado
    assert r"{\c&H00FFFF&}" in restaurado
    assert "Goku" in restaurado

