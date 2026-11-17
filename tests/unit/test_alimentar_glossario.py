import os
import sys
import pytest
from unittest.mock import MagicMock, mock_open

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from alimentar_glossario import limpar_nome_anime, auto_alimentar

@pytest.mark.parametrize("nome_arquivo, nome_esperado", [
    ("[SubsPlease] Bleach - Thousand-Year Blood War - 30 (1080p).mkv", "Bleach Thousand Year Blood War"),
    ("[Erai-raws] One Piece - 1098 [1080p][Multiple Subtitle].mkv", "One Piece"),
    ("Jujutsu Kaisen S2 - 05.mkv", "Jujutsu Kaisen S2"),
    ("[Crunchyroll] Tensei Shitara Slime Datta Ken 3rd Season - 48 (1080p).mkv", "Tensei Shitara Slime Datta Ken 3rd Season"),
    ("Naruto Shippuden_15.mp4", "Naruto Shippuden"),
    ("Shingeki no Kyojin - The Final Season Part 2 - 01v2 (1080p).mkv", "Shingeki no Kyojin The Final Season Part 2"),
    ("[Judas] TenKen - S02E07.mkv", "TenKen"),
    ("[SubsMix] A Tale of the Secret Saint - 03 (S01E03) - (WEB 1080p AVC x264 AAC 2.0).mkv", "A Tale of the Secret Saint"),
    ("Solo_Leveling_S01E12_1080p.mkv", "Solo Leveling"),
])
def test_limpar_nome_anime(nome_arquivo, nome_esperado):
    """Garante que a regex de limpeza funciona para diversos padrões comuns de fansubs."""
    assert limpar_nome_anime(nome_arquivo) == nome_esperado


def test_auto_alimentar_api_falha(mocker):
    """Garante que se a API do AniList falhar, a função retorna None sem crachar."""
    mock_post = mocker.patch('tradutor.anilist.requests.post')
    mock_post.side_effect = Exception("Erro de conexão simulado")
    
    resultado = auto_alimentar("[SubsPlease] Anime Inexistente - 01 (1080p).mkv")
    assert resultado is None


def test_auto_alimentar_sucesso(mocker):
    """Testa o fluxo feliz: encontra o anime, busca personagens e cria o arquivo no disco mockado."""
    mock_post = mocker.patch('tradutor.anilist.requests.post')
    
    mock_response_anime = MagicMock()
    mock_response_anime.json.return_value = {
        'data': {'Page': {'media': [{'id': 1234, 'title': {'romaji': 'Teste Anime', 'english': 'Test Anime'}}]}}
    }
    
    mock_response_chars = MagicMock()
    mock_response_chars.json.return_value = {
        'data': {'Media': {'characters': {'nodes': [
            {'name': {'first': 'John', 'last': 'Doe', 'full': 'John Doe'}},
            {'name': {'first': 'Jane', 'last': None, 'full': 'Jane'}}
        ]}}}
    }
    
    mock_post.side_effect = [mock_response_anime, mock_response_chars]
    
    # Isola o sistema de arquivos
    mocker.patch('os.makedirs')
    mocked_open = mocker.patch('builtins.open', mock_open())
    
    resultado = auto_alimentar("[Teste] Teste Anime - 01.mkv")
    
    assert resultado is not None
    assert resultado.endswith('Teste Anime.txt')
    
    mocked_open.assert_called_with(resultado, "w", encoding="utf-8")
    
    # Verifica o que foi gravado
    handle = mocked_open()
    calls = [call.args[0] for call in handle.write.mock_calls]
    conteudo_escrito = "".join(calls)
    
    assert "John Doe\n" in conteudo_escrito
    assert "Jane\n" in conteudo_escrito
    assert "John\n" in conteudo_escrito
    assert "Doe\n" in conteudo_escrito


def test_auto_alimentar_preserva_glossario_existente_e_registra_alias(tmp_path, mocker):
    """Garante que glossarios existentes preservam traducoes customizadas e registram # Alias."""
    from tradutor.config import GerenciadorConfig
    from tradutor.glossario import GerenciadorGlossario

    arquivo_existente = tmp_path / "Tensei Shitara Ken Deshita.txt"
    arquivo_existente.write_text(
        "# --- Tensei Shitara Ken Deshita ---\nFran\nTeacher=Mestre\n",
        encoding="utf-8",
    )

    mock_buscar_anime = mocker.patch(
        "tradutor.anilist.buscar_anime",
        return_value=[{"id": 1, "title": {"romaji": "Tensei Shitara Ken Deshita", "english": "Reincarnated as a Sword"}}],
    )
    mock_buscar_personagens = mocker.patch(
        "tradutor.anilist.buscar_personagens",
        return_value=[
            {"name": {"first": "Fran", "last": None, "full": "Fran"}},
            {"name": {"first": "Nell", "last": None, "full": "Nell"}},
        ],
    )

    caminho = auto_alimentar("[Judas] TenKen - S02E07.mkv", pasta_destino=str(tmp_path))

    mock_buscar_anime.assert_called_once_with("TenKen")
    mock_buscar_personagens.assert_called_once_with(1)
    assert caminho == str(arquivo_existente)

    conteudo = arquivo_existente.read_text(encoding="utf-8")
    assert "Teacher=Mestre" in conteudo
    assert "Nell" in conteudo
    assert "# Alias: TenKen" in conteudo

    mocker.patch.object(GerenciadorConfig, "DIRETORIO_GLOSSARIOS", str(tmp_path))
    arq_global = tmp_path / "glossario.txt"
    arq_global.write_text("", encoding="utf-8")

    glossario = GerenciadorGlossario(
        filepath=str(arq_global),
        video_filename="[Judas] TenKen - S02E08.mkv",
        habilitar_auto_alimentar=False,
    )
    assert glossario.glossario_map.get("Teacher") == "Mestre"
    assert glossario.glossario_map.get("Nell") == "Nell"

