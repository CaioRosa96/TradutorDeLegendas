# Histórico de Versões (Changelog)

Todas as mudanças relevantes deste projeto são documentadas neste arquivo, seguindo o padrão [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/) e o esquema de versionamento semântico.

---

## [2.9.0] - 2026-11-10

### Adicionado
- Desacoplamento completo de binários sob licença GPLv2 (`mkvmerge.exe` e `mkvextract.exe`) dos executáveis `.exe` das Releases (100% MIT), acompanhado do serviço `InstaladorDependencias` (`tradutor/instalador_dependencias.py`) e da janela `ModalDependencias` (`tradutor/ui/modal_dependencias.py`) para download sob demanda ou seleção manual de outra pasta pelo usuário.
- Logger de produção (`tradutor/logger.py`) com retenção automática de 7 dias, teto diário de 20 MB por arquivo, sonda de escrita com fallback para `%LOCALAPPDATA%`, cabeçalho real do Windows 10/11 e captura global de exceções (`sys.excepthook` / `threading.excepthook`).
- Verificador de atualizações in-app (`tradutor/atualizador.py`) e créditos clicáveis na aba Sobre do `ModalConfiguracoes`.
- Sintetizador de acorde musical suave em memória RAM (`tradutor/som.py`) via `winsound.SND_MEMORY` ao concluir lotes de tradução, sem arquivos externos.
- Workflow de publicação automática de Releases por tag (`.github/workflows/release.yml`) extraindo notas do `CHANGELOG.md` e gerando `SHA256SUMS.txt`.
- Testes de contrato de paridade de chaves e placeholders `{n}` para todos os catálogos i18n (`tradutor/locales/*.json`).

### Corrigido
- Falha crítica de assinatura em `CacheTraducoes.put_many` ao persistir sub-frases traduzidas a partir de dicionário (`Mapping[str, str]`), que lançava `TypeError` e acionava o bloco de exceção do `ServicoTraducao._traduzir_lote`, revertendo as falas já traduzidas para o idioma original (inglês) na 1ª execução de episódios inéditos.
- Isolamento *best-effort* de gravação no cache local (`_salvar_cache_seguro` e `_salvar_lote_cache_seguro`), impedindo que falhas de escrita no SQLite revertam legendas já traduzidas em memória.
- Filtro de proteção contra gravação de linhas contendo tokens sintéticos de glossário (`TKGLOSS{n}T`) no cache individual de Nível 2 durante o fluxo de sub-lote parcial.
- Isolamento do banco SQLite em diretório temporário durante a execução do teste E2E (`tests/e2e/test_srt_lote.py`), evitando gravação de entradas `[MOCK]` no banco local.

---

## [2.8.0] - 2026-10-29

### Adicionado
- Módulo opcional de transcrição local de áudio via Mozilla Whisperfile (`tradutor/transcritores/`) sob o contrato `ITranscritor`, com suporte aos modelos `tiny`, `small`, `medium` e `large-v3` e download sob demanda para a pasta `bin/`.
- Recomendador acústico e de hardware (`RecomendadorModeloWhisper`) que inspeciona duração do vídeo, idioma da faixa de áudio, presença de música de fundo/efeitos sonoros (`ffmpeg silencedetect`) e memória RAM livre via `GlobalMemoryStatusEx`.
- Botão individual `Analisar IA` nos cards da fila de processamento (`CardArquivo`), exibido automaticamente apenas para vídeos sem legenda embutida.
- Suporte nativo a múltiplos contêineres de vídeo (`.mkv`, `.mp4`, `.webm`, `.avi`, `.wmv`) com política configurável de formato de saída: conversão sem perda via *stream copy* para `.mkv` ou manutenção do contêiner original (`mov_text` para MP4, `webvtt` para WebM e `.srt` externo para AVI/WMV).
- Auto-alimentação opcional de glossários por obra integrada ao pipeline de tradução via API GraphQL do AniList (`auto_alimentar`).
- Arquivo `THIRD_PARTY_NOTICES.md` detalhando licenças e links de código-fonte de componentes externos (MKVToolNix sob GPLv2, Mozilla Whisperfile sob Apache 2.0/MIT e FFmpeg).

### Alterado
- Localização completa de todas as abreviações e siglas de idiomas nos 5 idiomas da interface (`pt-br`, `en`, `es`, `ja`, `zh-cn`), eliminando siglas latinas em japonês e chinês.
- Isolamento de instâncias de `Translator` por thread (`threading.local`) em `MotorTraducaoGoogle` e compartilhamento do estado do Circuit Breaker entre todos os arquivos da fila no `OrquestradorTraducoes`.
- Otimização do `ServicoTraducao` para consulta parcial em lote (`get_many`) e persistência individual de sub-frases traduzidas (`put_many`) no SQLite WAL.
- Ajuste de lookarounds na expressão regular do escudo anti-alucinação (`GerenciadorGlossario.apply_shield`) para proteger siglas terminadas em pontuação (ex.: `U.A.`).

### Corrigido
- Regressão de estado visual na fila ao remover um arquivo pendente durante a execução de um lote em andamento, preservando o botão `CANCELAR` e impedindo o disparo duplicado de threads no `OrquestradorTraducoes`.
- Criação automática do diretório `tests/output/` e ajuste de inicialização da flag `_is_running` no teste E2E (`tests/e2e/test_srt_lote.py`) para execução no GitHub Actions.

---

## [2.7.0] - 2026-10-17

### Adicionado
- Nova interface gráfica moderna inspirada no LosslessCut (`tradutor/interface.py` e pacote `tradutor/ui/`), com sidebar de parâmetros, fila em cards dinâmicos e gaveta retrátil de logs.
- Preservação da interface clássica em `tradutor/interface_classica.py` e ponto de entrada dedicado `TradutorLegendas26_Classico.py`.
- Sistema de internacionalização desacoplado (`tradutor/i18n.py` e catálogos JSON em `tradutor/locales/`) para 5 idiomas (`pt-br`, `en`, `es`, `ja`, `zh-cn`).
- Suporte a 4 temas visuais (`escuro`, `claro`, `alto_contraste`, `ms_dos`) com validação matemática de contraste WCAG 2.x.
- Modais dedicados para Configurações (`ModalConfiguracoes`), Grimório de Glossários (`ModalGrimorio`) e Visualizador de Logs.
- Script de empacotamento automatizado via PyInstaller (`packaging/build.py`) gerando executáveis standalone (`TradutorLegendas.exe` e `TradutorLegendas_Classico.exe`).
- Contratos formais imutáveis (`LinhaProtegida`, `ResultadoTraducaoLinha`, `EscudoTagsPort` e `CacheTraducaoPort` em `tradutor/contratos.py`).

### Alterado
- Extração das regras de negócio do AniList para o módulo de domínio `tradutor/anilist.py`, mantendo `alimentar_glossario.py` como wrapper CLI enxuto.
- Ativação do modo WAL (`PRAGMA journal_mode=WAL`) e buscas em lote fatiadas (`get_many` / `put_many`) no `CacheTraducoes`.

---

## [2.6-classic] - 2026-10-09

### Adicionado
- Arquitetura MVC desacoplada (`InterfaceGrafica`, `ControladorApp`, `OrquestradorTraducoes`) e padrões Strategy/Factory (`FabricaProcessadores`, `ProcessadorMkv`, `ProcessadorSrt`).
- Escudo anti-alucinação por tokenização reversível (`GerenciadorGlossario`) com suporte a glossários globais e por obra.
- Circuit Breaker thread-safe no `MotorTraducaoGoogle` e fallback sequencial resiliente no `ServicoTraducao`.
- Suíte inicial de testes unitários com `pytest` e workflow de Integração Contínua no GitHub Actions (`.github/workflows/tests.yml`).
- Licença MIT oficial do repositório.

