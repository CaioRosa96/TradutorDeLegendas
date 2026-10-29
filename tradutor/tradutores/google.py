import threading
import time
from googletrans import Translator
from .base import ITradutor, ExcecaoDisjuntorAberto
from ..logger import app_logger

class MotorTraducaoGoogle(ITradutor):
    """
    Implementação Concreta para a API do Google Translate.
    Encapsula rate-limits, retentativas e possui Circuit Breaker thread-safe:
    se falhar 5 vezes seguidas, para de tentar por 60 segundos
    para evitar banimentos permanentes ou travamentos da thread.
    """
    
    def __init__(self, max_retries=3, failure_threshold=5, recovery_timeout=60):
        self._local = threading.local()
        self._max_retries = max_retries
        self._lock = threading.Lock()
        
        # Estado do Circuit Breaker
        self._failure_count = 0
        self._failure_threshold = failure_threshold
        self._last_failure_time = 0
        self._recovery_timeout = recovery_timeout
        self._is_open = False

    def _get_engine(self):
        """Retorna uma instância de Translator isolada para a thread atual."""
        engine = getattr(self._local, "engine", None)
        if engine is None:
            engine = Translator()
            self._local.engine = engine
        return engine

    @property
    def _engine(self):
        """Propriedade de compatibilidade que retorna o cliente isolado da thread atual."""
        return self._get_engine()

    def _check_circuit(self):
        deve_logar_half_open = False
        with self._lock:
            if self._is_open:
                if time.time() - self._last_failure_time > self._recovery_timeout:
                    self._is_open = False
                    deve_logar_half_open = True
                else:
                    raise ExcecaoDisjuntorAberto("Circuit Breaker ABERTO: Abortando para evitar banimentos.")
        if deve_logar_half_open:
            app_logger.info("Circuit Breaker: Testando recuperação da API (Half-Open).")

    def _record_failure(self):
        deve_logar_erro = False
        with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.time()
            if self._failure_count >= self._failure_threshold:
                self._is_open = True
                deve_logar_erro = True
        if deve_logar_erro:
            app_logger.error(f"Circuit Breaker disparado! Atingiu {self._failure_threshold} falhas seguidas.")

    def _record_success(self):
        deve_logar_recuperacao = False
        with self._lock:
            if self._failure_count > 0:
                deve_logar_recuperacao = True
            self._failure_count = 0
            self._is_open = False
        if deve_logar_recuperacao:
            app_logger.info("Circuit Breaker: Conexão estabilizada. Resetando falhas.")

    def translate(self, text: str, src_lang: str, dest_lang: str) -> str:
        self._check_circuit()
        
        for tentativa in range(self._max_retries):
            try:
                resposta = self._engine.translate(text, src=src_lang, dest=dest_lang)
                if resposta is None or getattr(resposta, "text", None) is None:
                    raise RuntimeError("Resposta vazia retornada pela API do Google.")
                self._record_success()
                return resposta.text

            except (TypeError, ValueError, AttributeError) as e:
                self._record_failure()
                app_logger.error(f"Erro permanente na API do Google: {e}")
                raise RuntimeError(f"Erro permanente na API do Google: {e}")
            except Exception as e:
                if tentativa == self._max_retries - 1:
                    self._record_failure()
                    raise RuntimeError(f"Falha no Google após {self._max_retries} tentativas: {e}")
                
                app_logger.warning(f"Google API falhou. Retentando em breve... Erro: {e}")
                time.sleep(2 ** tentativa)
