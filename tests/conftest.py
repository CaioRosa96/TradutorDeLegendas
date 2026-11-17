import os
import sys
import tempfile

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
    tcl_path = os.path.join(sys.base_prefix, "tcl", "tcl8.6")
    tk_path = os.path.join(sys.base_prefix, "tcl", "tk8.6")
    if os.path.isdir(tcl_path) and "TCL_LIBRARY" not in os.environ:
        os.environ["TCL_LIBRARY"] = tcl_path
    if os.path.isdir(tk_path) and "TK_LIBRARY" not in os.environ:
        os.environ["TK_LIBRARY"] = tk_path
