import os
import sys
import tempfile
import pytest

# Garante que a raiz do projeto esteja no sys.path
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

# Isola o diretório de logs durante os testes para não gravar na pasta logs/ de produção
os.environ.setdefault(
    "TRADUTOR_LOG_DIR",
    os.path.join(tempfile.gettempdir(), "TradutorLegendas26_pytest_logs"),
)

# Garante configuração automática de caminhos do Tcl/Tk em ambientes Windows
if sys.platform == "win32":
    try:
        import ctypes
        ctypes.cdll.msvcrt._setmaxstdio(2048)
    except Exception:
        pass
    tcl_path = os.path.join(sys.base_prefix, "tcl", "tcl8.6").replace("\\", "/")
    tk_path = os.path.join(sys.base_prefix, "tcl", "tk8.6").replace("\\", "/")
    if os.path.isdir(tcl_path):
        os.environ["TCL_LIBRARY"] = tcl_path
    if os.path.isdir(tk_path):
        os.environ["TK_LIBRARY"] = tk_path


@pytest.fixture(autouse=True)
def isolar_ambiente_testes(tmp_path, request):
    """Isola preferências do usuário e diretório de glossários durante os testes."""
    from tradutor.config import GerenciadorConfig
    from tradutor.config_usuario import PreferenciasUsuario

    orig_arquivo_prefs = PreferenciasUsuario.ARQUIVO_PREFERENCIAS
    orig_dados = PreferenciasUsuario._dados
    orig_dir_gloss = GerenciadorConfig.DIRETORIO_GLOSSARIOS

    temp_prefs = tmp_path / "preferencias.json"
    PreferenciasUsuario.ARQUIVO_PREFERENCIAS = str(temp_prefs)
    PreferenciasUsuario._dados = None

    if request.node.name != "test_leitura_glossarios_grimorio":
        temp_gloss = tmp_path / "_conftest_glossarios"
        temp_gloss.mkdir(parents=True, exist_ok=True)
        GerenciadorConfig.DIRETORIO_GLOSSARIOS = str(temp_gloss)

    try:
        yield
    finally:
        PreferenciasUsuario.ARQUIVO_PREFERENCIAS = orig_arquivo_prefs
        PreferenciasUsuario._dados = orig_dados
        GerenciadorConfig.DIRETORIO_GLOSSARIOS = orig_dir_gloss
