# Auditoria do Historico de Commits, Evolucao do Codigo e Plano de Saneamento

Este documento registra a analise tecnica dos 43 commits do repositorio **TradutorDeLegendas**, mapeando a evolucao arquitetural do sistema, os desvios de versionamento identificados no historico Git, as correcoes sem risco ja aplicadas no ambiente e as acoes pendentes que exigem decisao explicita ou mudanca de fluxo continuo.

---

## 1. Analise de Evolucao do Codigo (Linha do Tempo dos 43 Commits)

O historico Git evidencia seis fases distintas de maturidade de engenharia:

### Fase 1: Prototipo Monolitico Inicial (09/07/2026 — 12 commits em 2 horas)
- **Commits:** `733ba33` a `837ed56`.
- **Caracteristicas:** Desenvolvimento rapido em arquivo unico, focado em validar a extracao de trilhas via MKVToolNix e a chamada basica de traducao.
- **Pontos positivos:** Commits pequenos e incrementais no inicio (`e19a132`, `834cdc9`, `846c32d`).
- **Problemas observados:**
  - Ausencia de padrao Conventional Commits em metade das mensagens (`834cdc9`, `846c32d`, `39cd33d`, `91f49d4`, `22a9258`).
  - Commit corretivo imediato de sintaxe (`39cd33d` — *"resolve erros de sintaxe e restaura funcao de embutir legenda"*), indicando codigo comitado sem execucao previa.
  - Adicao de binarios portateis completos do MKVToolNix diretamento no indice Git (`dc29b2e` — 203 arquivos, +160.182 linhas), inflando permanentemente o banco de objetos `.git/objects/pack`.

### Fase 2: Migracao de Interface Grafica (18/07/2026 — 4 commits)
- **Commits:** `e4df8a5` a `c8206ec`.
- **Caracteristicas:** Substituicao da interface inicial pelo CustomTkinter (`e4df8a5`) e isolamento do ambiente virtual `venv/` no `.gitignore` (`2156d19`).

### Fase 3: Primeiros Ajustes de Concorrencia e Cache (12/09/2026 — 2 commits)
- **Commits:** `0245e1f` e `181c028`.
- **Caracteristicas:** Primeiras protecoes de thread-safety na interface e persistencia local. A partir deste ponto, o nome do autor no Git passou a registrar `Administrador` (nome da conta local do Windows) em vez de `Caio Rosa`.

### Fase 4: Ponto de Inflexao Arquitetural — MVC, Padronizacao PT-BR e CI (05/10/2026 a 09/10/2026 — 13 commits)
- **Commits:** `c1a532e` a `71a6d9f`.
- **Caracteristicas:** Transformacao de script utilitario em arquitetura de software estruturada:
  - Separacao em camadas **MVC** (`InterfaceGrafica`, `ControladorApp`, `OrquestradorTraducoes`) e padroes **Strategy/Factory** (`FabricaProcessadores`, `ProcessadorMkv`, `ProcessadorSrt`).
  - Introducao do escudo anti-alucinacao por regex (`451425f`) e do Circuit Breaker (`3339782`).
  - Padronizacao integral de identificadores, classes e modulos para Portugues (`3339782`).
  - Criacao da suite de testes unitarios (`pytest`), mock E2E e pipeline de Integracao Continua no GitHub Actions (`12dad22`).
- **Problemas observados:**
  - Commits monoliticos misturando multiplas responsabilidades: `c1a532e` (+47.945 linhas) combinou refatoracao MVC com massa de dados de testes; `3339782` (+9.599 linhas) misturou renomeacao massiva de arquivos com mudanca de logica (injecao do Circuit Breaker), dificultando o rastreamento por `git log --follow` e `git blame`.

### Fase 5: Produto Desktop v2.7.0 — LosslessCut UI, i18n, Temas WCAG e Build (17/10/2026 — 6 commits)
- **Commits:** `e56eda4` a `9837596`.
- **Caracteristicas:**
  - Desacoplamento do dominio AniList e ativacao do modo WAL no SQLite (`e56eda4`).
  - Nova arquitetura visual modularizada (`tradutor/ui/`), suporte a 4 temas com contraste WCAG validado por testes e internacionalizacao em 5 idiomas (`9443f8d`, `66067ee`, `9837596`).
  - Automacao de build standalone com PyInstaller (`5e122c9`).
  - Adocao consistente de escopos semanticos nas mensagens (`feat(ui):`, `feat(packaging):`, `fix(core):`).

### Fase 6: Software Craftsmanship, Transcricao IA Whisper e Multi-Conteiner v2.8.0 (20/10/2026 a 29/10/2026 — 6 commits)
- **Commits:** `e029f08` a `b995e6e`.
- **Caracteristicas:**
  - Contratos de dominio imutaveis (`@dataclass(frozen=True, slots=True)` e `MappingProxyType`), lock fino no Circuit Breaker, isolamento de cliente por thread (`threading.local`) e operacoes em lote no SQLite (`get_many` / `put_many`) (`e029f08`, `b8c92ce`).
  - Remocao dos binarios do MKVToolNix da arvore de trabalho (`b8c92ce`).
  - Modulo opcional de transcricao de audio via Mozilla Whisperfile, recomendador acustico/hardware, suporte a `.mp4`/`.webm`/`.avi`/`.wmv`, conformidade de licencas de terceiros (`THIRD_PARTY_NOTICES.md`) e expansao para 166 testes unitarios (`6df420a`, `000b5d6`, `b995e6e`).

---

## 2. Correcoes Sem Risco Ja Aplicadas

As seguintes melhorias estruturais e de governanca Git foram aplicadas diretamente no ambiente local e nos arquivos de configuracao do projeto, sem risco de perda de dados ou quebra de hashes existentes:

| Item | Problema Identificado | Correcao Aplicada | Arquivos / Configuracao Afetados |
|---|---|---|---|
| **1. Identidade de Autor no Git** | Commits a partir de Set/2026 registravam `Administrador` em vez de `Caio Rosa`. | Configurado `git config --local user.name "Caio Rosa"` e `git config --global user.name "Caio Rosa"`. | Configuracao local (`.git/config`) e global (`~/.gitconfig`). |
| **2. Unificacao Historica de Autores** | Tres identidades distintas apareciam em `git shortlog` (`Caio Rosa` com dois e-mails e `Administrador`). | Criado arquivo `.mailmap` na raiz mapeando todas as variacoes para `Caio Rosa <117673906+CaioRosa96@users.noreply.github.com>`. | [`.mailmap`](../.mailmap) |
| **3. Desacoplamento de Artefatos Gerados de Teste** | 21 arquivos de saida `tests/data/legendas/*_*.srt` (`_PT.srt`, `_PTBR.srt`, `_PT_PT.srt`) estavam versionados e sujavam o `git status` a cada execucao do E2E. | Removidos do indice Git (`git rm --cached`), adicionada regra `tests/data/legendas/*_*.srt` ao `.gitignore` e ajustado `test_srt_lote.py` para limpar os arquivos temporarios gerados ao final do teste. | [`.gitignore`](../.gitignore), [`tests/e2e/test_srt_lote.py`](../tests/e2e/test_srt_lote.py) |
| **4. Validacao Automatica de Mensagens de Commit** | Mensagens historicas fora do padrao Conventional Commits ou iniciadas com letra maiuscula. | Instalado hook local `.git/hooks/commit-msg` em Python que valida o formato `<tipo>(<escopo-opcional>): <descricao em minusculo>` antes de aceitar qualquer novo commit. | `.git/hooks/commit-msg` |
| **5. Historico Estruturado de Versoes (Changelog)** | Ausencia de registro centralizado de mudancas entre as releases `v2.6-classic`, `v2.7.0` e `v2.8.0`. | Criado `CHANGELOG.md` na raiz seguindo o padrao Keep a Changelog. | [`CHANGELOG.md`](../CHANGELOG.md) |
| **6. Conformidade de Licencas e CI** | Falha no E2E do GitHub Actions por ausencia de `tests/output/` e ausencia de avisos GPLv2/Apache 2.0 nas releases. | Corrigido `tests/e2e/test_srt_lote.py` (`000b5d6`) e criado `THIRD_PARTY_NOTICES.md` (`b995e6e`). | [`THIRD_PARTY_NOTICES.md`](../THIRD_PARTY_NOTICES.md), [`tests/e2e/test_srt_lote.py`](../tests/e2e/test_srt_lote.py) |

---

## 3. Correcoes Nao Aplicadas (Pendentes ou de Processo Continuo)

Os itens abaixo **nao foram executados automaticamente** por envolverem reescrita destrutiva do historico remoto, configuracoes externas da conta GitHub ou disciplina continua em futuros commits:

### 3.1 Expurgo dos Binarios Antigos do Historico Git (`git filter-repo`)
- **O que e:** Embora o commit `b8c92ce` tenha removido a pasta `mkvtoolnix/` da branch atual, os objetos binarios adicionados no commit `dc29b2e` permanecem armazenados dentro de `.git/objects/pack` (~47 MiB).
- **Por que nao foi aplicado:** Reescrever o historico com `git filter-repo --path mkvtoolnix/ --invert-paths` altera todos os hashes SHA-1 de todos os commits desde `dc29b2e`, exigindo `git push --force --all` e invalidando as referencias de commit das releases `v2.6-classic`, `v2.7.0` e `v2.8.0` ja publicadas no GitHub.
- **Recomendacao:** Manter como esta, a menos que o tamanho do `git clone` Inicial (~47 MiB) se torne um gargalo real.

### 3.2 Granularidade Atomica em Novos Commits (Disciplina de Processo)
- **O que e:** Commits anteriores (`c1a532e`, `3339782`, `b8c92ce`, `6df420a`) agruparam multiplas features ou misturaram renomeacao de arquivos com alteracao de logica.
- **Por que nao foi aplicado retroativamente:** Dividir commits ja publicados na `master` tambem reescreveria o historico remoto.
- **Regra para os proximos commits:**
  1. Separar renomeacoes/movimentacoes de arquivos (`refactor(estrutura): ...`) em um commit exclusivo antes de alterar logica interna.
  2. Realizar um commit por responsabilidade coesa (`feat(transcricao): ...`, `feat(video): ...`, `perf(cache): ...`, `fix(fila): ...`).

### 3.3 Imutabilidade de Tags Publicadas (Versionamento Semantico de Correcao)
- **O que e:** A tag `v2.8.0` foi movida com `git push -f origin v2.8.0` apos ajustes de CI e documentacao.
- **Regra para as proximas versoes:** Uma vez que uma tag e uma Release sao publicadas no GitHub, a tag nunca deve ser movida com `--force`. Qualquer correcao subsequente no pipeline ou na documentacao deve gerar uma nova tag de patch (`v2.8.1`).

### 3.4 Protecao da Branch `master` no GitHub (Configuracao Externa da Conta)
- **O que e:** Todo o desenvolvimento ocorreu por push direto na branch `master`, o que permitiu que o commit `b8c92ce` ficasse com o CI quebrado sem bloqueio preventivo.
- **Como ativar no GitHub (opcional):** Em `Settings -> Branches -> Add branch ruleset` no repositorio GitHub, ativar *Require status checks to pass* selecionando o job `build-and-test` do GitHub Actions e trabalhar em branches tematicas (`feat/...`, `fix/...`) quando a alteracao envolver multiplos subsistemas.

