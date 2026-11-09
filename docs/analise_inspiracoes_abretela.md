# Analise Arquitetural e Inspiracoes do Projeto AbreTela (`beqm/abretela`)

Este documento analisa o repositorio [beqm/abretela](https://github.com/beqm/abretela) (aplicativo desktop para Windows em Tauri/Rust + Svelte) e mapeia as solucoes de engenharia, UX, testes, observabilidade e CI/CD que podem ser adaptadas diretamente para o **Tradutor de Legendas**.

---

## 1. Visao Geral do que Torna o `beqm/abretela` uma Referencia

Embora o dominio funcional seja diferente (compartilhamento de tela P2P via WebRTC + tunel Cloudflare), o `abretela` resolve exatamente os mesmos desafios de engenharia de produto desktop para Windows que o **Tradutor de Legendas**:
- Empacotamento de binarios externos (*sidecars* como `cloudflared.exe` la, `mkvmerge.exe` / `whisperfile.exe` aqui).
- Internacionalizacao multi-idiomas (`pt`, `en`, `es`, `zh`, `ja`, `ko`).
- Sistema de logs locais resiliente no Windows com rotacao automatica.
- Distribuicao via GitHub Releases para usuarios finais no Windows (lidando com SmartScreen e atualizacoes).
- Suite de testes de contrato e CI automatizado em `windows-latest`.

---

## 2. Ideias de Alto Impacto para Aplicar no Tradutor de Legendas

### Ideia 1: Testes Contratuais de Internacionalizacao (`src/lib/locales/locales.test.ts`)
- **Como o `abretela` faz:** Possui um teste automatizado que compara todos os dicionarios de idioma (`en`, `es`, `zh`, `ko`, `ja`) contra o dicionario base (`pt`), exigindo tres invariantes:
  1. **Mesmas chaves:** Nenhum idioma pode ter chave faltando ou sobrando em relacao ao portugues.
  2. **Mesmos marcadores (`{0}`, `{}`):** Todas as strings traduzidas precisam conter exatamente os mesmos placeholders de formatacao que o texto em portugues (evitando `IndexError` / `KeyError` quando o aplicativo formata mensagens em outros idiomas).
  3. **Nenhum texto vazio:** Nenhuma traducao pode ser string em branco.
- **Como aplicar aqui (`tests/unit/test_config_e_modais.py` + `tradutor/locales/`):**
  - Implementar `test_contrato_paridade_chaves_e_placeholders_locales()` validando `en.json`, `es.json`, `ja.json` e `zh-cn.json` contra `pt-br.json`.
  - Opcionalmente adicionar suporte ao idioma **Coreano (`ko.json`)** na interface, igualando os 6 idiomas do `abretela`.

---

### Ideia 2: Logger Resiliente com Retencao de 7 Dias, Limite de 20 MB, Fallback de Pasta e Captura de Crashes (`src-tauri/src/logging/mod.rs`)
- **Como o `abretela` faz:**
  1. **Retencao automatica (`prune`):** Mantem apenas os ultimos 7 dias de arquivo `.log` (`KEEP_DAYS = 7`), apagando os mais antigos na inicializacao e na virada de meia-noite.
  2. **Teto contra loop de erro (`MAX_BYTES = 20 MB`):** Impede que uma falha em loop lote o SSD do usuario.
  3. **Sonda de permissao de escrita (`pick_dir`):** Testa gravar um arquivo `.teste` na pasta `logs/` ao lado do `.exe`. Se o aplicativo estiver instalado em diretorio restrito (como `C:\Program Files`), faz fallback transparente para `%LOCALAPPDATA%`.
  4. **Cabecalho de diagnostico real do Windows 11/10:** Le `CurrentBuildNumber` e `DisplayVersion` do registro do Windows (`build >= 22000` -> Windows 11, corrigindo o fato de o Windows 11 se reportar como Windows 10 para APIs legadas) e grava no topo do log:
     `===== Tradutor de Legendas v2.8.0 · Windows 11 24H2 (build 26200) · Python 3.11.9 =====`
  5. **Hook global de excecoes (`panic::set_hook`):** Qualquer erro fatal nao tratado na thread principal ou em threads de trabalho e gravado no arquivo de log antes de encerrar.
- **Como aplicar aqui ([`tradutor/logger.py`](../tradutor/logger.py)):**
  - Evoluir `setup_logger()` (atualmente com apenas 39 linhas basicas) incorporando a limpeza dos 7 dias (`prune`), limite de tamanho, fallback para `LOCALAPPDATA`, cabecalho de diagnostico do Windows e `sys.excepthook` / `threading.excepthook`.

---

### Ideia 3: Verificador de Atualizacoes via GitHub Releases e Aba "Sobre / Creditos" (`src/lib/update.ts` + `Credits.svelte`)
- **Como o `abretela` faz:**
  - Na tela de Configuracoes (e na inicializacao opcional), consulta a ultima release no GitHub com timeout curto (8s), informa se o usuario ja esta na versao mais recente ou exibe um botao para baixar a nova versao.
  - Exibe creditos discretos e clicaveis (`Tradutor de Legendas v2.8.0 · Desenvolvido por @CaioRosa96 · GitHub`).
- **Como aplicar aqui (`tradutor/ui/modal_config.py` + novo modulo `tradutor/atualizador.py`):**
  - Adicionar no rodape do `ModalConfiguracoes` o bloco de versao/creditos clicavel (`@CaioRosa96`) e um botao **"Procurar atualizacoes"** que consulta `https://api.github.com/repos/CaioRosa96/TradutorDeLegendas/releases/latest` em background thread sem travar a UI.

---

### Ideia 4: Automacao de CI (`concurrency`) e Release Automatica a partir do `CHANGELOG.md` (`.github/workflows/ci.yml` e `release.yml`)
- **Como o `abretela` faz:**
  1. No `ci.yml`, declara:
     ```yaml
     concurrency:
       group: ci-${{ github.ref }}
       cancel-in-progress: true
     ```
     Se voce fizer dois pushes seguidos na mesma branch, o GitHub Actions cancela imediatamente a execucao anterior em andamento.
  2. No `release.yml`, ao enviar qualquer tag `v*` (`git push origin v2.8.1`), o workflow extrai automaticamente o texto daquela versao de dentro do `CHANGELOG.md`, compila o executavel no runner `windows-latest` e publica a GitHub Release pronta com o binario anexado.
- **Como aplicar aqui (`.github/workflows/tests.yml` e `.github/workflows/release.yml`):**
  - Adicionar o bloco `concurrency` ao `tests.yml`.
  - Criar `.github/workflows/release.yml` que extrai as notas do nosso `CHANGELOG.md`, compila `TradutorLegendas.exe` e `TradutorLegendas_Classico.exe` via `packaging/build.py` e publica a Release automaticamente ao detectar uma tag `v*`.

---

### Ideia 5: Feedback Sonoro Sintetizado Sem Arquivos Externos (`src/lib/sounds.ts`) e Indicador na Barra de Tarefas (`tray.rs`)
- **Como o `abretela` faz:**
  - Em vez de usar o `MessageBeep` padrao de erro/alerta do Windows, sintetiza um acorde curto e agradavel em memoria (arpejo suave de Do maior ou Mi -> Si) respeitando a preferencia `tocar_som`.
  - Altera o estado visual/tooltip enquanto uma operacao pesada esta ativa.
- **Como aplicar aqui (`tradutor/interface.py`):**
  - Gerar em memoria um pequeno buffer WAV PCM de 200ms (acorde suave de conclusao) tocado via `winsound.PlaySound(..., winsound.SND_MEMORY | winsound.SND_ASYNC)` quando `tocar_som=True`, substituindo o som generico do sistema operacional sem adicionar nenhum arquivo `.wav` ao repositorio.

---

### Ideia 6: Estrutura de `README.md` com Guia Direto e Aviso do Windows SmartScreen
- **Como o `abretela` faz:**
  - Coloca logo no topo do `README.md` o passo a passo de 3 linhas para quem quer apenas baixar o `.exe` na aba Releases, acompanhado de um bloco `> [!WARNING]` explicando a tela *"O Windows protegeu o computador"* (SmartScreen para executaveis sem certificado comercial caro: clicar em **Mais informacoes** -> **Executar assim mesmo**).
- **Como aplicar aqui ([`README.md`](../README.md)):**
  - Adicionar a secao rapida de download do executavel standalone com o alerta explicativo do Windows SmartScreen.

---

## 3. Resumo de Priorizacao Sugerida

| # | Melhoria Inspirada no `abretela` | Complexidade | Impacto no Produto |
|---|---|---|---|
| **1** | Teste contratual de paridade de chaves e `{placeholders}` nos 5 idiomas (`locales`) | Baixa | Alto (previne crashes de traducao na UI) |
| **2** | Evolucao do `tradutor/logger.py` (retencao 7 dias, teto 20 MB, fallback `LOCALAPPDATA`, build real Win10/11 e crash hook) | Baixa | Alto (observabilidade e seguranca em disco) |
| **3** | `concurrency` no CI + workflow `.github/workflows/release.yml` lendo o `CHANGELOG.md` | Baixa | Alto (releases 100% automatizadas por tag) |
| **4** | Verificador de atualizacoes via GitHub API + creditos `@CaioRosa96` no modal de Configuracoes | Media | Alto (experiencia de aplicativo moderno) |
| **5** | Aviso do Windows SmartScreen e guia rapido de `.exe` no `README.md` | Muito Baixa | Medio (reduz duvidas de usuarios finais) |
| **6** | Som sintetizado suave em memoria (`SND_MEMORY`) ao concluir lote | Baixa | Medio (polimento de UX) |

