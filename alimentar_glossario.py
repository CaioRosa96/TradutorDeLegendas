"""CLI Interativo para Alimentação de Glossários via AniList.

Delega as regras de negócio para o módulo de domínio `tradutor.anilist`.
"""

import os
from tradutor.config import GerenciadorConfig
from tradutor.anilist import (
    requests,
    buscar_anime,
    buscar_personagens,
    limpar_nome_anime,
    extrair_nomes_ordenados,
    sanitizar_nome_arquivo,
    auto_alimentar,
)


def main():
    print("=" * 50)
    print("EXTRATOR AUTOMÁTICO DE PERSONAGENS (AniList)")
    print("=" * 50)

    nome_busca = input("Digite o nome do anime que deseja buscar: ").strip()
    if not nome_busca:
        return

    print("\nBuscando...")
    animes = buscar_anime(nome_busca)

    if not animes:
        print("Nenhum anime encontrado.")
        return

    print("\nResultados encontrados:")
    for i, anime in enumerate(animes):
        titulo_romaji = anime['title'].get('romaji') or ""
        titulo_eng = anime['title'].get('english') or ""
        print(f"[{i+1}] {titulo_romaji} / {titulo_eng}")

    escolha = input("\nEscolha o número do anime (ou pressione Enter para cancelar): ").strip()
    if not escolha.isdigit() or int(escolha) < 1 or int(escolha) > len(animes):
        print("Operação cancelada.")
        return

    anime_escolhido = animes[int(escolha) - 1]
    anime_id = anime_escolhido['id']
    titulo_principal = anime_escolhido['title'].get('romaji') or anime_escolhido['title'].get('english')

    print(f"\nO anime selecionado foi: {titulo_principal}")
    nome_arquivo = input("Qual deve ser o nome do arquivo? (Deixe em branco para usar o título original): ").strip()
    if not nome_arquivo:
        nome_arquivo = titulo_principal

    nome_arquivo = sanitizar_nome_arquivo(nome_arquivo)

    print("\nBuscando os nomes dos personagens mais relevantes...")
    personagens = buscar_personagens(anime_id)

    if not personagens:
        print("Nenhum personagem encontrado.")
        return

    lista_ordenada = extrair_nomes_ordenados(personagens)
    pasta_glossarios = GerenciadorConfig.DIRETORIO_GLOSSARIOS
    os.makedirs(pasta_glossarios, exist_ok=True)

    caminho_arquivo = os.path.join(pasta_glossarios, f"{nome_arquivo}.txt")

    with open(caminho_arquivo, "w", encoding="utf-8") as f:
        f.write(f"# --- {titulo_principal} ---\n")
        f.write("# Personagens extraídos automaticamente via AniList API\n")
        f.write("# Adicione ou modifique abaixo conforme necessário:\n\n")
        for nome in lista_ordenada:
            if nome:
                f.write(f"{nome}\n")

    print(f"\n[SUCESSO] {len(lista_ordenada)} termos salvos em: {caminho_arquivo}")


if __name__ == "__main__":
    main()
