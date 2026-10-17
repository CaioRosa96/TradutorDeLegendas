import os
import re
from .config import GerenciadorConfig

try:
    import requests
except ImportError:
    requests = None

ANILIST_URL = "https://graphql.anilist.co"


def buscar_anime(nome):
    """Busca títulos de animes no AniList via GraphQL."""
    query = '''
    query ($search: String) {
      Page(page: 1, perPage: 10) {
        media(search: $search, type: ANIME) {
          id
          title {
            romaji
            english
          }
        }
      }
    }
    '''
    variables = {'search': nome}

    if requests is None:
        return []

    try:
        response = requests.post(ANILIST_URL, json={'query': query, 'variables': variables}, timeout=10)
        response.raise_for_status()
        data = response.json()
        return data.get('data', {}).get('Page', {}).get('media', [])
    except Exception:
        return []


def buscar_personagens(anime_id):
    """Busca lista de personagens associados ao anime pelo ID."""
    query = '''
    query ($id: Int) {
      Media(id: $id) {
        characters(page: 1, perPage: 50, sort: [ROLE, RELEVANCE, ID]) {
          nodes {
            name {
              first
              last
              full
            }
          }
        }
      }
    }
    '''
    variables = {'id': anime_id}

    if requests is None:
        return []

    try:
        response = requests.post(ANILIST_URL, json={'query': query, 'variables': variables}, timeout=10)
        response.raise_for_status()
        data = response.json()
        return data.get('data', {}).get('Media', {}).get('characters', {}).get('nodes', [])
    except Exception:
        return []


def limpar_nome_anime(nome_arquivo):
    """Limpa tags de release, grupos, extensões e números de episódio do nome do arquivo."""
    nome = nome_arquivo.rsplit('.', 1)[0]
    # Remove tags em colchetes ou parênteses [SubsPlease], (1080p)
    nome = re.sub(r'\[.*?\]|\(.*?\)', '', nome)
    # Remove números de episódio finais (ex: - 12, - 01v2, _15)
    nome = re.sub(r'[-_]\s*\d+.*$', '', nome)
    # Limpa espaços e hifens
    nome = nome.replace('_', ' ').replace('-', ' ').strip()
    nome = re.sub(r'\s+', ' ', nome)
    return nome


def extrair_nomes_ordenados(personagens):
    """Extrai nomes completos, primeiros e últimos nomes, ordenando por tamanho decrescente."""
    lista_nomes = set()
    for char in personagens:
        name_dict = char.get('name', {})
        nome_completo = name_dict.get('full')
        primeiro_nome = name_dict.get('first')
        ultimo_nome = name_dict.get('last')

        if nome_completo:
            lista_nomes.add(nome_completo.strip())
        if primeiro_nome:
            lista_nomes.add(primeiro_nome.strip())
        if ultimo_nome:
            lista_nomes.add(ultimo_nome.strip())

    return sorted(list(lista_nomes), key=len, reverse=True)


def sanitizar_nome_arquivo(nome):
    """Remove caracteres inválidos para nomes de arquivos no sistema de arquivos."""
    return "".join([c for c in nome if c.isalpha() or c.isdigit() or c in ' -_()']).strip()


def auto_alimentar(nome_video, pasta_destino=None):
    """Busca silenciosa do anime e cria o arquivo de glossário com nomes de personagens."""
    nome_limpo = limpar_nome_anime(nome_video)
    if not nome_limpo:
        return None

    animes = buscar_anime(nome_limpo)
    if not animes:
        return None

    anime = animes[0]
    anime_id = anime.get('id')
    titulo_info = anime.get('title', {})
    titulo = titulo_info.get('romaji') or titulo_info.get('english') or nome_limpo

    nome_arquivo = sanitizar_nome_arquivo(titulo)
    personagens = buscar_personagens(anime_id)
    if not personagens:
        return None

    lista_ordenada = extrair_nomes_ordenados(personagens)

    destino_dir = pasta_destino or GerenciadorConfig.DIRETORIO_GLOSSARIOS
    os.makedirs(destino_dir, exist_ok=True)

    caminho_arquivo = os.path.join(destino_dir, f"{nome_arquivo}.txt")

    with open(caminho_arquivo, "w", encoding="utf-8") as f:
        f.write(f"# --- {titulo} ---\n")
        f.write("# Personagens extraídos via auto_alimentar\n\n")
        for nome in lista_ordenada:
            if nome:
                f.write(f"{nome}\n")

    return caminho_arquivo
