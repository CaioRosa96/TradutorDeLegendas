@echo off
echo ===================================================
echo     Iniciando Tradutor Automatico de Legendas
echo ===================================================
echo.

if not exist venv\ (
    echo [INFO] Criando ambiente virtual...
    python -m venv venv
)

echo [INFO] Ativando ambiente virtual...
call venv\Scripts\activate

fc /b requirements.txt venv\.req_cache >nul 2>&1
if errorlevel 1 (
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

pause
