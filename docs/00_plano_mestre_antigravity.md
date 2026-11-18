# Plano Mestre de Execucao Direta para Agente (Antigravity)

Este documento coordena a execucao em 4 etapas das melhorias de integridade, resiliencia e performance do repositorio **TradutorLegendas26**.

## Regras Estritas para o Agente Executor (Antigravity)

1. **Economia de Tokens (Zero Exploracao):** Nao realize buscas globais nem releia arquivos fora do escopo listado em cada etapa. Todos os blocos `SEARCH` e `REPLACE` ja correspondem exatamente ao codigo-fonte da versao v2.9.2.
2. **TDD / Regression-First:** Antes de aplicar qualquer bloco `REPLACE` no codigo produtivo, adicione e execute os testes de regressao especificados na respectiva etapa.
3. **Soberania da Suite Existente:** Nenhum dos 337 testes unitarios existentes pode quebrar. Ao final de cada etapa, execute obrigatoriamente:
   ```powershell
   .\venv\Scripts\pytest tests\unit -v
   ```
4. **Convencao de Estilo:** Manter codigo, docstrings e comentarios em portugues do Brasil e documentacao Markdown sem emojis.

---

## Ordem de Execucao das Etapas

### Etapa 1 (P0) - Integridade de Dados, Corrupcao e Falsos Sucessos
- **Arquivo de Instrucoes:** `docs/01_etapa1_p0_integridade_e_corrupcao.md`
- **Arquivos Modificados:**
  - `tradutor/servico_traducao.py` (escrita atomica via arquivo temporario com extensao preservada e fatiamento de lotes com teto duplo de linhas e caracteres)
  - `tradutor/estrategias/processador_base.py` (protecao contra exclusao de legenda preexistente ao cancelar ou falhar)
  - `tradutor/glossario.py` (correcao de espacos antes de ponto final e ao redor de tags HTML/SRT na restauracao do escudo)
  - `tradutor/particionador_texto.py` (preservacao da pontuacao de fim de frase dentro do bloco enviado ao tradutor)

### Etapa 2 (P1) - Resiliencia de Rede, Concorrencia e Fallback
- **Arquivo de Instrucoes:** `docs/02_etapa2_p1_resiliencia_e_concorrencia.md`
- **Arquivos Modificados:**
  - `tradutor/tradutores/google.py` (protecao contra Thundering Herd no estado Half-Open com sonda unica sob lock e jitter no backoff)
  - `tradutor/servico_traducao.py` (isolamento do fallback para sub-lotes pendentes do cache Nivel 2, preservacao de linhas ja recuperadas do cache parcial em caso de erro e eliminacao de `asyncio.sleep` em cache hits no fallback)
  - `tradutor/servico_textos_extensos.py` (fallback recursivo descendo na hierarquia de delimitadores)

### Etapa 3 (P2) - Performance de CPU, SQLite e Eficiencia de Cache
- **Arquivo de Instrucoes:** `docs/03_etapa3_p2_performance_cpu_sqlite_cache.md`
- **Arquivos Modificados:**
  - `tradutor/glossario.py` (pre-compilacao de expressao regular unica para termos do glossario com invalidacao automatica por snapshot e regex estatica unica em `remove_shield`)
  - `tradutor/cache.py` (reutilizacao de conexao SQLite por thread via `threading.local()` com invalidacao segura no `limpar_tudo`)
  - `tradutor/servico_textos_extensos.py` (eliminacao de consulta SQLite duplicada em cache miss apos `get_many` e persistencia em lote via `put_many`)

### Etapa 4 (P3) - Contratos, Cancelamento e Higiene de Arquitetura
- **Arquivo de Instrucoes:** `docs/04_etapa4_p3_contratos_cancelamento_higiene.md`
- **Arquivos Modificados:**
  - `tradutor/contratos.py` (carregamento tardio via `__getattr__` para `ManipuladorMidiaPort` e `TrilhaMidia`, desacoplando o nucleo textual do modulo de midia em tempo de importacao)
  - `tradutor/particionador_texto.py` e `tradutor/servico_textos_extensos.py` (exposicao da propriedade publica `delimitadores` e permissao de cache para blocos legitimamente identicos ao original)
  - `tradutor/orquestrador.py` e `tradutor/estrategias/processador_base.py` (compartilhamento da instancia de `CacheTraducoes` entre arquivos da fila e metodo gancho `deve_copiar_sem_traduzir`)