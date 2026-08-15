@echo off
title SisGAB — Watcher de Fotos com IA Local & Upload ao Drive
cls

echo ===============================================================================
echo   SISGAB - MOTOR DE IA LOCAL E UPLOAD PARALELO (10 WORKERS)
echo   Gabinete do CGCFN / Comunicacao Social
echo ===============================================================================
echo.

set /p EVENT_ID="Digite o ID/Numero do Evento [Padrao: 50]: "
if "%EVENT_ID%"=="" set EVENT_ID=50

set /p PASTA_FOTOS="Digite o Caminho da Pasta com as Fotos: "
if "%PASTA_FOTOS%"=="" set PASTA_FOTOS=F:\CGCFN\ENCONTRO VETERANOS\FOTOS\EXPORT

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
