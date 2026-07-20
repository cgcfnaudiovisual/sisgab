@echo off
title SisGAB
cd /d "%~dp0"

echo.
echo ========================================
echo   SisGAB - Sistema de Gestao de Gabinete
echo ========================================
echo.

REM Verificar se virtualenv existe
if not exist "venv" (
    echo [1/3] Criando ambiente virtual...
    py -m venv venv
)

echo [2/3] Ativando ambiente virtual...
call venv\Scripts\activate.bat

echo [3/3] Verificando dependencias...
pip install -r requirements.txt --quiet

echo.
echo Iniciando servidor...
echo Acesse: http://localhost:8080
echo.
echo Pressione CTRL+C para parar
echo.

python main.py
pause
