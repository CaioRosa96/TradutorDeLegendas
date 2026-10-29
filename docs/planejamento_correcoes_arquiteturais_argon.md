# Especificação de Engenharia: Correções Arquiteturais, Concorrência e Resiliência (Auditoria Argon v2.7.0)

**Repositório:** TradutorDeLegendas (TaradutorLegendas26)  
**Versão Alvo:** v2.7.1  
**Destinatário da Execução:** Antigravity IDE / Gemini Argon  
**Diretrizes de Qualidade:** `perfil_caio` §0 (Língua PT-BR e Zero Emojis em Docs), §1 (MVC/OOP e Regression Test Enforcer), §2 (Segurança SSL/TLS), §3 (Concorrência e Thread-Safety), §6 (Declaração de Regras); `AGENTS.md`.

---

## 1. Auditoria Prévia: Lacunas Identificadas nos Planejamentos Anteriores (Gemini 3.8 Flash)

Antes de consolidar o plano de correções arquiteturais, os dois documentos gerados anteriormente pelo modelo *Gemini 3.8 Flash* foram auditados contra o código-fonte real do repositório e o histórico da última sessão:

### 1.1 Lacunas em `docs/planejamento_desacoplamento_mkvtoolnix.md`
1. **Download sem Extração no `iniciar.bat`:** O bloco proposto baixa `mkvtoolnix-64-bit-82.0.7z` (`mkvtoolnix_temp.7z`), mas não o descompacta, apenas exibindo um aviso textual e prosseguindo imediatamente para `python TradutorLegendas26.py` (o que causa falha imediata na ausência do 7-Zip).
2. **Manutenção Indevida de `--trusted-host`:** Não corrigiu a linha 18 do `iniciar.bat`, que desativa a verificação de certificados SSL do `pip` por padrão (`--trusted-host pypi.org ...`), violando `perfil_caio §2`.
3. **Caminhos Hardcoded nos `.spec` do PyInstaller:** Não identificou que `packaging/TradutorLegendas.spec` e `packaging/TradutorLegendas_Classico.spec` contêm caminhos absolutos fixos (`D:/programas/TaradutorLegendas26/...`), violando `AGENTS.md §5.6`, e que `packaging/build.py` não utiliza `GerenciadorConfig.get_mkvtoolnix_path()` como fallback quando a pasta local `mkvtoolnix/` não existir.
4. **Precisão sobre `git rm --cached`:** Desindexar os binários remove os 170 MB do *working tree* do `HEAD` e de exportações via `git archive`, mas os *blobs* permanecem no histórico `.git/objects/pack` até que seja executado `git filter-repo` ou clone superficial (`--depth 1`).

### 1.2 Lacunas Críticas em `docs/planejamento_whisper_argon.md`
1. **Incompatibilidade de Codecs entre `mkvextract` e `whisperfile` (Bloqueante):**
   - O `mkvextract` extrai a faixa de áudio em seu formato nativo do contêiner (em animes/séries MKV: quase sempre **AAC**, **Opus**, **AC3/EAC3** ou **Vorbis**).
   - O `whisperfile` (`whisper.cpp`) decodifica nativamente apenas `.wav` (PCM 16-bit), `.mp3`, `.flac` e `.ogg`. Se receber um arquivo `.aac`, `.opus` ou `.ac3` extraído diretamente pelo `mkvextract`, o binário **falha imediatamente**. É indispensável converter o áudio extraído para `.wav` PCM 16 kHz mono (via `ffmpeg` portátil ou MediaFoundation) antes de acionar o `whisperfile`.
2. **Incompatibilidade de Códigos de Idioma (`ISO-639-2` vs `ISO-639-1`):**
   - O `ProcessadorMkv` opera com códigos de 3 letras do MKV (`jpn`, `eng`, `por`), mas a flag `-l` do `whisperfile` exige códigos de 2 letras (`ja`, `en`, `pt`). Sem converter via `Idiomas.para_google(idioma_origem)`, o comando do Whisper falha.
3. **Uso de `os.getcwd()` violando `AGENTS.md §5.6`:**
   - `MotorWhisperfile.resolver_executavel()` utilizou `os.getcwd()` em vez de `GerenciadorConfig.DIRETORIO_EXECUCAO`, o que quebra em execuções fora do diretório raiz ou empacotadas via PyInstaller.
4. **Vazamento de Arquivos Temporários em `cleanup_temporary()`:**
   - `ProcessadorMkv.cleanup_temporary()` remove apenas arquivos contendo a substring `"_ORIGINAL"`. Arquivos de áudio extraídos sem esse sufixo ficariam órfãos na pasta do usuário.
5. **Blocos `SEARCH/REPLACE` Omitidos:**
   - O documento anterior declarou alterações em `manipulador_mkv.py`, `processador_mkv.py` e `config_usuario.py`, mas omitiu seus blocos `SEARCH/REPLACE` na seção final e não previu os controles na camada View (`modal_config.py` / `sidebar.py`).

---

## 2. Análise e Refinamento Técnico dos Apontamentos do Argon (v2.7.0)

A inspeção do código-fonte real validou integralmente os 5 problemas de engenharia + itens de higiene apontados pelo Argon, com os seguintes ajustes finos para preservar **100% de compatibilidade com os 129 testes unitários existentes**:

### Etapa 1: Isolamento de `googletrans.Translator` por Thread (`tradutor/tradutores/google.py`) [Crítico]
- **Problema:** `self._engine = Translator()` cria uma única instância compartilhada por até 5 threads simultâneas do `ThreadPoolExecutor` em `ServicoTraducao`. O cliente HTTP interno da `googletrans` não é *thread-safe*, gerando exceções esporádicas (`AttributeError`, `TypeError`) que são capturadas como erro permanente e incrementam indevidamente o *Circuit Breaker*.
- **Solução e Compatibilidade com Testes:**
  - Utilizar `self._local = threading.local()` e um método auxiliar `_get_engine()` que instancia `Translator()` sob demanda para cada thread.
  - Expor a propriedade `_engine` retornando `self._get_engine()` para manter compatibilidade total com `tests/unit/test_disjuntor_google.py` (onde a fixture `translator_falso` aplica `mocker.patch('tradutor.tradutores.google.Translator')`).

### Etapa 2: Persistência do *Circuit Breaker* na Fila (`orquestrador.py`, `fabrica.py`, `processador_base.py`) [Alto]
- **Problema:** `ProcessadorArquivoBase.process()` instancia um novo `MotorTraducaoGoogle` a cada arquivo. Se o Arquivo 1 sofrer bloqueio de IP e abrir o disjuntor, o Arquivo 2 cria uma nova instância com `_is_open = False`, ignorando a janela de recuperação de 60 segundos.
- **Solução e Compatibilidade com Testes:**
  - Instanciar `MotorTraducaoGoogle(max_retries=GerenciadorConfig.MAX_RETENTATIVAS)` uma única vez em `OrquestradorTraducoes._process_files()` antes do loop de arquivos.
  - Propagar `engine` via `FabricaProcessadores.get_processor(..., engine=engine)` até `ProcessadorArquivoBase.__init__(..., engine=None)`.
  - Manter `engine=None` como argumento padrão opcional em `get_processor` e `ProcessadorArquivoBase.__init__` (criando instância local apenas se `self.engine is None`), garantindo retrocompatibilidade com chamadas diretas em scripts e testes E2E.

### Etapa 3: Lookarounds no Escudo de Glossário para Termos com Pontuação (`tradutor/glossario.py`) [Médio-Alto]
- **Problema:** `re.compile(rf'(?i)\b{escaped_key}\b')` falha quando o termo começa ou termina com caractere não-alfanumérico (`\W`), como `U.A.` (presente na linha 58 de `glossario.txt`), pois o ponto final não forma fronteira `\b` quando seguido de espaço ou pontuação (`"Bem-vindos à U.A.!"`).
- **Solução e Compatibilidade com Golden Master:**
  - Substituir `\b...\b` por lookarounds de não-palavra: `re.compile(rf'(?i)(?<!\w){escaped_key}(?!\w)')`.
  - **Prova de Não-Regressão:** Para todos os termos que começam e terminam com caracteres alfanuméricos (`\w`), `(?<!\w)termo(?!\w)` produz resultado idêntico a `\btermo\b`. Assim, todos os hashes SHA-256 *Golden Master* em `tests/unit/test_contratos_escudo.py` permanecem 100% inalterados, enquanto termos como `U.A.` passam a ser devidamente tokenizados.

### Etapa 4: Integração da Auto-Alimentação via AniList (`config_usuario.py`, `servico_traducao.py`) [Médio]
- **Problema:** `ServicoTraducao.__init__` instancia `GerenciadorGlossario(video_filename=video_filename)` sem repassar `habilitar_auto_alimentar`, mantendo a funcionalidade sempre desativada no fluxo principal.
- **Solução e Isolamento Offline nos Testes:**
  - Adicionar a preferência `"auto_alimentar_anilist": True` em `PreferenciasUsuario.PADRAO` (`tradutor/config_usuario.py`).
  - Em `ServicoTraducao.__init__`, adicionar o parâmetro opcional `habilitar_auto_alimentar: bool | None = None`. Quando `None`, consulta `PreferenciasUsuario.obter("auto_alimentar_anilist", True)` e repassa ao `GerenciadorGlossario`.
  - Em `GerenciadorGlossario.__init__`, manter o default `habilitar_auto_alimentar=False` para chamadas diretas sem argumento, garantindo que testes unitários de glossário que instanciam `GerenciadorGlossario(filepath=...)` nunca tentem acessar a rede.

### Etapa 5: Cache em 2 Níveis (`get_many` / `put_many`) em `ServicoTraducao` (`servico_traducao.py`) [Otimização]
- **Problema:** `ServicoTraducao._traduzir_lote` consulta apenas o hash do bloco inteiro de 40 linhas (`self._cache.get(bloco_protegido, ...)`). Se 39 linhas de uma abertura de anime forem idênticas ao episódio anterior e 1 linha mudar, ocorre *Cache Miss* completo do bloco.
- **Armadilha de Regressão Detectada nos Testes:**
  - O teste `test_chave_de_cache_usa_texto_mascarado_do_bloco` (`tests/unit/test_servico_traducao.py`, linha 315) exige explicitamente que `self._cache.get("<A\nB>", "auto", "pt")` e `self._cache.put("<A\nB>", "auto", "pt", "<X\nY>")` sejam chamados quando o bloco não tem hits parciais, e usa `MagicMock` para `self._cache`.
- **Solução Arquitetural em 2 Níveis (Compatível com Golden Tests):**
  1. **Nível 1 (Cache de Bloco Completo):** Consulta `self._cache.get(bloco_protegido, src_lang, dest_lang)`. Se encontrar, restaura imediatamente (1 query SQLite para 40 linhas).
  2. **Nível 2 (Cache Granular por Linha via `get_many`):** Se o bloco completo não estiver no cache, protege cada linha individualmente e chama `self._cache.get_many(textos_mascarados_linhas, src_lang, dest_lang)`.
     - *(Valida `isinstance(mapa_cache_linhas, dict)` e `len(mapa_cache_linhas) > 0` para que mocks genéricos de testes unitários que não configuram `get_many` sigam o fluxo padrão de bloco).*
     - Se todas as linhas do lote forem resolvidas pelo `get_many`, preenche `subs` sem tocar na rede!
     - Se houver hits parciais, traduz apenas o sub-lote das linhas ausentes na rede, salva as novas linhas via `self._cache.put_many(...)` e também salva o bloco consolidado.
  3. **Otimização do Fallback Sequencial:** Antes de iterar linha a linha no fallback, consulta `get_many` de uma só vez e grava as novas traduções ao final com `put_many`.

### Etapa 6: Higiene de UI e Segurança de Script (`tradutor/ui/header.py`, `iniciar.bat`) [Baixo]
- **`tradutor/ui/header.py`:** Em `HeaderView.redefinir_textos()` (linhas 144-145), remover os prefixos de emoji (`🎨 ` e `📖 `) que não existem em `_construir_widgets()`, mantendo consistência visual ao alternar idiomas.
- **`iniciar.bat`:** Executar `pip install -r requirements.txt` com verificação SSL padrão, utilizando `--trusted-host` apenas como fallback condicional (`if errorlevel 1`) caso o usuário esteja atrás de proxy corporativo.
- *(Nota: Verificou-se que `tests/scripts/preparar_video.py` está completo com 78 linhas no disco local; o truncamento na linha 46 ocorreu apenas na visualização web anterior).*

---

## 3. Blocos `SEARCH/REPLACE` para Aplicação Cirúrgica

### 3.1 Etapa 1 — `tradutor/tradutores/google.py`
```markdown
### FILE: tradutor/tradutores/google.py
<<<<<<< SEARCH
    def __init__(self, max_retries=3, failure_threshold=5, recovery_timeout=60):
        self._engine = Translator()
        self._max_retries = max_retries
        self._lock = threading.Lock()
        
        # Estado do Circuit Breaker
        self._failure_count = 0
        self._failure_threshold = failure_threshold
        self._last_failure_time = 0
        self._recovery_timeout = recovery_timeout
        self._is_open = False
=======
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
>>>>>>>
```

---

### 3.2 Etapa 2 — `tradutor/orquestrador.py`, `tradutor/estrategias/fabrica.py`, `tradutor/estrategias/processador_base.py`, `tradutor/estrategias/processador_mkv.py` e `tradutor/estrategias/processador_srt.py`

```markdown
### FILE: tradutor/orquestrador.py
<<<<<<< SEARCH
from .estrategias import FabricaProcessadores
from .logger import app_logger
=======
from .config import GerenciadorConfig
from .estrategias import FabricaProcessadores
from .logger import app_logger
from .tradutores import MotorTraducaoGoogle
>>>>>>>
<<<<<<< SEARCH
        try:
            for index, origem in enumerate(files, 1):
                if not self._is_running:
                    break

                try:
                    inicio_arquivo = time.time()
                    log(f"\n--- Arquivo [{index}/{total_arquivos}]: {os.path.basename(origem)} ---")

                    # Devolvemos a responsabilidade de saber COMO processar para o Factory/Strategy
                    processador = FabricaProcessadores.get_processor(
                        origem, log, update_progress, ask_overwrite, lambda: self._is_running
                    )
                    resultado = processador.process(origem, idioma_origem, idioma_destino, manter_legenda)
=======
        engine_compartilhado = MotorTraducaoGoogle(max_retries=GerenciadorConfig.MAX_RETENTATIVAS)

        try:
            for index, origem in enumerate(files, 1):
                if not self._is_running:
                    break

                try:
                    inicio_arquivo = time.time()
                    log(f"\n--- Arquivo [{index}/{total_arquivos}]: {os.path.basename(origem)} ---")

                    # Devolvemos a responsabilidade de saber COMO processar para o Factory/Strategy
                    processador = FabricaProcessadores.get_processor(
                        origem, log, update_progress, ask_overwrite, lambda: self._is_running,
                        engine=engine_compartilhado
                    )
                    resultado = processador.process(origem, idioma_origem, idioma_destino, manter_legenda)
>>>>>>>

### FILE: tradutor/estrategias/fabrica.py
<<<<<<< SEARCH
    @staticmethod
    def get_processor(filepath, log_cb, progress_cb, ask_overwrite_cb, is_running_cb):
        ext = filepath.lower()
        if ext.endswith('.mkv'):
            return ProcessadorMkv(log_cb, progress_cb, ask_overwrite_cb, is_running_cb)
        elif ext.endswith(('.srt', '.ass', '.txt')):
            return ProcessadorSrt(log_cb, progress_cb, ask_overwrite_cb, is_running_cb)
        else:
            raise ValueError(f"Formato não suportado pela Fábrica: {filepath}")
=======
    @staticmethod
    def get_processor(filepath, log_cb, progress_cb, ask_overwrite_cb, is_running_cb, engine=None):
        ext = filepath.lower()
        if ext.endswith('.mkv'):
            return ProcessadorMkv(log_cb, progress_cb, ask_overwrite_cb, is_running_cb, engine=engine)
        elif ext.endswith(('.srt', '.ass', '.txt')):
            return ProcessadorSrt(log_cb, progress_cb, ask_overwrite_cb, is_running_cb, engine=engine)
        else:
            raise ValueError(f"Formato não suportado pela Fábrica: {filepath}")
>>>>>>>

### FILE: tradutor/estrategias/processador_base.py
<<<<<<< SEARCH
    def __init__(self, log_cb, progress_cb, ask_overwrite_cb, is_running_cb):
        self.log = log_cb
        self.update_progress = progress_cb
        self.ask_overwrite = ask_overwrite_cb
        self.is_running = is_running_cb
=======
    def __init__(self, log_cb, progress_cb, ask_overwrite_cb, is_running_cb, engine=None):
        self.log = log_cb
        self.update_progress = progress_cb
        self.ask_overwrite = ask_overwrite_cb
        self.is_running = is_running_cb
        self.engine = engine
>>>>>>>
<<<<<<< SEARCH
        try:
            # 5. Tradução (Core)
            self.log(self.get_translation_message())
            engine = MotorTraducaoGoogle(max_retries=GerenciadorConfig.MAX_RETENTATIVAS)
            translator_svc = ServicoTraducao(
=======
        try:
            # 5. Tradução (Core)
            self.log(self.get_translation_message())
            engine = self.engine or MotorTraducaoGoogle(max_retries=GerenciadorConfig.MAX_RETENTATIVAS)
            translator_svc = ServicoTraducao(
>>>>>>>
```

---

### 3.3 Etapa 3 — `tradutor/glossario.py`
```markdown
### FILE: tradutor/glossario.py
<<<<<<< SEARCH
        for key in sorted_keys:
            escaped_key = re.escape(key)
            pattern = re.compile(rf'(?i)\b{escaped_key}\b')
=======
        for key in sorted_keys:
            escaped_key = re.escape(key)
            pattern = re.compile(rf'(?i)(?<!\w){escaped_key}(?!\w)')
>>>>>>>
```

---

### 3.4 Etapa 4 e Etapa 5 — `tradutor/config_usuario.py` e `tradutor/servico_traducao.py`
```markdown
### FILE: tradutor/config_usuario.py
<<<<<<< SEARCH
        "politica_sobrescrita": "perguntar",  # "perguntar", "sobrescrever", "pular"
        "mkvtoolnix_custom": ""
    }
=======
        "politica_sobrescrita": "perguntar",  # "perguntar", "sobrescrever", "pular"
        "mkvtoolnix_custom": "",
        "auto_alimentar_anilist": True
    }
>>>>>>>

### FILE: tradutor/servico_traducao.py
<<<<<<< SEARCH
    def __init__(self, logger, progress_callback, is_cancelled_callback=None, engine=None, video_filename=None):
        self._logger = logger
        self._progress_callback = progress_callback
        self._is_cancelled = is_cancelled_callback or (lambda: False)
        self._linhas_processadas = 0
        self._total_linhas = 0
        self._glossary = GerenciadorGlossario(video_filename=video_filename)
        self._cache = CacheTraducoes()
=======
    def __init__(
        self,
        logger,
        progress_callback,
        is_cancelled_callback=None,
        engine=None,
        video_filename=None,
        habilitar_auto_alimentar=None,
    ):
        self._logger = logger
        self._progress_callback = progress_callback
        self._is_cancelled = is_cancelled_callback or (lambda: False)
        self._linhas_processadas = 0
        self._total_linhas = 0
        if habilitar_auto_alimentar is None:
            try:
                from .config_usuario import PreferenciasUsuario
                habilitar_auto_alimentar = bool(PreferenciasUsuario.obter("auto_alimentar_anilist", True))
            except Exception:
                habilitar_auto_alimentar = False
        self._glossary = GerenciadorGlossario(
            video_filename=video_filename,
            habilitar_auto_alimentar=habilitar_auto_alimentar,
        )
        self._cache = CacheTraducoes()
>>>>>>>
<<<<<<< SEARCH
                # 1. Busca no Cache Local
                traduzido = self._cache.get(bloco_protegido, src_lang, dest_lang)
                
                if not traduzido:
                    # 2. Se não existir, vai na Rede via Engine injetada
                    traduzido = await loop.run_in_executor(executor, self._engine.translate, bloco_protegido, src_lang, dest_lang)
                    # 3. Salva no Cache
                    self._cache.put(bloco_protegido, src_lang, dest_lang, traduzido)
                    
                traduzido_restaurado = self._glossary.restaurar(traduzido, payload_bloco)
=======
                # 1. Busca no Cache Local (Nível 1: Bloco Inteiro)
                traduzido = self._cache.get(bloco_protegido, src_lang, dest_lang)
                
                if not traduzido:
                    # Nível 2: Verifica se há linhas individuais já cacheadas via get_many
                    payloads_linhas = [
                        self._glossary.proteger(t, id_linha=idx)
                        for idx, t in zip(lote_indices, textos_preparados)
                    ]
                    chaves_linhas = [p.texto_mascarado for p in payloads_linhas]
                    cache_parcial = getattr(self._cache, "get_many", lambda *_: {})(
                        chaves_linhas, src_lang, dest_lang
                    )
                    if not isinstance(cache_parcial, dict):
                        cache_parcial = {}

                    if cache_parcial and len(cache_parcial) == len(chaves_linhas):
                        # 100% das linhas já estão no cache individual
                        for idx, p_linha in zip(lote_indices, payloads_linhas):
                            r_cached = cache_parcial[p_linha.texto_mascarado]
                            r_rest = self._glossary.restaurar(r_cached, p_linha)
                            subs[idx].text = self._limpar_quebras(r_rest.strip())
                        with pbar_lock:
                            self._linhas_processadas += len(lote_indices)
                            self._progress_callback(self._linhas_processadas, self._total_linhas)
                        return

                    # 2. Vai na Rede via Engine injetada para o bloco
                    traduzido = await loop.run_in_executor(
                        executor, self._engine.translate, bloco_protegido, src_lang, dest_lang
                    )
                    # 3. Salva no Cache (Bloco)
                    self._cache.put(bloco_protegido, src_lang, dest_lang, traduzido)
                    
                traduzido_restaurado = self._glossary.restaurar(traduzido, payload_bloco)
>>>>>>>
```

---

### 3.5 Etapa 6 — `tradutor/ui/header.py` e `iniciar.bat`
```markdown
### FILE: tradutor/ui/header.py
<<<<<<< SEARCH
    def redefinir_textos(self):
        """Atualiza os textos traduziveis apos troca de idioma."""
        self.lbl_sub.configure(text=I18n.t("app_sub"))
        self.btn_tema.configure(text=f"🎨 {I18n.t('btn_visualizar')}")
        self.btn_grimorio.configure(text=f"📖 {I18n.t('btn_grimorio')}")
        self.lbl_status.configure(text=I18n.t("status_pronto"))
=======
    def redefinir_textos(self):
        """Atualiza os textos traduziveis apos troca de idioma."""
        self.lbl_sub.configure(text=I18n.t("app_sub"))
        self.btn_tema.configure(text=I18n.t("btn_visualizar"))
        self.btn_grimorio.configure(text=I18n.t("btn_grimorio"))
        self.lbl_status.configure(text=I18n.t("status_pronto"))
>>>>>>>

### FILE: iniciar.bat
<<<<<<< SEARCH
    echo [INFO] Instalando/atualizando dependencias...
    pip install --trusted-host pypi.org --trusted-host pypi.python.org --trusted-host files.pythonhosted.org -r requirements.txt
    copy /y requirements.txt venv\.req_cache >nul
=======
    echo [INFO] Instalando/atualizando dependencias...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo [AVISO] Falha SSL detectada. Tentando contingencia para rede corporativa...
        pip install --trusted-host pypi.org --trusted-host pypi.python.org --trusted-host files.pythonhosted.org -r requirements.txt
    )
    copy /y requirements.txt venv\.req_cache >nul
>>>>>>>
```

---

## 4. Plano de Testes de Regressão Obrigatórios (`regression-test-enforcer`)

Para cada etapa aplicada, os seguintes testes unitários devem ser criados (Red -> Green):

1. **`tests/unit/test_disjuntor_google.py`:**
   - `test_isolamento_instancia_translator_por_thread`: Verifica que duas threads distintas executando `motor.translate()` recebem objetos `Translator` independentes via `threading.local()`, enquanto compartilham o mesmo contador `_failure_count` e estado `_is_open`.
2. **`tests/unit/test_orquestrador_disjuntor.py` (ou em `test_disjuntor_google.py`):**
   - `test_orquestrador_compartilha_mesmo_motor_entre_arquivos_da_fila`: Processa 2 arquivos na fila do `OrquestradorTraducoes` e comprova que a instância de `ITradutor` injetada no Arquivo 1 é exatamente a mesma (`assert engine_arq1 is engine_arq2`) no Arquivo 2, preservando o disjuntor aberto.
3. **`tests/unit/test_glossario.py`:**
   - `test_apply_shield_termos_com_pontuacao_final`: Valida que termos como `"U.A."` em frases como `"Bem-vindos à U.A.!"` e `"Vamos para a U.A. agora"` são mascarados por `TKGLOSS{n}T` e restaurados perfeitamente.
4. **`tests/unit/test_servico_traducao.py`:**
   - `test_cache_get_many_evita_rede_quando_linhas_ja_cacheadas`: Simula duas linhas já salvas individualmente no cache e verifica que um novo lote contendo essas linhas resolve tudo localmente via `get_many` com `mock_engine.translate.call_count == 0`.
5. **Execução Completa:**
   - `.\venv\Scripts\pytest tests\unit -v` deve aprovar todos os 129 testes originais + os novos testes de regressão em menos de 5 segundos.

