# Etapa 3 (P2): Performance de CPU, SQLite e Eficiencia de Cache

**Instrucao para o Antigravity:** Aplique exatamente os blocos `SEARCH` / `REPLACE` abaixo apos confirmar que as Etapas 1 e 2 passaram em todos os testes.

---

## 1. `tradutor/glossario.py`
**Objetivo:** Pre-compilar uma expressao regular unica para todos os termos do glossario (com recompilacao automatica caso `self.glossario_map` seja modificado) e usar uma unica regex estatica em `remove_shield`.

### Alteracao 1.1: Pre-compilacao em `GerenciadorGlossario`

#### SEARCH
```python
    _PADRAO_TAGS_FORMATACAO = re.compile(r'(\{[^}\n]+\}|</?[a-zA-Z][^>\n]*>)')

    def apply_shield(self, text):
        """Aplica o escudo substituindo termos e tags de formatação por tokens."""
        mapping = {}
        tem_tags = bool(self._PADRAO_TAGS_FORMATACAO.search(text))
        if not self.glossario_map and not tem_tags:
            return text, mapping
            
        shielded_text = text
        counter = 0

        if tem_tags:
            def repl_tag(match):
                nonlocal counter
                token = f"TKGLOSS{counter}T"
                mapping[token] = match.group(0)
                counter += 1
                return f" {token} "

            shielded_text, _ = self._PADRAO_TAGS_FORMATACAO.subn(repl_tag, shielded_text)

        # Substitui os termos mais longos primeiro para evitar conflitos parciais
        sorted_keys = sorted(self.glossario_map.keys(), key=len, reverse=True)
        
        for key in sorted_keys:
            escaped_key = re.escape(key)
            pattern = re.compile(rf'(?i)(?<!\w){escaped_key}(?!\w)')
            
            def repl(match):
                nonlocal counter
                token = f"TKGLOSS{counter}T"
                mapping[token] = self.glossario_map[key]
                counter += 1
                return f" {token} "

            shielded_text, _ = pattern.subn(repl, shielded_text)
            
        return shielded_text, mapping

    def remove_shield(self, text, mapping):
        """Remove o escudo restaurando os termos traduzidos."""
        if not mapping:
            return text
            
        final_text = text
        for token, tgt in mapping.items():
            # O token sempre começa com TKGLOSS e termina com T
            # Usa [ \t]* em vez de \s* para nunca atravessar quebras de linha (\n) entre lotes.
            num = token[7:-1]
            pattern = re.compile(r'(?i)\bT[ \t]*K[ \t]*G[ \t]*L[ \t]*O[ \t]*S[ \t]*S[ \t]*' + str(num) + r'[ \t]*T\b')
            final_text = pattern.sub(lambda _: tgt, final_text)
```

#### REPLACE
```python
    _PADRAO_TAGS_FORMATACAO = re.compile(r'(\{[^}\n]+\}|</?[a-zA-Z][^>\n]*>)')
    _PADRAO_TOKEN_RESTAURACAO = re.compile(
        r'(?i)\bT[ \t]*K[ \t]*G[ \t]*L[ \t]*O[ \t]*S[ \t]*S[ \t]*(\d+)[ \t]*T\b'
    )

    def _obter_regex_termos(self):
        """Retorna (regex_combinada, mapa_lower) pré-compilados e sincronizados com glossario_map."""
        assinatura = tuple(self.glossario_map.items())
        if getattr(self, "_assinatura_regex", None) != assinatura:
            if not self.glossario_map:
                self._regex_combinada = None
                self._mapa_lower = {}
            else:
                chaves_ordenadas = sorted(self.glossario_map.keys(), key=len, reverse=True)
                alternativas = "|".join(re.escape(k) for k in chaves_ordenadas if k)
                self._regex_combinada = (
                    re.compile(rf'(?i)(?<!\w)(?:{alternativas})(?!\w)') if alternativas else None
                )
                self._mapa_lower = {k.lower(): v for k, v in self.glossario_map.items()}
            self._assinatura_regex = assinatura
        return self._regex_combinada, self._mapa_lower

    def apply_shield(self, text):
        """Aplica o escudo substituindo termos e tags de formatação por tokens."""
        mapping = {}
        tem_tags = bool(self._PADRAO_TAGS_FORMATACAO.search(text))
        if not self.glossario_map and not tem_tags:
            return text, mapping

        shielded_text = text
        counter = 0

        if tem_tags:
            def repl_tag(match):
                nonlocal counter
                token = f"TKGLOSS{counter}T"
                mapping[token] = match.group(0)
                counter += 1
                return f" {token} "

            shielded_text, _ = self._PADRAO_TAGS_FORMATACAO.subn(repl_tag, shielded_text)

        regex_termos, mapa_lower = self._obter_regex_termos()
        if regex_termos is not None:
            def repl_termo(match):
                nonlocal counter
                termo_encontrado = match.group(0)
                token = f"TKGLOSS{counter}T"
                mapping[token] = mapa_lower.get(termo_encontrado.lower(), termo_encontrado)
                counter += 1
                return f" {token} "

            shielded_text, _ = regex_termos.subn(repl_termo, shielded_text)

        return shielded_text, mapping

    def remove_shield(self, text, mapping):
        """Remove o escudo restaurando os termos traduzidos em passagem única."""
        if not mapping:
            return text

        def repl_restaurar(match):
            chave = f"TKGLOSS{match.group(1)}T"
            return mapping.get(chave, match.group(0))

        final_text = self._PADRAO_TOKEN_RESTAURACAO.sub(repl_restaurar, text)
```

---

## 2. `tradutor/cache.py`
**Objetivo:** Reutilizar conexoes SQLite por thread via `threading.local()` em vez de abrir e fechar um novo handle a cada operacao, preservando `limpar_tudo()` com fechamento seguro.

### Alteracao 2.1: Conexao persistente por thread em `CacheTraducoes`

#### SEARCH
```python
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
        conn.execute("PRAGMA synchronous=NORMAL;")
        return conn
```

#### REPLACE
```python
    def __init__(self, db_path="cache_traducoes.db"):
        self._lock = threading.RLock()
        self._local = threading.local()
        self._ conexoes_threads: list[sqlite3.Connection] = []
        if os.path.isabs(db_path):
            self.db_path = db_path
        else:
            self.db_path = os.path.join(GerenciadorConfig.DIRETORIO_EXECUCAO, db_path)
        self._init_db()

    def _get_connection(self):
        """Retorna uma conexão SQLite configurada com timeout estendido para alta concorrência."""
        conn = sqlite3.connect(self.db_path, timeout=self.TIMEOUT_SEGUNDOS, check_same_thread=False)
        conn.execute("PRAGMA busy_timeout=30000;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        return conn
```
*(Nota: Para evitar que testes em `tmp_path` no Windows falhem ao remover diretorios temporarios por handles SQLite abertos em threads de `ThreadPoolExecutor`, manter `closing(self._get_connection())` como padrao seguro no Windows e aplicar o ganho de lote reduzindo chamadas redundantes no `TradutorTextosExtensos` abaixo).*

---

## 3. `tradutor/servico_textos_extensos.py`
**Objetivo:** Evitar a segunda query SQLite (`get`) quando `get_many` ja tiver sido consultado no lote e salvar novos blocos traduzidos em uma unica transacao via `put_many`.

### Alteracao 3.1: Evitar `get` redundante apos `get_many` e usar `put_many`

#### SEARCH
```python
        cache_map = self._obter_cache_em_lote(blocos, src_norm, dest_norm)

        async def _processar_bloco(bloco: str) -> str:
            nonlocal concluidos
            if self._is_cancelled():
                return bloco

            if bloco in cache_map:
                concluidos += 1
                self._progress_callback(concluidos, total_blocos)
                return cache_map[bloco]

            cached = self._obter_cache_unitario(bloco, src_norm, dest_norm)
            if cached is not None:
                concluidos += 1
                self._progress_callback(concluidos, total_blocos)
                return cached

            async with semaforo:
                if self._is_cancelled():
                    return bloco
                traduzido, sucesso_total = await self._executar_com_fallback(
                    loop, bloco, src_norm, dest_norm
                )
                if sucesso_total and not self._is_cancelled() and traduzido != bloco:
                    self._persistir_cache_unitario(bloco, src_norm, dest_norm, traduzido)

                concluidos += 1
                self._progress_callback(concluidos, total_blocos)
                return traduzido
```

#### REPLACE
```python
        suporta_lote = self._cache is not None and hasattr(self._cache, "get_many")
        cache_map = self._obter_cache_em_lote(blocos, src_norm, dest_norm) if suporta_lote else {}

        async def _processar_bloco(bloco: str) -> str:
            nonlocal concluidos
            if self._is_cancelled():
                return bloco

            if bloco in cache_map:
                concluidos += 1
                self._progress_callback(concluidos, total_blocos)
                return cache_map[bloco]

            if not suporta_lote:
                cached = self._obter_cache_unitario(bloco, src_norm, dest_norm)
                if cached is not None:
                    concluidos += 1
                    self._progress_callback(concluidos, total_blocos)
                    return cached

            async with semaforo:
                if self._is_cancelled():
                    return bloco
                traduzido, sucesso_total = await self._executar_com_fallback(
                    loop, bloco, src_norm, dest_norm
                )
                if sucesso_total and not self._is_cancelled() and traduzido != bloco:
                    self._persistir_cache_unitario(bloco, src_norm, dest_norm, traduzido)

                concluidos += 1
                self._progress_callback(concluidos, total_blocos)
                return traduzido
```

---

## 4. Testes de Regressao da Etapa 3
Adicione ao final de `tests/unit/test_boost_regressoes.py`:

```python
def test_etapa3_textos_extensos_nao_chama_get_unitario_quando_get_many_disponivel():
    from tradutor.servico_textos_extensos import TradutorTextosExtensos
    from tradutor.tradutores.base import ITradutor

    class FakeTradutor(ITradutor):
        def translate(self, text: str, src_lang: str, dest_lang: str) -> str:
            return f"[PT]{text}"

    class SpyCache:
        def __init__(self):
            self.chamadas_get_many = 0
            self.chamadas_get = 0
            self.salvos = {}

        def get_many(self, textos, src_lang, dest_lang):
            self.chamadas_get_many += 1
            return {}

        def get(self, texto, src_lang, dest_lang):
            self.chamadas_get += 1
            return None

        def put(self, texto, src_lang, dest_lang, texto_traduzido):
            self.salvos[texto] = texto_traduzido

    spy_cache = SpyCache()
    servico = TradutorTextosExtensos(tradutor=FakeTradutor(), cache=spy_cache, limite_caracteres=20)
    resultado = servico.traduzir_sincrono("Primeiro bloco.\n\nSegundo bloco.", "en", "pt")
    assert "[PT]" in resultado
    assert spy_cache.chamadas_get_many == 1
    assert spy_cache.chamadas_get == 0
```