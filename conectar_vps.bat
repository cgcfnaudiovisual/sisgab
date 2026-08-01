@echo off
:: =========================================================
:: Script de Conexão Rápida SisGAB VPS
:: =========================================================
title Conectar VPS SisGAB

echo =========================================================
echo  [SisGAB] Conectando a VPS (193.122.207.129)...
echo =========================================================
echo.

:: Garante que a chave esteja configurada com permissões seguras
if not exist "%USERPROFILE%\.ssh\sisgab_key.pem" (
    mkdir "%USERPROFILE%\.ssh" 2>nul
    copy "%~dp0sisgab-server-ssh-key.key" "%USERPROFILE%\.ssh\sisgab_key.pem" /Y >nul
    icacls "%USERPROFILE%\.ssh\sisgab_key.pem" /inheritance:r >nul
    icacls "%USERPROFILE%\.ssh\sisgab_key.pem" /grant:r "%USERNAME%:(F)" >nul
)

:: Conecta via SSH e entra direto na pasta do projeto na VPS
ssh -t -i "%USERPROFILE%\.ssh\sisgab_key.pem" ubuntu@193.122.207.129 "cd ~/sisgab 2>/dev/null || cd /home/ubuntu/sisgab 2>/dev/null || cd /app 2>/dev/null ; exec bash -l"

echo.
echo Conexao encerrada.
pause
