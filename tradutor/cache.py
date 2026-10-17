import sqlite3
import hashlib
import os
from .config import GerenciadorConfig

class CacheTraducoes:
    """
    Sistema de Caching em Banco de Dados (SQLite) para traduções.
    Previne que o mesmo bloco exato de texto seja enviado ao Google duas vezes,
    economizando tempo e protegendo contra rate-limits.
    Funciona como Checkpoint: se uma tradução grande cair aos 90%,
    a próxima tentativa vai pular os primeiros 90% instantaneamente.
    """
    TIMEOUT_SEGUNDOS = 30.0

    def __init__(self, db_path="cache_traducoes.db"):
        if os.path.isabs(db_path):
            self.db_path = db_path
        else:
            self.db_path = os.path.join(GerenciadorConfig.DIRETORIO_EXECUCAO, db_path)
        self._init_db()

    def _get_connection(self):
        """Retorna uma conexão SQLite configurada com timeout estendido para alta concorrência."""
        return sqlite3.connect(self.db_path, timeout=self.TIMEOUT_SEGUNDOS)

    def _init_db(self):
        """Cria a tabela de cache e ativa o modo WAL para leitura/escrita concorrente."""
        with self._get_connection() as conn:
            conn.execute('PRAGMA journal_mode=WAL;')
            conn.execute('PRAGMA synchronous=NORMAL;')
            conn.execute('''
                CREATE TABLE IF NOT EXISTS traducoes (
                    hash_origem TEXT PRIMARY KEY,
                    src_lang TEXT,
                    dest_lang TEXT,
                    texto_traduzido TEXT,
                    data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
    def _gerar_hash(self, texto, src_lang, dest_lang):
        """Gera uma assinatura única (SHA-256) para o bloco de texto + idiomas."""
        raw = f"{src_lang}_{dest_lang}_{texto}"
        return hashlib.sha256(raw.encode('utf-8')).hexdigest()
        
    def get(self, texto, src_lang, dest_lang):
        """Busca uma tradução no cache. Retorna None se não existir."""
        h = self._gerar_hash(texto, src_lang, dest_lang)
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT texto_traduzido FROM traducoes WHERE hash_origem=?", (h,))
            row = cursor.fetchone()
            if row:
                return row[0]
        return None
        
    def put(self, texto, src_lang, dest_lang, texto_traduzido):
        """Salva uma nova tradução no cache."""
        h = self._gerar_hash(texto, src_lang, dest_lang)
        with self._get_connection() as conn:
            conn.execute('''
                INSERT OR REPLACE INTO traducoes 
                (hash_origem, src_lang, dest_lang, texto_traduzido) 
                VALUES (?, ?, ?, ?)
            ''', (h, src_lang, dest_lang, texto_traduzido))

    def contar_traducoes(self) -> int:
        """Retorna o número total de traduções armazenadas no cache."""
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM traducoes")
            row = cursor.fetchone()
            return row[0] if row else 0

    def obter_tamanho_bytes(self) -> int:
        """Retorna o tamanho do arquivo SQLite do cache em bytes."""
        if os.path.exists(self.db_path):
            return os.path.getsize(self.db_path)
        return 0

    def limpar_tudo(self):
        """Remove todos os registros do cache e executa VACUUM para otimizar espaço."""
        conn = self._get_connection()
        try:
            conn.execute("DELETE FROM traducoes;")
            conn.commit()
            conn.isolation_level = None
            conn.execute("VACUUM;")
        finally:
            conn.close()


