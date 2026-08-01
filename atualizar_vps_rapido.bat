@echo off
:: =========================================================
:: Script de Atualização RÁPIDA do SisGAB na VPS
:: =========================================================
title Atualizar SisGAB na VPS (Rapido)

echo =========================================================
echo  [SisGAB] Atualizacao Rapida na VPS (193.122.207.129)...
echo =========================================================
echo.

:: Garante permissões seguras da chave
if not exist "%USERPROFILE%\.ssh\sisgab_key.pem" (
    mkdir "%USERPROFILE%\.ssh" 2>nul
    copy "%~dp0sisgab-server-ssh-key.key" "%USERPROFILE%\.ssh\sisgab_key.pem" /Y >nul
    icacls "%USERPROFILE%\.ssh\sisgab_key.pem" /inheritance:r >nul
    icacls "%USERPROFILE%\.ssh\sisgab_key.pem" /grant:r "%USERNAME%:(F)" >nul
)

:: Conecta na VPS, entra na pasta e roda git pull + docker compose down + docker compose up -d --build
ssh -t -i "%USERPROFILE%\.ssh\sisgab_key.pem" ubuntu@193.122.207.129 "cd ~/sisgab 2>/dev/null || cd /home/ubuntu/sisgab 2>/dev/null || cd /app 2>/dev/null ; git pull ; sudo docker compose down ; sudo docker compose up -d --build ; exec bash -l"

echo.
echo Atualizacao rapida concluida com sucesso!
pause
