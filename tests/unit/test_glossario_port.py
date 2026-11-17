"""Testes unitários para o contrato BuscadorEntidadesPort e seus adaptadores."""
import os
import pytest
from unittest.mock import MagicMock

from tradutor.config import GerenciadorConfig
from tradutor.glossario import GerenciadorGlossario
from tradutor.glossario_port import (
    AdaptadorAniListGraphQL,
    AdaptadorMemoriaGlossario,
    BuscadorEntidadesPort,
)


# ============================================================================
# 1. Validação de Contrato (Protocol)
# ============================================================================


def test_contrato_buscador_entidades_port_conformidade():
    """Garante que os adaptadores implementam o protocolo BuscadorEntidadesPort."""
    adaptador_memoria = AdaptadorMemoriaGlossario()
    adaptador_anilist = AdaptadorAniListGraphQL()

    assert isinstance(adaptador_memoria, BuscadorEntidadesPort)
    assert isinstance(adaptador_anilist, BuscadorEntidadesPort)


def test_contrato_buscador_entidades_port_objeto_invalido():
    """Garante que objetos sem o método obrigatório não sejam reconhecidos como instâncias do protocolo."""
    class ObjetoIncompleto:
        def outro_metodo(self):
            return []

    assert not isinstance(ObjetoIncompleto(), BuscadorEntidadesPort)


def test_contrato_buscador_entidades_port_classe_customizada():
    """Garante que qualquer implementação compatível em tempo de execução respeite o protocolo."""
    class BuscadorCustomizado:
        def buscar_nomes_proprios(self, titulo_obra: str) -> list[str]:
            return ["Termo1", "Termo2"]

    instancia = BuscadorCustomizado()
    assert isinstance(instancia, BuscadorEntidadesPort)
    assert instancia.buscar_nomes_proprios("obra") == ["Termo1", "Termo2"]


# ============================================================================
# 2. Adaptador em Memória (AdaptadorMemoriaGlossario)
# ============================================================================


def test_adaptador_memoria_vazio():
    """Adaptador sem registros deve retornar lista vazia para qualquer título."""
    adaptador = AdaptadorMemoriaGlossario()
    assert adaptador.buscar_nomes_proprios("Bleach") == []
    assert adaptador.buscar_nomes_proprios("") == []


def test_adaptador_memoria_com_dicionario_casamento_exato():
    """Garante recuperação exata de entidades configuradas via dicionário."""
    entidades = {
        "Bleach": ["Ichigo Kurosaki", "Rukia Kuchiki"],
        "Naruto": ["Naruto Uzumaki", "Sasuke Uchiha"],
    }
    adaptador = AdaptadorMemoriaGlossario(entidades)

    resultado = adaptador.buscar_nomes_proprios("Bleach")
    assert resultado == ["Ichigo Kurosaki", "Rukia Kuchiki"]

    # Valida que não altera o estado interno (cópia defensiva)
    resultado.append("ItemInvasor")
    assert "ItemInvasor" not in adaptador.buscar_nomes_proprios("Bleach")


def test_adaptador_memoria_casamento_parcial_nome_arquivo():
    """Garante que nomes de arquivo com release tags encontrem a obra configurada."""
    entidades = {
        "Frieren": ["Frieren", "Fern", "Stark"],
    }
    adaptador = AdaptadorMemoriaGlossario(entidades)

    resultado = adaptador.buscar_nomes_proprios("[SubsPlease] Sousou no Frieren - 01 (1080p).mkv")
    assert resultado == ["Frieren", "Fern", "Stark"]


def test_adaptador_memoria_com_lista_direta():
    """Quando inicializado com lista direta, retorna os termos para qualquer consulta."""
    termos = ["Goku", "Vegeta", "Piccolo"]
    adaptador = AdaptadorMemoriaGlossario(termos)

    assert adaptador.buscar_nomes_proprios("Dragon Ball Z") == termos
    assert adaptador.buscar_nomes_proprios("Outro Anime") == termos
    assert adaptador.buscar_nomes_proprios("") == termos


def test_adaptador_memoria_cadastrar_obra():
    """Permite registrar obras e entidades dinamicamente."""
    adaptador = AdaptadorMemoriaGlossario()
    assert adaptador.buscar_nomes_proprios("One Piece") == []

    adaptador.cadastrar_obra("One Piece", ["Luffy", "Zoro", "Nami"])
    assert adaptador.buscar_nomes_proprios("One Piece") == ["Luffy", "Zoro", "Nami"]
    assert adaptador.buscar_nomes_proprios("[Erai-raws] One Piece - 1098.mkv") == ["Luffy", "Zoro", "Nami"]


# ============================================================================
# 3. Adaptador AniList GraphQL (AdaptadorAniListGraphQL)
# ============================================================================


def test_adaptador_anilist_titulo_vazio():
    """Títulos vazios ou nulos devem retornar lista vazia sem realizar requisições."""
    adaptador = AdaptadorAniListGraphQL()
    assert adaptador.buscar_nomes_proprios("") == []
    assert adaptador.buscar_nomes_proprios("   ") == []


def test_adaptador_anilist_sucesso_delegacao(mocker):
    """Garante delegação correta para limpar_nome_anime, buscar_anime, buscar_personagens e ordenação."""
    mock_buscar_anime = mocker.patch(
        "tradutor.glossario_port.buscar_anime",
        return_value=[{"id": 42, "title": {"romaji": "Bleach", "english": "Bleach"}}],
    )
    mock_buscar_personagens = mocker.patch(
        "tradutor.glossario_port.buscar_personagens",
        return_value=[
            {"name": {"first": "Ichigo", "last": "Kurosaki", "full": "Ichigo Kurosaki"}},
            {"name": {"first": "Rukia", "last": "Kuchiki", "full": "Rukia Kuchiki"}},
        ],
    )

    adaptador = AdaptadorAniListGraphQL()
    resultado = adaptador.buscar_nomes_proprios("[SubsPlease] Bleach - S01E01.mkv")

    mock_buscar_anime.assert_called_once_with("Bleach")
    mock_buscar_personagens.assert_called_once_with(42)

    assert "Ichigo Kurosaki" in resultado
    assert "Rukia Kuchiki" in resultado
    assert "Ichigo" in resultado


def test_adaptador_anilist_anime_nao_encontrado(mocker):
    """Quando o AniList não encontra o anime, retorna lista vazia."""
    mocker.patch("tradutor.glossario_port.buscar_anime", return_value=[])

    adaptador = AdaptadorAniListGraphQL()
    resultado = adaptador.buscar_nomes_proprios("Obra Totalmente Desconhecida")
    assert resultado == []


def test_adaptador_anilist_personagens_vazios(mocker):
    """Quando a API não retorna personagens para o ID, retorna lista vazia."""
    mocker.patch(
        "tradutor.glossario_port.buscar_anime",
        return_value=[{"id": 999, "title": {"romaji": "Anime Sem Personagens"}}],
    )
    mocker.patch("tradutor.glossario_port.buscar_personagens", return_value=[])

    adaptador = AdaptadorAniListGraphQL()
    resultado = adaptador.buscar_nomes_proprios("Anime Sem Personagens")
    assert resultado == []


def test_adaptador_anilist_resiliencia_a_excecoes(mocker):
    """Falhas de conexão ou erros na API são capturados com segurança retornando lista vazia."""
    mocker.patch(
        "tradutor.glossario_port.buscar_anime",
        side_effect=Exception("Erro de timeout na rede"),
    )

    adaptador = AdaptadorAniListGraphQL()
    resultado = adaptador.buscar_nomes_proprios("Bleach")
    assert resultado == []


def test_adaptador_anilist_persistencia_arquivo(tmp_path, mocker):
    """Quando persistir_arquivo=True e pasta_destino informada, salva os termos em arquivo no disco."""
    mocker.patch(
        "tradutor.glossario_port.buscar_anime",
        return_value=[{"id": 101, "title": {"romaji": "Solo Leveling", "english": "Solo Leveling"}}],
    )
    mocker.patch(
        "tradutor.glossario_port.buscar_personagens",
        return_value=[
            {"name": {"first": "Jin-woo", "last": "Sung", "full": "Sung Jin-woo"}},
        ],
    )

    adaptador = AdaptadorAniListGraphQL(pasta_destino=str(tmp_path), persistir_arquivo=True)
    resultado = adaptador.buscar_nomes_proprios("Solo Leveling")

    assert "Sung Jin-woo" in resultado
    arquivo_esperado = tmp_path / "Solo Leveling.txt"
    assert arquivo_esperado.exists()

    conteudo = arquivo_esperado.read_text(encoding="utf-8")
    assert "Sung Jin-woo" in conteudo
    assert "# --- Solo Leveling ---" in conteudo


# ============================================================================
# 4. Injeção e Fallback no GerenciadorGlossario
# ============================================================================


def test_gerenciador_glossario_com_buscador_injetado_em_memoria(tmp_path, mocker):
    """Garante enriquecimento do glossário com entidades injetadas via AdaptadorMemoriaGlossario."""
    mocker.patch.object(GerenciadorConfig, "DIRETORIO_GLOSSARIOS", str(tmp_path / "glossarios_inexistente"))
    arquivo_global = tmp_path / "glossario_global.txt"
    arquivo_global.write_text("# Global\n", encoding="utf-8")

    adaptador_memoria = AdaptadorMemoriaGlossario({
        "Jujutsu": ["Gojo Satoru", "Yuji Itadori", "Megumi Fushiguro"],
    })

    gerenciador = GerenciadorGlossario(
        filepath=str(arquivo_global),
        video_filename="[Crunchyroll] Jujutsu Kaisen - 01.mkv",
        habilitar_auto_alimentar=True,
        buscador_entidades=adaptador_memoria,
    )

    assert "Gojo Satoru" in gerenciador.glossario_map
    assert "Yuji Itadori" in gerenciador.glossario_map
    assert "Megumi Fushiguro" in gerenciador.glossario_map
    assert gerenciador.glossario_map["Gojo Satoru"] == "Gojo Satoru"


def test_gerenciador_glossario_fallback_para_anilist(tmp_path, mocker):
    """Garante que se nenhum buscador for injetado, o fallback utiliza AdaptadorAniListGraphQL."""
    mocker.patch.object(GerenciadorConfig, "DIRETORIO_GLOSSARIOS", str(tmp_path / "glossarios_inexistente"))
    arquivo_global = tmp_path / "glossario_global.txt"
    arquivo_global.write_text("", encoding="utf-8")

    mock_buscar_proprios = mocker.patch.object(
        AdaptadorAniListGraphQL,
        "buscar_nomes_proprios",
        return_value=["Edward Elric", "Alphonse Elric"],
    )

    gerenciador = GerenciadorGlossario(
        filepath=str(arquivo_global),
        video_filename="Fullmetal Alchemist - 01.mkv",
        habilitar_auto_alimentar=True,
        buscador_entidades=None,
    )

    mock_buscar_proprios.assert_called_once_with("Fullmetal Alchemist - 01.mkv")
    assert "Edward Elric" in gerenciador.glossario_map
    assert "Alphonse Elric" in gerenciador.glossario_map


def test_gerenciador_glossario_auto_alimentar_desabilitado(tmp_path, mocker):
    """Quando habilitar_auto_alimentar=False, nem o buscador injetado nem a API são chamados."""
    arquivo_global = tmp_path / "glossario_global.txt"
    arquivo_global.write_text("", encoding="utf-8")

    mock_buscador = MagicMock(spec=BuscadorEntidadesPort)

    gerenciador = GerenciadorGlossario(
        filepath=str(arquivo_global),
        video_filename="Naruto Shippuden 01.mkv",
        habilitar_auto_alimentar=False,
        buscador_entidades=mock_buscador,
    )

    mock_buscador.buscar_nomes_proprios.assert_not_called()
    assert gerenciador.glossario_map == {}


def test_gerenciador_glossario_prioriza_arquivo_local_existente(tmp_path, mocker):
    """Se o arquivo local do anime já existir, ele é carregado e o buscador não é consultado."""
    dir_especificos = tmp_path / "glossarios"
    dir_especificos.mkdir(parents=True)
    mocker.patch.object(GerenciadorConfig, "DIRETORIO_GLOSSARIOS", str(dir_especificos))

    arquivo_local = dir_especificos / "Bleach.txt"
    arquivo_local.write_text("Ichigo\nRukia\n", encoding="utf-8")

    arquivo_global = tmp_path / "glossario_global.txt"
    arquivo_global.write_text("", encoding="utf-8")

    mock_buscador = MagicMock(spec=BuscadorEntidadesPort)

    gerenciador = GerenciadorGlossario(
        filepath=str(arquivo_global),
        video_filename="[SubsPlease] Bleach - 01.mkv",
        habilitar_auto_alimentar=True,
        buscador_entidades=mock_buscador,
    )

    mock_buscador.buscar_nomes_proprios.assert_not_called()
    assert "Ichigo" in gerenciador.glossario_map
    assert "Rukia" in gerenciador.glossario_map
