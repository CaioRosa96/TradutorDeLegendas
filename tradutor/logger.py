"""Sistema de logging resiliente com rotacao de 7 dias, teto de 20 MB, fallback de diretorio e captura de crashes."""

import logging
import os
import platform
import re
import sys
import tempfile
import threading
from datetime import datetime, timedelta
from .config import GerenciadorConfig

DIAS_RETENCAO = 7
LIMITE_BYTES_ARQUIVO = 20 * 1024 * 1024  # 20 MB por arquivo diario
VERSAO_APP = "2.9.0"

_PADRAO_ARQUIVO_LOG = re.compile(r"^tradutor_(\d{8})\.log$")
_hooks_instalados = False


def escolher_diretorio_logs(diretorio_preferido: str | None = None) -> str:
    """Seleciona um diretorio com permissao real de escrita para os arquivos de log.

    Testa a criacao de um arquivo sonda na pasta preferida (ao lado do executavel).
    Caso o aplicativo esteja em diretorio protegido (ex.: C:\\Program Files),
    faz fallback automatico para %LOCALAPPDATA%\\TradutorLegendas26\\logs.
    """
    candidatos = []
    if diretorio_preferido:
        candidatos.append(diretorio_preferido)
    else:
        candidatos.append(os.path.join(GerenciadorConfig.DIRETORIO_EXECUCAO, "logs"))

    local_appdata = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    candidatos.append(os.path.join(local_appdata, "TradutorLegendas26", "logs"))
    candidatos.append(os.path.join(tempfile.gettempdir(), "TradutorLegendas26", "logs"))

    for pasta in candidatos:
        try:
            os.makedirs(pasta, exist_ok=True)
            sonda = os.path.join(pasta, ".sonda_escrita")
            with open(sonda, "w", encoding="utf-8") as f:
                f.write("ok")
            os.remove(sonda)
            return pasta
        except OSError:
            continue

    return candidatos[-1]


def expurgar_logs_antigos(
    log_dir: str,
    dias_retencao: int = DIAS_RETENCAO,
    referencia: datetime | None = None,
) -> int:
    """Remove arquivos tradutor_YYYYMMDD.log mais antigos que dias_retencao."""
    if not os.path.isdir(log_dir):
        return 0

    ref = (referencia or datetime.now()).date()
    data_limite = ref - timedelta(days=max(1, dias_retencao) - 1)
    removidos = 0

    try:
        nomes = os.listdir(log_dir)
    except OSError:
        return 0

    for nome in nomes:
        match = _PADRAO_ARQUIVO_LOG.match(nome)
        if not match:
            continue
        try:
            data_arq = datetime.strptime(match.group(1), "%Y%m%d").date()
        except ValueError:
            continue

        if data_arq < data_limite:
            caminho = os.path.join(log_dir, nome)
            try:
                os.remove(caminho)
                removidos += 1
            except OSError:
                pass

    return removidos


def detectar_sistema_operacional() -> str:
    """Identifica a versao real do Windows 10/11 via Registro ou fallback multiplataforma."""
    if sys.platform == "win32":
        try:
            import winreg

            chave_path = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion"
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, chave_path) as chave:
                build_str, _ = winreg.QueryValueEx(chave, "CurrentBuildNumber")
                build_num = int(build_str)
                nome_win = "Windows 11" if build_num >= 22000 else "Windows 10"

                try:
                    display_ver, _ = winreg.QueryValueEx(chave, "DisplayVersion")
                except OSError:
                    display_ver = ""

                try:
                    ubr, _ = winreg.QueryValueEx(chave, "UBR")
                    sufixo_build = f"{build_num}.{ubr}"
                except OSError:
                    sufixo_build = str(build_num)

                partes = [nome_win]
                if display_ver:
                    partes.append(str(display_ver))
                partes.append(f"(build {sufixo_build})")
                return " ".join(partes)
        except Exception:
            pass

    return platform.platform()


def gerar_cabecalho_sessao() -> str:
    """Monta a linha de diagnostico gravada no inicio da sessao de log."""
    so_info = detectar_sistema_operacional()
    py_ver = platform.python_version()
    return f"===== Tradutor de Legendas v{VERSAO_APP} | {so_info} | Python {py_ver} ====="


class HandlerArquivoComTeto(logging.FileHandler):
    """FileHandler que interrompe novas gravacoes diarias ao atingir o teto de bytes."""

    def __init__(self, filename: str, max_bytes: int = LIMITE_BYTES_ARQUIVO, encoding: str = "utf-8"):
        super().__init__(filename, mode="a", encoding=encoding)
        self.max_bytes = max_bytes
        self._bloqueado_por_teto = False

    def emit(self, record: logging.LogRecord):
        if self._bloqueado_por_teto:
            return
        try:
            if self.stream is None:
                self.stream = self._open()
            self.stream.seek(0, os.SEEK_END)
            tamanho_atual = self.stream.tell()
            if tamanho_atual >= self.max_bytes:
                aviso = (
                    f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - [WARNING] - Tradutor - "
                    f"Limite diario de log atingido ({self.max_bytes} bytes); "
                    f"novas entradas serao suprimidas neste arquivo.\n"
                )
                self.stream.write(aviso)
                self.flush()
                self._bloqueado_por_teto = True
                return
        except Exception:
            pass

        super().emit(record)


def instalar_hooks_excecao(logger: logging.Logger):
    """Registra hooks globais para gravar excecoes nao tratadas em arquivo antes de encerrar."""
    global _hooks_instalados
    if _hooks_instalados:
        return

    hook_sys_original = sys.excepthook

    def _excepthook_principal(exc_type, exc_value, exc_tb):
        if not issubclass(exc_type, KeyboardInterrupt):
            logger.critical(
                "Excecao fatal nao tratada na thread principal",
                exc_info=(exc_type, exc_value, exc_tb),
            )
        hook_sys_original(exc_type, exc_value, exc_tb)

    sys.excepthook = _excepthook_principal

    if hasattr(threading, "excepthook"):
        hook_thread_original = threading.excepthook

        def _excepthook_thread(args):
            if not issubclass(args.exc_type, SystemExit):
                logger.critical(
                    f"Excecao nao tratada na thread '{ getattr(args.thread, 'name', 'desconhecida') }'",
                    exc_info=(args.exc_type, args.exc_value, args.exc_traceback),
                )
            hook_thread_original(args)

        threading.excepthook = _excepthook_thread

    _hooks_instalados = True


def setup_logger(
    diretorio_preferido: str | None = None,
    max_bytes: int = LIMITE_BYTES_ARQUIVO,
    dias_retencao: int = DIAS_RETENCAO,
) -> logging.Logger:
    """Configura o sistema de log estruturado com rotacao de 7 dias e teto de tamanho."""
    log_dir = escolher_diretorio_logs(diretorio_preferido)
    expurgar_logs_antigos(log_dir, dias_retencao=dias_retencao)

    filename = datetime.now().strftime("tradutor_%Y%m%d.log")
    filepath = os.path.join(log_dir, filename)

    logger = logging.getLogger("Tradutor")
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        formatter = logging.Formatter("%(asctime)s - [%(levelname)s] - %(name)s - %(message)s")

        fh = HandlerArquivoComTeto(filepath, max_bytes=max_bytes, encoding="utf-8")
        fh.setLevel(logging.INFO)
        fh.setFormatter(formatter)

        ch = logging.StreamHandler()
        ch.setLevel(logging.ERROR)
        ch.setFormatter(formatter)

        logger.addHandler(fh)
        logger.addHandler(ch)
        logger.info(gerar_cabecalho_sessao())
        instalar_hooks_excecao(logger)

    return logger


app_logger = setup_logger()
