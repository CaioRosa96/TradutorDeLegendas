import sqlite3
import hashlib
import os
import threading
from contextlib import closing
from typing import Mapping, Sequence
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
    CHUNK_PARAMETROS = 500

    def __init__(self, db_path="cache_traducoes.db"):
        self._lock = threading.RLock()
        if os.path.isabs(db_path):
            self.db_path = db_path
        else:
            self.db_path = os.path.join(GerenciadorConfig.DIRETORIO_EXECUCAO, db_path)
        self._init_db()

    def _get_connection(self):
        """Retorna uma conexão SQLite configurada com timeout estendido para alta concorrência."""
        conn = sqlite3.connect(self.db_path, timeout=self.TIMEOUT_SEGUNDOS, check_same_thread=False)
        conn.execute("PRAGMA busy_timeout=30000;")
        return conn

    def _init_db(self):
        """Cria a tabela de cache e ativa o modo WAL para leitura/escrita concorrente."""
        with self._lock, closing(self._get_connection()) as conn, conn:
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
            
    def _gerar_hash(self, texto: str, src_lang: str, dest_lang: str) -> str:
        """Gera uma assinatura única (SHA-256) para o bloco de texto + idiomas."""
        raw = f"{src_lang}_{dest_lang}_{texto}"
        return hashlib.sha256(raw.encode('utf-8')).hexdigest()
        
    def get(self, texto: str, src_lang: str, dest_lang: str) -> str | None:
        """Busca uma tradução no cache. Retorna None se não existir."""
        h = self._gerar_hash(texto, src_lang, dest_lang)
        with closing(self._get_connection()) as conn:
            cursor = conn.execute("SELECT texto_traduzido FROM traducoes WHERE hash_origem=?", (h,))
            row = cursor.fetchone()
            if row:
                return row[0]
        return None
        
    def put(self, texto: str, src_lang: str, dest_lang: str, texto_traduzido: str) -> None:
        """Salva uma nova tradução no cache."""
        if texto_traduzido is None:
            return
        h = self._gerar_hash(texto, src_lang, dest_lang)
        with self._lock, closing(self._get_connection()) as conn, conn:
            conn.execute('''
                INSERT OR REPLACE INTO traducoes 
                (hash_origem, src_lang, dest_lang, texto_traduzido) 
                VALUES (?, ?, ?, ?)
            ''', (h, src_lang, dest_lang, texto_traduzido))

    def get_many(self, textos: Sequence[str], src_lang: str, dest_lang: str) -> dict[str, str]:
        """Busca traduções em lote para múltiplos textos com os mesmos idiomas.

        Fatia a busca em chunks de até 500 parâmetros para respeitar SQLITE_MAX_VARIABLE_NUMBER.
        Retorna dicionário {texto_original: texto_traduzido}.
        """
        if not textos:
            return {}

        hash_para_texto: dict[str, str] = {}
        for t in textos:
            h = self._gerar_hash(t, src_lang, dest_lang)
            hash_para_texto[h] = t

        hashes = list(hash_para_texto.keys())
        resultados: dict[str, str] = {}

        with closing(self._get_connection()) as conn:
            for i in range(0, len(hashes), self.CHUNK_PARAMETROS):
                chunk = hashes[i : i + self.CHUNK_PARAMETROS]
                placeholders = ",".join("?" for _ in chunk)
                query = f"SELECT hash_origem, texto_traduzido FROM traducoes WHERE hash_origem IN ({placeholders})"
                cursor = conn.execute(query, chunk)
                for h_origem, trad in cursor.fetchall():
                    if h_origem in hash_para_texto:
                        resultados[hash_para_texto[h_origem]] = trad

        return resultados

    def buscar_lote(self, textos: Sequence[str], src_lang: str = "auto", dest_lang: str = "pt") -> dict[str, str]:
        """Fachada de busca em lote."""
        return self.get_many(textos, src_lang, dest_lang)

    def put_many(self, itens: Sequence[tuple[str, str, str, str]]) -> None:
        """Salva múltiplas traduções em lote usando executemany sob RLock em uma única transação.

        Cada item deve ser uma tupla: (texto, src_lang, dest_lang, texto_traduzido).
        """
        if not itens:
            return

        dados = []
        for texto, src_lang, dest_lang, texto_traduzido in itens:
            if texto_traduzido is not None:
                h = self._gerar_hash(texto, src_lang, dest_lang)
                dados.append((h, src_lang, dest_lang, texto_traduzido))

        if not dados:
            return

        with self._lock, closing(self._get_connection()) as conn, conn:
            conn.executemany('''
                INSERT OR REPLACE INTO traducoes 
                (hash_origem, src_lang, dest_lang, texto_traduzido) 
                VALUES (?, ?, ?, ?)
            ''', dados)

    def salvar_lote(
        self,
        itens: Mapping[str, str] | Sequence[tuple[str, str, str, str]],
        src_lang: str = "auto",
        dest_lang: str = "pt",
    ) -> None:
        """Fachada para gravação em lote. Aceita dict {texto: traducao} ou lista de tuplas."""
        if isinstance(itens, Mapping):
            tuplas = [(txt, src_lang, dest_lang, trad) for txt, trad in itens.items()]
        else:
            tuplas = list(itens)
        self.put_many(tuplas)

    def contar_traducoes(self) -> int:
        """Retorna o número total de traduções armazenadas no cache."""
        with closing(self._get_connection()) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM traducoes")
            row = cursor.fetchone()
            return row[0] if row else 0

    def obter_tamanho_bytes(self) -> int:
        """Retorna o tamanho do arquivo SQLite do cache em bytes."""
        if os.path.exists(self.db_path):
            return os.path.getsize(self.db_path)
        return 0

    def limpar_tudo(self):
        """Remove todos os registros do cache, executa checkpoint do WAL e VACUUM para otimizar espaço."""
        with self._lock, closing(self._get_connection()) as conn:
            conn.execute("DELETE FROM traducoes;")
            conn.commit()
            try:
                conn.execute("PRAGMA wal_checkpoint(TRUNCATE);")
            except Exception:
                pass
            conn.isolation_level = None
            conn.execute("VACUUM;")
            try:
                conn.execute("PRAGMA wal_checkpoint(TRUNCATE);")
            except Exception:
                pass


# Alias para o padrão de repositório
RepositorioCacheSqlite = CacheTraducoes



