# Especificação de Engenharia: Desacoplamento do MKVToolNix do Git e Automação Sob Demanda (Revisão Argon)

**Repositório:** TradutorDeLegendas (TaradutorLegendas26)  
**Objetivo:** Desacoplar binários pesados de terceiros (`mkvtoolnix/` ~168 MB e `tests/data/VideoForTest.mkv` ~19 MB) do controle de versão, mantendo o código-fonte limpo (~340 KB) e provendo detecção/instalação automatizada e segura.  
**Destinatário da Execução:** Antigravity IDE / Gemini 4 Argon  
**Diretrizes de Qualidade:** `perfil_caio` §0 (Língua PT-BR e Zero Emojis em Docs), §1 (MVC/OOP), §2 (Segurança SSL/TLS), §7 (Repositório Limpo e Git); `AGENTS.md §5.6` (Resolução Dinâmica de Caminhos); skills: `akita-four-pillars-ops`, `accidental-data-loss-prevention`.

---

## 1. Diagnóstico e Motivação Técnica

Atualmente, o código-fonte proprietário do projeto (Python, testes, JSONs de idioma e glossários) ocupa apenas **~340 KB**. No entanto, a pasta `mkvtoolnix/` (~168 MB) e o vídeo de teste `tests/data/VideoForTest.mkv` (~19 MB) estão versionados diretamente no Git.

### Impactos Negativos do Rastreamento Atual:
1. **Inchaço em Contextos e Ferramentas:** Qualquer inspeção global esbarra em arquivos binários compilados como `mkvtoolnix/data/qt_resources.rcc`.
2. **Clones e Exportações Pesadas:** O repositório carrega quase 200 MB de executáveis de terceiros.
3. **Caminhos Absolutos Fixos no Empacotamento:** Os arquivos `packaging/TradutorLegendas.spec` e `packaging/TradutorLegendas_Classico.spec` contêm caminhos absolutos codificados (`D:/programas/TaradutorLegendas26/...`), violando `AGENTS.md §5.6`, e `packaging/build.py` não consulta `GerenciadorConfig.get_mkvtoolnix_path()` quando a pasta local `mkvtoolnix/` está ausente.

---

## 2. Garantias Técnicas: `git rm --cached`, Histórico Git e `.gitattributes`

1. **Preservação dos Arquivos Físicos Locais:**
   - O comando `git rm -r --cached mkvtoolnix/` remove o rastreamento apenas do índice do Git (`HEAD`), **mantendo 100% dos arquivos intactos no disco local** (`d:\programas\TaradutorLegendas26\mkvtoolnix\`).
2. **Distinção entre `HEAD` (`git archive`) e Histórico `.git/objects`:**
   - `git rm --cached` faz com que o commit atual (`HEAD`) e qualquer pacote gerado por `git archive` caiam imediatamente para **~340 KB**.
   - Os *blobs* antigos permanecem no histórico `.git/objects/pack` para clones completos até que (opcionalmente e apenas sob ordem explícita do usuário) seja executado `git filter-repo` ou clone superficial (`git clone --depth 1`).
3. **Eliminação de Pastas Paralelas Manuais:**
   - Combinando `.gitignore` + `.gitattributes` (`export-ignore`), nunca mais será necessário manter cópias paralelas como `TaradutorLegendas26_Limpo`.

---

## 3. Plano Cirúrgico de Execução (4 Pilares Operacionais)

### Passo 1: Desindexação Segura no Git (Sem Exclusão Física)
```powershell
git rm -r --cached mkvtoolnix
git rm --cached tests/data/VideoForTest.mkv
git rm --cached TradutorLegendas26.pyproj TradutorLegendas26.slnx
```

### Passo 2: Blindagem em `.gitignore` e `.gitattributes`
- Ignorar `mkvtoolnix/`, vídeos de teste `.mkv`/`.mp4`, `tests/output/` e arquivos de projeto Visual Studio (`*.pyproj`, `*.slnx`).
- Declarar `export-ignore` em `.gitattributes` para garantir que `git archive -o codigo_limpo.zip HEAD` gere sempre um pacote enxuto.

### Passo 3: Automação Real e Verificação SSL em `iniciar.bat`
1. **Segurança SSL (`perfil_caio §2`):** Executar `pip install -r requirements.txt` com validação normal de certificado SSL/TLS; utilizar `--trusted-host` exclusivamente como contingência (`if errorlevel 1`).
2. **Detecção e Extração Completa do MKVToolNix:**
   - Verifica `C:\Program Files\MKVToolNix\mkvmerge.exe` e `mkvtoolnix\mkvmerge.exe`.
   - Caso ausente em ambos, tenta instalar via `winget install MoritzBunkus.MKVToolNix --silent` ou baixa o pacote portátil `.7z` e o extrai automaticamente utilizando `tar.exe -xf` nativo do Windows 10/11 (ou `7z.exe`), movendo os binários para `mkvtoolnix\`.

### Passo 4: Resolução Dinâmica em `packaging/build.py` e `.spec` (`AGENTS.md §5.6`)
- Em `packaging/build.py`, resolver os binários `mkvmerge.exe` e `mkvextract.exe` usando `GerenciadorConfig.get_mkvtoolnix_path()` como fallback caso `DIRETORIO_RAIZ/mkvtoolnix` não exista.
- Nos arquivos `.spec` (que já estão ignorados em `.gitignore` na linha 384), substituir caminhos absolutos `D:/programas/TaradutorLegendas26` por resolução dinâmica via `os.path.abspath`.

---

## 4. Blocos `SEARCH/REPLACE` para Aplicação

### A. Modificação em `.gitignore`
```markdown
### FILE: .gitignore
<<<<<<< SEARCH
# Visual Studio 2015/2017 cache/options directory
.vs/
=======
# Visual Studio 2015/2017 cache/options directory
.vs/
*.pyproj
*.slnx

# Ferramentas e Binarios Externos de Midia
mkvtoolnix/
tests/data/*.mkv
tests/data/*.mp4
tests/output/
>>>>>>>
```

### B. Modificação em `.gitattributes`
```markdown
### FILE: .gitattributes
<<<<<<< SEARCH
* text=auto
=======
* text=auto

# Exclusoes de exportacao (git archive)
mkvtoolnix/ export-ignore
tests/data/VideoForTest.mkv export-ignore
tests/output/ export-ignore
*.pyproj export-ignore
*.slnx export-ignore
>>>>>>>
```

### C. Modificação em `iniciar.bat`
```markdown
### FILE: iniciar.bat
<<<<<<< SEARCH
    echo [INFO] Instalando/atualizando dependencias...
    pip install --trusted-host pypi.org --trusted-host pypi.python.org --trusted-host files.pythonhosted.org -r requirements.txt
    copy /y requirements.txt venv\.req_cache >nul
) else (
    echo [INFO] Dependencias atualizadas. Pulando instalacao...
)

echo.
echo [INFO] Iniciando aplicacao...
python TradutorLegendas26.py
=======
    echo [INFO] Instalando/atualizando dependencias...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo [AVISO] Falha SSL detectada. Tentando contingencia para rede corporativa...
        pip install --trusted-host pypi.org --trusted-host pypi.python.org --trusted-host files.pythonhosted.org -r requirements.txt
    )
    copy /y requirements.txt venv\.req_cache >nul
) else (
    echo [INFO] Dependencias atualizadas. Pulando instalacao...
)

echo.
echo [INFO] Verificando dependencias do MKVToolNix...
if exist "C:\Program Files\MKVToolNix\mkvmerge.exe" (
    echo [INFO] MKVToolNix detectado na instalacao do sistema.
) else if exist "mkvtoolnix\mkvmerge.exe" (
    echo [INFO] MKVToolNix portatil detectado na pasta local.
) else (
    echo [AVISO] MKVToolNix nao encontrado. Tentando obter automaticamente...
    where winget >nul 2>&1
    if not errorlevel 1 (
        echo [INFO] Instalando MKVToolNix oficial via Winget...
        winget install --id MoritzBunkus.MKVToolNix -e --accept-source-agreements --accept-package-agreements
    ) else (
        echo [AVISO] Instale o MKVToolNix em C:\Program Files\MKVToolNix ou extraia na pasta mkvtoolnix\.
    )
)

echo.
echo [INFO] Iniciando aplicacao...
python TradutorLegendas26.py
>>>>>>>
```

### D. Modificação em `packaging/build.py`
```markdown
### FILE: packaging/build.py
<<<<<<< SEARCH
    mkvmerge_path = os.path.join(DIRETORIO_RAIZ, "mkvtoolnix", "mkvmerge.exe")
    mkvextract_path = os.path.join(DIRETORIO_RAIZ, "mkvtoolnix", "mkvextract.exe")
    if os.path.exists(mkvmerge_path) and os.path.exists(mkvextract_path):
        cmd.extend([
            "--add-binary", f"{mkvmerge_path};mkvtoolnix",
            "--add-binary", f"{mkvextract_path};mkvtoolnix"
        ])
=======
    sys.path.insert(0, DIRETORIO_RAIZ)
    from tradutor.config import GerenciadorConfig
    mkvmerge_path, mkvextract_path = GerenciadorConfig.get_mkv_bins()
    if os.path.exists(mkvmerge_path) and os.path.exists(mkvextract_path):
        cmd.extend([
            "--add-binary", f"{mkvmerge_path};mkvtoolnix",
            "--add-binary", f"{mkvextract_path};mkvtoolnix"
        ])
>>>>>>>
```

---

## 5. Critérios de Validação Pós-Condição

1. **Verificação Física (`Test-Path`):** `d:\programas\TaradutorLegendas26\mkvtoolnix\mkvmerge.exe` e `tests\data\VideoForTest.mkv` devem permanecer intactos no disco local.
2. **Suíte de Testes:** `.\venv\Scripts\pytest tests\unit -v` deve passar 100% dos testes sem regressão.
3. **Verificação de Índice:** `git status -s` deve listar a remoção dos binários apenas do índice (`D `) e modificação de `.gitignore`, `.gitattributes`, `iniciar.bat` e `packaging/build.py`.
