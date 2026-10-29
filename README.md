# Tradutor de Legendas

![GitHub Actions Workflow Status](https://img.shields.io/github/actions/workflow/status/Xaxadox/TradutorDeLegendas/tests.yml?style=flat-square&label=Testes%20CI)
![Python](https://img.shields.io/badge/Python-3.11%2B-blue?style=flat-square)
![Licença](https://img.shields.io/badge/Licen%C3%A7a-MIT-green?style=flat-square)

O **Tradutor de Legendas** é uma ferramenta de automação para extração, transcrição opcional de áudio via IA local, tradução e multiplexação de legendas em arquivos de vídeo (`.mkv`, `.mp4`, `.webm`, `.avi` e `.wmv`), bem como legendas avulsas nos formatos SRT, ASS e TXT. O sistema emprega processamento assíncrono para garantir alto desempenho, acompanhado por tolerância a falhas, cache persistente local em dois níveis e proteção de contexto via glossário dinâmico.

---

## Funcionalidades Principais

- **Tradução em Lote Concorrente:** Utiliza `asyncio` e `ThreadPoolExecutor` com isolamento de cliente por thread (`threading.local`) para particionar e traduzir legendas em paralelo, respeitando a cadência da API.
- **Cache Local Inteligente em Dois Níveis (SQLite WAL):** Sistema `CacheTraducoes` que armazena assinaturas SHA-256 tanto de blocos inteiros quanto de linhas individuais (`get` e `get_many` fatiado). Reaproveita instantaneamente falas repetidas (como aberturas e encerramentos entre episódios) mesmo quando o restante do bloco muda.
- **Escudo Anti-Alucinação (Tokenização Isolada):** Substitui nomes próprios, siglas com pontuação e tags de formatação ASS/HTML por tokens protegidos antes do envio ao motor de tradução e restaura os valores originais após a resposta.
- **Dicionários Específicos e Integração AniList:** Suporta glossários customizados por obra na pasta `glossarios/` e extração automática de personagens via GraphQL (`auto_alimentar`).
- **Transcrição Opcional de Áudio com Diagnóstico Acústico (Mozilla Whisperfile):** Vídeos que não possuem legendas embutidas podem ter o áudio extraído, filtrado na faixa de voz humana (WAV PCM 16 kHz mono) e transcrito localmente para `.srt` antes de seguir para a tradução. Inclui recomendador automático de modelo (`RecomendadorModeloWhisper`) baseado em duração, acústica e RAM livre, além de catálogo com download sob demanda (`tiny`, `small`, `medium` e `large-v3`).
- **Suporte Multi-Contêiner de Vídeo (`.mkv`, `.mp4`, `.webm`, `.avi`, `.wmv`):** Extrai trilhas de legenda ou áudio via MKVToolNix e FFmpeg, traduz preservando estilizações e permite escolher entre converter sem perda de qualidade (`stream copy`) para `.mkv` (preservando estilos `.ass`) ou manter o formato original do arquivo (`mov_text` para MP4, `webvtt` para WebM ou `.srt` externo para AVI/WMV).
- **Detecção e Mapeamento Localizado de Idiomas:** Varre faixas disponíveis em contêineres de vídeo e mapeia códigos ISO-639-2 para códigos ISO-639-1 com abreviações nativas localizadas nos 5 idiomas da interface (`pt-br`, `en`, `es`, `ja`, `zh-cn`).

---

## Tolerância a Falhas e Resiliência

- **Circuit Breaker (Disjuntor de Rede Compartilhado):** O motor de tradução monitora falhas consecutivas da API sob lock de granularidade fina e compartilha o estado do disjuntor ao longo de toda a fila de arquivos no `OrquestradorTraducoes`.
- **Fallback Sequencial Resiliente:** Se a tradução em lote apresentar discrepância na contagem de linhas retornadas, o sistema comuta automaticamente para tradução individual item a item com consulta ao cache.
- **Auditoria Estruturada de Logs:** Toda a operação do sistema é gravada em arquivos rotativos na pasta `logs/`, contendo níveis de severidade, contexto e timestamps detalhados.

---

## Arquitetura (Padrão MVC, Strategy e Ports)

O projeto é estruturado segundo os princípios de separação de responsabilidades (MVC e Design Patterns):

- **View (`tradutor/interface.py` e `tradutor/ui/`):** Interface gráfica inspirada no layout moderno do LosslessCut (painel lateral de parâmetros, fila com cards dinâmicos por arquivo, seletor de 4 temas com conformidade WCAG, modal de configurações e console de logs retrátil). A versão clássica permanece preservada em `tradutor/interface_classica.py`.
- **Controller (`tradutor/controlador.py`):** Camada mediadora que processa comandos do usuário e sincroniza eventos entre a interface e as regras de negócio.
- **Model / Orquestrador (`tradutor/orquestrador.py`):** Gerenciador de pipeline que coordena o fluxo em lote de forma desacoplada da interface gráfica.
- **Estratégias (`tradutor/estrategias/`):** Aplicação do Strategy e Template Method via `FabricaProcessadores`, delegando a lógica especializada para `ProcessadorMkv` ou `ProcessadorSrt`.
- **Serviço de Tradução (`tradutor/servico_traducao.py`):** Motor assíncrono que abstrai provedores de tradução através da interface `ITradutor`.
- **Transcritores (`tradutor/transcritores/`):** Módulo opt-in desacoplado sob o contrato `ITranscritor` com implementação `MotorWhisperfile` e diagnóstico acústico/hardware em `RecomendadorModeloWhisper`.

---

## Instalação e Execução

### Pré-requisitos
- Python 3.11 ou superior.
- MKVToolNix e FFmpeg (para processamento de contêineres de vídeo e áudio):
  - **Opção 1 (Automática/Sistema):** O script `iniciar.bat` detecta a instalação em `C:\Program Files\MKVToolNix` ou instala automaticamente via `winget`.
  - **Opção 2 (Portátil):** Coloque os executáveis `mkvmerge.exe`, `mkvextract.exe` e `ffmpeg.exe` na pasta `mkvtoolnix/` ou `bin/` na raiz do projeto.
- *(Opcional)* Mozilla Whisperfile para transcrição de vídeos sem legenda:
  - O próprio aplicativo oferece catálogo integrado nas Configurações e no modal de confirmação para baixar sob demanda os modelos `tiny`, `small`, `medium` ou `large-v3` diretamente para a pasta `bin/`.

### Execução Rápida (Windows)
Dê um duplo clique no arquivo **`iniciar.bat`**. O script configura automaticamente o ambiente virtual (`venv/`), valida as dependências com verificação SSL e inicia a aplicação.

### Execução Manual
```bash
# Clone o repositório
git clone https://github.com/Xaxadox/TradutorDeLegendas.git

# Crie e ative o ambiente virtual
python -m venv venv
.\venv\Scripts\activate

# Instale as dependências
pip install -r requirements.txt

# Inicie a aplicação
python TradutorLegendas26.py
```

---

## Suíte de Testes e Qualidade

O repositório possui cobertura de **166 testes unitários automatizados** com pytest, além de integração contínua (CI) via GitHub Actions.

### Testes Unitários
Os testes rodam de forma 100% offline, utilizando diretórios temporários e injeção de mocks:
```bash
pytest tests/unit/ -v
```
Você também pode rodar os testes diretamente pelo script auxiliar **`testar.bat`**.

**Cobertura dos testes:**
- `test_contratos_escudo.py`: Imutabilidade de Value Objects (`LinhaProtegida`) e Golden Master SHA-256.
- `test_glossario.py`: Tokenização reversível, preservação de tags ASS/HTML e siglas com pontuação (`U.A.`).
- `test_disjuntor_google.py`: Concorrência do Circuit Breaker, transição half-open e isolamento `threading.local`.
- `test_cache.py`: Operações SQLite WAL sob concorrência de 20 threads, `get_many` fatiado e `put_many` atômico.
- `test_servico_traducao.py`: Simulação assíncrona da API, cache em dois níveis e fallback sequencial.
- `test_transcritor_whisper.py`: Resolução de binário Whisperfile, conversão FFmpeg WAV 16 kHz e fallback MKV.
- `test_alimentar_glossario.py`: Sanitização de nomes de arquivo e integração mockada com a API AniList.
- `test_tema.py` e `test_config_e_modais.py`: Contraste matemático WCAG 2.x nos 4 temas, i18n em 5 idiomas e modais.
- `test_idiomas.py`: Conversão bidirecional entre códigos ISO-639-2 e códigos do Google Translate.

### Teste E2E (End-to-End)
Validação de pipelines completos de lote em ambiente controlado:
```bash
python tests/e2e/test_srt_lote.py
```

---

## Licença

Este projeto está licenciado sob os termos da licença MIT. Para mais detalhes, consulte o arquivo [LICENSE](LICENSE).
