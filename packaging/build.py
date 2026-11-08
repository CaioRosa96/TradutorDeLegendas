"""Script de automação de build para compilar as versões Moderna e Clássica em .exe.

Utiliza o PyInstaller para empacotar o aplicativo de forma reprodutiva e organizada,
copiando dependências de dados (locales, glossários e mkvtoolnix portátil).
"""

import argparse
import os
import shutil
import subprocess
import sys

DIRETORIO_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def obter_pyinstaller_exec() -> str:
    """Localiza o binário do PyInstaller dentro do ambiente virtual."""
    no_venv = os.path.join(DIRETORIO_RAIZ, "venv", "Scripts", "pyinstaller.exe")
    if os.path.exists(no_venv):
        return no_venv
    return "pyinstaller"


def compilar_alvo(alvo_script: str, nome_saida: str, modo_onefile: bool = False):
    """Executa a compilação de um alvo específico via PyInstaller."""
    pyinstaller = obter_pyinstaller_exec()
    locales_origem = os.path.join(DIRETORIO_RAIZ, "tradutor", "locales")
    glossario_padrao = os.path.join(DIRETORIO_RAIZ, "glossario.txt")
    licenca_mit = os.path.join(DIRETORIO_RAIZ, "LICENSE")
    avisos_terceiros = os.path.join(DIRETORIO_RAIZ, "THIRD_PARTY_NOTICES.md")
    script_alvo = os.path.join(DIRETORIO_RAIZ, alvo_script)

    modo_flag = "--onefile" if modo_onefile else "--onedir"

    cmd = [
        pyinstaller,
        "--noconfirm",
        modo_flag,
        "--windowed",
        "--name", nome_saida,
        "--collect-data", "customtkinter",
        "--collect-data", "tkinterdnd2",
        "--add-data", f"{locales_origem};tradutor/locales",
        "--add-data", f"{glossario_padrao};.",
        "--add-data", f"{licenca_mit};.",
        "--add-data", f"{avisos_terceiros};.",
        "--add-data", f"{os.path.join(DIRETORIO_RAIZ, 'glossarios')};glossarios",
        "--distpath", os.path.join(DIRETORIO_RAIZ, "dist"),
        "--workpath", os.path.join(DIRETORIO_RAIZ, "build"),
        "--specpath", os.path.join(DIRETORIO_RAIZ, "packaging"),
    ]

    cmd.append(script_alvo)

    print(f"\n[BUILD] Iniciando compilação (100% MIT, sem binários GPL embutidos): {nome_saida} ({modo_flag})...")
    subprocess.run(cmd, check=True)
    print(f"[BUILD] Concluído com sucesso: {nome_saida}")

    # No modo onedir, copia apenas recursos de dados sob licença MIT (glossários)
    if not modo_onefile:
        pasta_destino = os.path.join(DIRETORIO_RAIZ, "dist", nome_saida)
        if os.path.exists(pasta_destino):
            origem_gloss = os.path.join(DIRETORIO_RAIZ, "glossarios")
            dest_gloss = os.path.join(pasta_destino, "glossarios")
            if os.path.exists(origem_gloss):
                shutil.copytree(origem_gloss, dest_gloss, dirs_exist_ok=True)
                print(f"[BUILD] Glossários copiados para: {dest_gloss}")


def main():
    parser = argparse.ArgumentParser(description="Automação de Build do Tradutor de Legendas (.exe)")
    parser.add_argument(
        "--alvo",
        choices=["moderno", "classico", "todos"],
        default="todos",
        help="Qual versão compilar (moderno, classico ou todos)"
    )
    parser.add_argument(
        "--onefile",
        action="store_true",
        help="Gera um único executável .exe portátil em vez de pasta onedir"
    )
    args = parser.parse_args()

    alvos = []
    if args.alvo in ("moderno", "todos"):
        alvos.append(("TradutorLegendas26.py", "TradutorLegendas"))
    if args.alvo in ("classico", "todos"):
        alvos.append(("TradutorLegendas26_Classico.py", "TradutorLegendas_Classico"))

    for script, nome in alvos:
        compilar_alvo(script, nome, modo_onefile=args.onefile)

    print("\n[BUILD] Processo de empacotamento finalizado! Verifique a pasta 'dist/'.")


if __name__ == "__main__":
    main()
