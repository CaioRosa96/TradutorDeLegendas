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
    caminho_str = os.fspath(nome_arquivo) if not isinstance(nome_arquivo, str) else nome_arquivo
    caminho_str = caminho_str.strip().rstrip("/\\")
    base = os.path.basename(caminho_str.replace('\\', '/'))
    nome = base.rsplit('.', 1)[0]
    # Remove tags em colchetes ou parênteses [SubsPlease], (1080p)
    nome = re.sub(r'\[.*?\]|\(.*?\)', '', nome)
    # Remove marcadores no formato S02E07, - S01E03, _S02E12
    nome = re.sub(r'(?i)(?:[-_ ]+|\b)S\d+\s*E\d+(?:v\d+)?(?![a-zA-Z0-9]).*$', '', nome)
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
    if not nome:
        return "Anime_Desconhecido"
    limpo = "".join([c for c in nome if c.isalpha() or c.isdigit() or c in ' -_()']).strip()
    return limpo or "Anime_Desconhecido"


def salvar_glossario_arquivo(
    pasta_destino: str,
    titulo: str,
    anime_id: int | str,
    nome_limpo: str,
    nomes: list[str],
) -> str | None:
    """Persiste ou atualiza arquivo de glossário local com nomes extraídos e alias."""
    if not nomes:
        return None
    nome_arquivo = sanitizar_nome_arquivo(titulo) or f"Anime_{anime_id}"
    if pasta_destino:
        os.makedirs(pasta_destino, exist_ok=True)

    caminho_arquivo = os.path.join(pasta_destino or "", f"{nome_arquivo}.txt")
    alias_candidato = nome_limpo if (nome_limpo and nome_arquivo.lower() not in nome_limpo.lower()) else None

    if os.path.isfile(caminho_arquivo):
        _atualizar_glossario_existente(caminho_arquivo, nomes, alias_candidato)
    else:
        with open(caminho_arquivo, "w", encoding="utf-8") as f:
            f.write(f"# --- {titulo} ---\n")
            if alias_candidato:
                f.write(f"# Alias: {alias_candidato}\n")
            f.write("# Personagens extraídos via auto_alimentar\n\n")
            for nome in nomes:
                if nome:
                    f.write(f"{nome}\n")

    return caminho_arquivo


def auto_alimentar(nome_video, pasta_destino=None, anime_title=None, anilist_id=None):
    """Busca silenciosa do anime e cria o arquivo de glossário com nomes de personagens."""
    alias_video = limpar_nome_anime(nome_video) if nome_video else ""
    if anime_title:
        nome_limpo = anime_title.strip()
    else:
        nome_limpo = alias_video

    if not nome_limpo and anilist_id is None:
        return None

    if anilist_id is not None:
        anime_id = anilist_id
        titulo = anime_title or nome_limpo or f"Anime_{anilist_id}"
    else:
        animes = buscar_anime(nome_limpo)
        if not animes:
            return None
        anime = animes[0]
        anime_id = anime.get('id')
        titulo_info = anime.get('title', {})
        titulo = anime_title or titulo_info.get('romaji') or titulo_info.get('english') or nome_limpo

    personagens = buscar_personagens(anime_id)
    if not personagens:
        return None

    lista_ordenada = extrair_nomes_ordenados(personagens)
    destino_dir = pasta_destino or GerenciadorConfig.DIRETORIO_GLOSSARIOS

    return salvar_glossario_arquivo(
        pasta_destino=destino_dir,
        titulo=titulo,
        anime_id=anime_id,
        nome_limpo=alias_video or nome_limpo,
        nomes=lista_ordenada,
    )


def _atualizar_glossario_existente(
    caminho_arquivo: str, lista_ordenada: list[str], alias_candidato: str | None
) -> None:
    """Mescla novos personagens e alias em um glossário existente preservando customizações."""
    with open(caminho_arquivo, "r", encoding="utf-8") as f:
        linhas = f.read().splitlines()

    termos_existentes: set[str] = set()
    aliases_existentes: set[str] = set()
    indice_alias = None

    for i, linha in enumerate(linhas):
        limpa = linha.strip()
        if not limpa:
            continue
        if limpa.startswith("#"):
            if limpa.lower().startswith("# alias:"):
                indice_alias = i
                bruto = limpa.split(":", 1)[1]
                aliases_existentes.update(a.strip().lower() for a in bruto.split(",") if a.strip())
            continue

        termos_existentes.add(limpa.lower())
        if "=" in limpa:
            termos_existentes.add(limpa.split("=", 1)[0].strip().lower())

    if alias_candidato and alias_candidato.lower() not in aliases_existentes:
        if indice_alias is not None:
            sufixo = alias_candidato if linhas[indice_alias].rstrip().endswith(":") else f", {alias_candidato}"
            linhas[indice_alias] = f"{linhas[indice_alias].rstrip()}{sufixo}"
        else:
            pos_insercao = 1 if linhas and linhas[0].strip().startswith("# ---") else 0
            linhas.insert(pos_insercao, f"# Alias: {alias_candidato}")

    novos_nomes = [nome for nome in lista_ordenada if nome and nome.lower() not in termos_existentes]
    while linhas and not linhas[-1].strip():
        linhas.pop()
    linhas.extend(novos_nomes)

    with open(caminho_arquivo, "w", encoding="utf-8") as f:
        f.write("\n".join(linhas) + "\n")
