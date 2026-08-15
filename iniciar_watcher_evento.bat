@echo off
chcp 65001 >nul
title SisGAB — Watcher de Fotos com IA Local & Upload ao Drive
color 0b

echo ===============================================================================
echo   SISGAB — MOTOR DE IA LOCAL & UPLOAD PARALELO (10 WORKERS)
echo   Gabinete do CGCFN / Comunicação Social
echo ===============================================================================
echo.

set /p EVENT_ID="Digite o ID/Número do Evento (ex: 50): "
if "%EVENT_ID%"=="" set EVENT_ID=50

set /p PASTA_FOTOS="Digite o Caminho da Pasta com as Fotos (ex: F:\CGCFN\ENCONTRO VETE): "
if "%PASTA_FOTOS%"=="" set PASTA_FOTOS=D:\FOTOS\%EVENT_ID%

echo.
echo -------------------------------------------------------------------------------
echo [1/2] Verificando pasta: "%PASTA_FOTOS%"
echo [2/2] Conectando ao SisGAB para o Evento: #%EVENT_ID%
echo -------------------------------------------------------------------------------
echo.

python "%~dp0event_photo_watcher.py" --event-id "%EVENT_ID%" --pasta "%PASTA_FOTOS%" --workers 10

echo.
echo ===============================================================================
echo   Processamento finalizado ou interrompido.
echo ===============================================================================
pause
