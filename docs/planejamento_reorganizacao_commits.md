# Planejamento de Reorganizacao do Historico de Commits (Padrao da Industria)

Este documento estabelece o plano arquitetural e operacional para reorganizar o historico Git do repositorio **TradutorDeLegendas**, aplicando os padroes de engenharia adotados por projetos de referencia da industria (Linux Kernel Patch Series, Conventional Commits v1.0.0, SemVer 2.0.0 e os 4 Pilares de Operacoes Seguras).

---

## 1. Diagnostico Quantitativo do Historico Atual

A inspecao completa dos 43 commits atuais (`733ba33..b995e6e`) revelou cinco distorcoes estruturais que degradam a auditabilidade, o `git blame`, o `git bisect` e o tempo de clonagem:

| Indicador | Estado Atual (43 Commits) | Meta Pos-Reorganizacao (51 Commits Atomicos) |
|---|---|---|
| **Tamanho do Pack Git (`.git/objects/pack`)** | **47,26 MiB** (poluido por binarios excluidos depois) | **< 1,50 MiB** (reducao de ~97%) |
| **Identidades de Autor no Log** | 3 variacoes (`Administrador`, 2 e-mails de `Caio Rosa`) | 1 identidade unica (`Caio Rosa <117673906+CaioRosa96@...>`) |
| **Conformidade Conventional Commits** | **58%** (18 commits sem tipo, sem escopo ou capitalizados) | **100%** (`<tipo>(<escopo>): <verbo no infinitivo>`) |
| **Mega-Commits (> 2 responsabilidades)** | 6 commits (`c1a532e`, `3339782`, `66067ee`, `9837596`, `b8c92ce`, `6df420a`) | **0** (1 responsabilidade coesa por commit) |
| **Mistura de `git mv` com logica** | Presente em `3339782` e `9837596` (quebra `git log --follow`) | **0** (renomeacoes isoladas em commits puros de estrutura) |

### 1.1 Inventario de Poluicao Binaria e Gerada no Historico
Mesmo removidos na ponta da `master`, os seguintes arquivos continuam gravados nos objetos internos do Git:
1. `mkvtoolnix/` (`dc29b2e` -> `b8c92ce`): 202 arquivos binarios/HTML (~120 MB descomprimidos).
2. `tests/data/VideoForTest.mkv` (`07ccda2` -> `b8c92ce`): 19,86 MB de video binario.
3. `cache_traducoes.db` (`3339782` -> `1834d15`): 585 KB de banco SQLite binario.
4. `tests/relatorio_teste_massivo.json` e `tests/output/relatorio_teste_massivo.json` (`c1a532e` -> `b8c92ce`): 18.066 linhas de saida JSON.
5. `tests/data/legendas/*_PT.srt`, `*_PTBR.srt`, `*_PT_PT.srt` (`c1a532e`, `451425f`, `3339782`): 21 arquivos gerados (~37.800 linhas).
6. `TaradutorLegendas26.pyproj` e `.slnx` (`e19a132` -> `b8c92ce`): arquivos locais de IDE.
7. `docs/contexto_alteracoes_para_gemini.txt` e rascunhos (`da28481` -> `5ceff78`): adicionados e deletados 41 minutos depois.

---

## 2. Principios do Padrao da Industria Adotados

1. **Regra da Atomicidade e Bisectability (Padrao Linux Kernel / Git):**
   - Cada commit deve responder a uma unica pergunta: *"O que esta mudanca faz e por que?"*.
   - Nenhum commit intermediario pode conter erro de sintaxe conhecido (como `846c32d` corrigido por `39cd33d` 3 minutos depois — ambos devem sofrer *squash/fixup*).
2. **Isolamento Estrito de Renomeacoes (`Rename-Only Commits`):**
   - O Git nao rastreia renomeacoes por metadados, mas por heuristica de similaridade de conteudo (`-M`). Quando um arquivo e renomeado (`controller.py -> controlador.py` ou `TaradutorLegendas26.py -> TradutorLegendas26.py`) no mesmo commit em que seu codigo e reescrito, o `git blame` perde a linhagem. Toda renomeacao massiva deve ser um commit isolado com 100% de similaridade.
3. **Taxonomia Fechada de Tipos e Escopos (Conventional Commits v1.0.0):**
   - **Tipos permitidos:** `feat`, `fix`, `refactor`, `perf`, `test`, `docs`, `chore`, `build`, `ci`.
   - **Escopos canonicos do dominio:**
     - `repo`: `.gitignore`, `.gitattributes`, `.mailmap`, licencas.
     - `core`: contratos imutaveis, orquestrador, controlador, configuracao base.
     - `mkv`: `ManipuladorMkv`, `ProcessadorMkv`, `ProcessadorSrt`, `FabricaProcessadores`.
     - `tradutor`: `ServicoTraducao`, `MotorTraducaoGoogle`, `ITradutor`, disjuntor.
     - `glossario`: `GerenciadorGlossario`, `glossario.txt`, `glossarios/`.
     - `anilist`: `tradutor/anilist.py`, `alimentar_glossario.py`.
     - `cache`: `CacheTraducoes` (SQLite WAL).
     - `idiomas`: `tradutor/idiomas.py`.
     - `transcricao`: `tradutor/transcritores/` (Whisperfile e recomendador).
     - `ui`: `InterfaceGrafica`, `InterfaceClassica`, componentes `tradutor/ui/`.
     - `i18n`: `tradutor/i18n.py`, `tradutor/locales/*.json`.
     - `tema`: `tradutor/ui/tema.py`.
     - `packaging`: `packaging/build.py`, `iniciar.bat`.
     - `testes`: suite unitaria (`tests/unit/`) e E2E (`tests/e2e/`).
     - `ci`: `.github/workflows/tests.yml`.
     - `docs`: `README.md`, `CHANGELOG.md`, `THIRD_PARTY_NOTICES.md`, `docs/`.
4. **Preservacao Cronologica Real (`AuthorDate`):**
   - Ao dividir ou higienizar commits, as datas originais (`--date`) sao preservadas para manter a fidelidade historica do desenvolvimento (Julho a Outubro de 2026).

---

## 3. Mapa Completo de Transformacao (De 43 Commits Brutos + Implementacoes Atuais para 51 Commits Atomicos)

### Epoca 1 — Fundacao e Prototipo Funcional (09/07/2026 a 12/09/2026)

| Novo # | Operacao sobre Commits Originais | Nova Mensagem Padronizada (Conventional Commits) | Justificativa de Engenharia |
|---|---|---|---|
| **01** | `733ba33` + `2156d19` + `7aa25a7` (regras de ignore consolidadas desde a raiz) | `chore(repo): configurar .gitignore e .gitattributes iniciais do projeto` | Garante que `venv/`, `mkvtoolnix/`, `*.db`, `*.pyproj` e `tests/output/` sejam ignorados desde o commit #1. |
| **02** | `e19a132` (expurgando `.pyproj` e `.slnx`) | `feat(core): implementar estrutura base do tradutor de legendas` | Mantem apenas codigo produtivo (`TaradutorLegendas26.py`). |
| **03** | `834cdc9` (expurgando `.slnx`) | `feat(mkv): integrar mkvtoolnix para extracao e autodetecao de idioma` | Padroniza mensagem sem tipo. |
| **04** | **SQUASH** `846c32d` + `39cd33d` | `fix(mkv): corrigir deteccao e remultiplexacao de legendas .ass em arquivos mkv` | Elimina o commit quebrado intermediario (`39cd33d` corrigia erro de sintaxe de `846c32d` 3 min depois). |
| **05** | `e07ca7b` | `fix(mkv): remover legendas .ass temporarias apos multiplexacao no video` | Mantem atomicidade e padroniza verbo no infinitivo. |
| **06** | `91f49d4` | `refactor(ui): simplificar selecao de saida e aprimorar mensagens de status` | Adiciona tipo e escopo ausentes. |
| **07** | `22a9258` | `feat(core): adicionar processamento em lote de multiplos arquivos` | Adiciona tipo e escopo ausentes. |
| **08** | `dc29b2e` (mantendo apenas `TaradutorLegendas26.py`, **expurgando** os 202 arquivos de `mkvtoolnix/`) | `feat(config): adicionar resolucao portatil do mkvtoolnix e validacao de dependencias` | Elimina ~120 MB de binarios mantendo 100% da logica em Python. |
| **09** | **SQUASH** `7760056` + `0a66812` | `docs(readme): criar documentacao inicial e instrucoes do modo portatil` | Funde ajuste de 2 linhas feito 3 minutos apos criar o README. |
| **10** | `837ed56` | `fix(tradutor): corrigir palavras aglutinadas e preservacao de quebras de linha` | Padroniza escopo `tradutor`. |
| **11** | `e4df8a5` | `refactor(ui): migrar interface grafica para customtkinter e criar script iniciar.bat` | Mantem commit coeso de migracao visual. |
| **12** | `475e489` | `feat(mkv): adicionar preferencia de idioma na extracao de legendas` | Padroniza escopo `mkv`. |
| **13** | **SQUASH** `c8206ec` + `181c028` | `docs(readme): atualizar documentacao com interface customtkinter e preservacao de srt` | Consolida duas micro-atualizacoes de README adjacentes. |
| **14** | `0245e1f` | `fix(core): garantir thread-safety na interface e persistencia de cache` | Corrige autor de `Administrador` para `Caio Rosa`. |

---

### Epoca 2 — Arquitetura MVC, Strategy, Escudo Anti-Alucinacao e CI (`v2.6-classic` — 05/10 a 09/10/2026)

| Novo # | Operacao sobre Commits Originais | Nova Mensagem Padronizada (Conventional Commits) | Justificativa de Engenharia |
|---|---|---|---|
| **15** | **SPLIT 1/2 de `c1a532e`** (`tradutor/*`, `TaradutorLegendas26.py`) | `refactor(core): estruturar arquitetura em camadas mvc e servico assincrono de traducao` | Separa a refatoracao MVC pura da massa de dados de teste (+47 mil linhas). |
| **16** | **SPLIT 2/2 de `c1a532e`** (`tests/`, `testar.bat` — **expurgando** `*_PTBR.srt` e `relatorio_teste_massivo.json`) | `test(e2e): adicionar massa de legendas originais multi-idiomas e suite de integracao` | Versiona apenas as 8 legendas de entrada (`.srt`), sem artefatos gerados de saida. |
| **17** | `d61a825` | `feat(ui): adicionar selecao dinamica de idioma de destino e cancelamento gracioso` | Padroniza mensagem. |
| **18** | `451425f` (**expurgando** os 8 arquivos `*_PT.srt`) | `feat(glossario): implementar escudo anti-alucinacao por regex e suporte a drag-and-drop` | Remove 14.400 linhas de saida gerada, mantendo apenas `glossary.py`, `glossario.txt` e `gui.py`. |
| **19** | `da28481` (**expurgando** os 3 rascunhos `.txt`/`.md` apagados em `5ceff78`) | `feat(idiomas): implementar mapeamento iso-639-2 e varredura inteligente de faixas mkv` | Elimina rascunhos temporarios que foram deletados em `5ceff78`. |
| **20** | `07ccda2` (**expurgando** `VideoForTest.mkv` e saidas `*_PT*.srt`) | `refactor(testes): organizar diretorio tests em unit, e2e, scripts e data` | Remove video binario de 19,8 MB mantendo a reestruturacao de pastas. |
| **21** | **SPLIT 1/2 de `3339782`** (apenas `git mv` de `controller.py`, `glossary.py`, `gui.py`, `mkv_wrapper.py`, `translator_service.py`) | `refactor(core): padronizar nomes de modulos e classes do pacote tradutor para portugues` | **Crucial:** isola o `git mv` com alta similaridade para preservar `git log --follow` e `git blame`. |
| **22** | **SPLIT 2/2 de `3339782`** (`tradutor/estrategias/*`, `tradutor/tradutores/*`, `cache.py`, `logger.py` — **expurgando** `cache_traducoes.db` e `*_PT_PT.srt`) | `feat(core): introduzir padrao strategy de processadores, cache sqlite e circuit breaker` | Isola a nova arquitetura Strategy/Adapter e o disjuntor sem arquivos `.db` nem `.srt` gerados. |
| **23** | **SPLIT 1/2 de `12dad22`** (`alimentar_glossario.py`, `glossarios/*.txt`, `tradutor/glossario.py`) | `feat(anilist): adicionar extrator de glossarios por obra via graphql do anilist` | Separa a feature do AniList da criacao do CI/CD. |
| **24** | **SPLIT 2/2 de `12dad22`** (`.github/workflows/tests.yml`, `tests/unit/*` — **expurgando** `cache_traducoes.db`) | `ci(testes): implementar suite de testes unitarios com pytest e workflow github actions` | Corrige prefixo invalido `Testes:` para `ci(testes):`. |
| **25** | `1834d15` | `fix(core): estabilizar pipeline de traducao, caminhos de configuracao e execucao no ci` | Mantem correcoes de estabilizacao. |
| **26** | **SQUASH** `9662642` + `69bb44c` + `71a6d9f` | `docs(repo): adicionar licenca mit e documentar arquitetura mvc no readme principal` | Consolida a transicao de `docs/README.md` para `README.md` na raiz + `LICENSE`. **(Tag `v2.6-classic`)** |

---

### Epoca 3 — Modularizacao de Dominio, UI LosslessCut v2.7.0, Temas WCAG e Build (`v2.7.0` — 17/10/2026)

| Novo # | Operacao sobre Commits Originais | Nova Mensagem Padronizada (Conventional Commits) | Justificativa de Engenharia |
|---|---|---|---|
| **27** | **SPLIT 1/2 de `e56eda4`** (`tradutor/anilist.py`, `alimentar_glossario.py`, `test_alimentar_glossario.py`) | `refactor(anilist): desacoplar servico de dominio anilist do wrapper interativo cli` | Isola a modularizacao do AniList. |
| **28** | **SPLIT 2/2 de `e56eda4`** (`tradutor/cache.py`, `tradutor/servico_traducao.py`, `test_cache.py`, `test_servico_traducao.py`) | `fix(cache): ativar modo wal no sqlite e preservar alinhamento posicional de linhas vazias` | Isola as correcoes de concorrencia SQLite e alinhamento de lotes. |
| **29** | **SPLIT 1/2 de `9837596`** (`TaradutorLegendas26.py -> TradutorLegendas26.py`) | `refactor(repo): corrigir grafia do ponto de entrada principal para TradutorLegendas26.py` | Isola a renomeacao do arquivo raiz. |
| **30** | `9443f8d` (absorvendo ajustes de UI de `9837596` e **expurgando** `prototipo_layout_completo.py`) | `feat(ui): implementar interface moderna v2.7.0 inspirada no losslesscut e preservar modo classico` | Elimina a duplicacao de mensagem entre `9443f8d` e `9837596` e remove arquivo temporario de prototipo. |
| **31** | **SPLIT 1/2 de `66067ee`** (`tradutor/i18n.py`, `tradutor/config_usuario.py`, `tradutor/locales/*.json`) | `feat(i18n): adicionar motor de internacionalizacao em 5 idiomas e persistencia de preferencias` | Isola a infraestrutura de i18n e preferencias de usuario. |
| **32** | **SPLIT 2/2 de `66067ee` + `9837596`** (`tradutor/ui/tema.py`, `modal_*.py`, `tests/unit/test_tema.py`, `test_config_e_modais.py`) | `feat(ui): adicionar 4 temas com conformidade wcag e modais de configuracao e grimorio` | Agrupa os temas e modais com seus respectivos testes matematicos WCAG. |
| **33** | `af39c65` | `fix(glossario): blindar tags ass/html no escudo e reforcar resiliencia do servico de traducao` | Mantem commit focado no core. |
| **34** | `5e122c9` | `feat(packaging): adicionar automacao de build standalone via pyinstaller para versoes moderna e classica` | **(Tag `v2.7.0`)** |

---

### Epoca 4 — Contratos Imutaveis, Isolamento de Threads, IA Whisper e Multi-Conteiner (`v2.8.0` — 20/10 a 29/10/2026)

| Novo # | Operacao sobre Commits Originais | Nova Mensagem Padronizada (Conventional Commits) | Justificativa de Engenharia |
|---|---|---|---|
| **35** | **SPLIT 1/2 de `e029f08`** (`tradutor/contratos.py`, `tradutor/glossario.py`, `test_contratos_escudo.py`) | `refactor(core): definir value objects imutaveis LinhaProtegida e portas formais do escudo e cache` | Isola os contratos de dominio e testes Golden Master SHA-256. |
| **36** | **SPLIT 2/2 de `e029f08`** (`tradutor/cache.py`, `tradutor/tradutores/google.py`, `test_cache.py`, `test_disjuntor_google.py`) | `perf(core): implementar operacoes em lote get_many/put_many no sqlite e lock fino no disjuntor` | Isola a evolucao de concorrencia no SQLite e no Circuit Breaker. |
| **37** | **SPLIT de `b8c92ce`** (`google.py`, `orquestrador.py`, `processador_base.py`, `glossario.py`, `servico_traducao.py` e testes) | `refactor(tradutor): isolar instancia do cliente google por thread e compartilhar disjuntor na fila` | Separa o codigo produtivo de `b8c92ce` da exclusao de 178 mil linhas de binarios (ja eliminados na origem no Novo #08). |
| **38** | **SPLIT 1/6 de `6df420a`** (`tradutor/idiomas.py`, `tradutor/locales/*.json`, `tests/unit/test_idiomas.py`) | `feat(idiomas): localizar abreviacoes e siglas nativas nos 5 idiomas da interface` | Desmembra o mega-commit `6df420a` em unidades atomicas testaveis. |
| **39** | **SPLIT 2/6 de `6df420a`** (`tradutor/servico_traducao.py`, `tests/unit/test_servico_traducao.py`) | `perf(cache): reaproveitar hits parciais via get_many e persistir sub-frases com put_many` | Isola a otimizacao de cache em 2 niveis. |
| **40** | **SPLIT 3/6 de `6df420a`** (`tradutor/transcritores/base.py`, `whisperfile.py`, `recomendador.py`, `test_transcritor_whisper.py`) | `feat(transcricao): implementar motor opcional whisperfile com catalogo de modelos e recomendador acustico` | Isola o novo subsistema de dominio de transcricao via IA local. |
| **41** | **SPLIT 4/6 de `6df420a`** (`fabrica.py`, `processador_base.py`, `processador_mkv.py`, `manipulador_mkv.py`) | `feat(mkv): suportar conteineres mp4, webm, avi e wmv com politica configuravel de formato de saida` | Isola o suporte multi-conteiner e integracao FFmpeg. |
| **42** | **SPLIT 5/6 de `6df420a`** (`tradutor/ui/modal_whisper.py`, `modal_config.py`, `fila.py`, `interface.py`, `controlador.py`) | `feat(ui): adicionar seletor de modelos whisper e botao de analise de ia por card na fila` | Isola os novos componentes visuais da v2.8.0. |
| **43** | **SPLIT 6/6 de `6df420a`** (`orquestrador.py`, `interface.py`, `test_config_e_modais.py`) | `fix(ui): preservar botao cancelar e impedir execucao duplicada ao remover item durante o lote` | Isola o bugfix de concorrencia na fila com seu teste de regressao. |
| **44** | `000b5d6` + limpeza automatica de `*_PT.srt` | `fix(testes): garantir criacao da pasta de saida e limpeza de artefatos temporarios no teste e2e` | Mantem o E2E 100% deterministico e limpo. |
| **45** | `b995e6e` + `CHANGELOG.md` + `.mailmap` | `docs(licenca): adicionar THIRD_PARTY_NOTICES.md, CHANGELOG.md e mapeamento de autores` | **(Tag `v2.8.0`)** |

---

### Epoca 5 — Observabilidade, Automacao de Releases, Som em Memoria e Desacoplamento GPLv2/MIT (08/11/2026)

| Novo # | Operacao sobre Alteracoes da Arvore Atual | Nova Mensagem Padronizada (Conventional Commits) | Justificativa de Engenharia |
|---|---|---|---|
| **46** | `tradutor/logger.py` | `feat(core): evoluir logger com retencao de 7 dias, teto de 20mb, fallback localappdata e crash hook` | Isola a evolucao do sistema de logging para producao no Windows. |
| **47** | `tradutor/atualizador.py`, `tradutor/som.py`, `tradutor/interface_classica.py`, `tests/unit/test_logger_atualizador_som.py` | `feat(ui): adicionar verificador de atualizacoes via github releases e acorde wav sintetizado em memoria` | Agrupa os servicos de notificacao sonora em RAM e consulta de versao com seus testes unitarios. |
| **48** | `packaging/build.py`, `tradutor/config.py`, `tradutor/config_usuario.py`, `tradutor/instalador_dependencias.py`, `tradutor/ui/modal_dependencias.py`, `tradutor/ui/modal_config.py`, `tradutor/ui/__init__.py`, `tradutor/interface.py`, `tradutor/controlador.py`, `tradutor/orquestrador.py`, `tradutor/manipulador_mkv.py`, `tradutor/estrategias/*`, `tests/unit/test_instalador_dependencias.py` | `feat(config): desacoplar binarios gplv2 do build exe e adicionar instalador e modal de dependencias` | Isola a conformidade 100% MIT das Releases e o fluxo de download/selecao de pasta customizada do MKVToolNix. |
| **49** | `tradutor/locales/*.json`, `tests/unit/test_config_e_modais.py` | `test(i18n): sincronizar catalogos nos 5 idiomas e adicionar testes de contrato de chaves e placeholders` | Garante paridade de chaves e marcadores `{n}` em todos os idiomas da interface. |
| **50** | `.github/workflows/tests.yml`, `.github/workflows/release.yml` | `ci(release): adicionar controle de concorrencia no ci e workflow de publicacao automatica por tag` | Automatiza compilacao e publicacao de Releases a partir do `CHANGELOG.md`. |
| **51** | `README.md`, `THIRD_PARTY_NOTICES.md`, `CHANGELOG.md`, `docs/*.md` | `docs(repo): atualizar readme com guia smartscreen, avisos mit/gplv2 e documentacao arquitetural` | Consolida toda a documentacao atualizada do repositorio. |

---

## 4. Protocolo de Execucao Segura (4 Pilares de Operacoes)

Caso voce decida autorizar a execucao deste plano de reescrita, o procedimento seguira rigorosamente os 4 Pilares de Operacoes Seguras (`akita-four-pillars-ops`):

1. **Pilar 1 — Escopo Positivo e Backup Integral (Snapshot Imutavel):**
   - Criacao de um clone espelho completo (`git clone --mirror . ../TradutorDeLegendas_backup_mirror.git`) e de uma branch de seguranca (`backup/pre-reorganizacao-43-commits`) antes de tocar em qualquer objeto.
2. **Pilar 2 — Restricoes Negativas (Invariantes Intocaveis):**
   - **Zero alteracao no codigo-fonte final:** O comando `git diff backup/pre-reorganizacao-43-commits..master` ao final da reorganizacao **deve retornar exatamente vazio (0 bytes de diferenca)** para todos os arquivos produtivos e de teste.
   - Os 166 testes unitarios (`pytest tests/unit -v`) e o teste E2E (`python tests/e2e/test_srt_lote.py`) devem passar 100%.
3. **Pilar 3 — Oraculo / Dry-Run em Branch Isolada:**
   - Toda a reconstrucao da arvore de commits e executada inicialmente em uma branch orfa isolada (`reorg/historico-limpo`), sem afetar a `master` local nem o GitHub remoto.
   - Validacao de `git log --oneline`, `git shortlog -sne`, `git count-objects -vH` e `git diff` contra a `master` original.
4. **Pilar 4 — Confirmacao de Pos-Condicao e Sincronizacao:**
   - Somente apos a verificacao matematica de que `git diff` entre a ponta antiga e a ponta nova e vazio e que o pack caiu de ~47 MiB para < 1,5 MiB, a `master` e as tags (`v2.6-classic`, `v2.7.0`, `v2.8.0`) sao atualizadas.

