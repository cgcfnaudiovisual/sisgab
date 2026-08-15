@echo off
title SisGAB — Watcher de Fotos com IA Local (GPU) & Upload ao Drive
cls

python "%~dp0event_photo_watcher.py" --interactive --workers 10

echo.
echo ===============================================================================
echo   Processamento finalizado ou interrompido.
echo ===============================================================================
pause
