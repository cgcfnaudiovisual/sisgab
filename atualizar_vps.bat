@echo off
:: =========================================================
:: Script de Atualização 1-Clique do SisGAB na VPS
:: =========================================================
title Atualizar SisGAB na VPS

echo =========================================================
echo  [SisGAB] Conectando e Atualizando o Servidor VPS...
echo =========================================================
echo.

:: Garante permissões seguras da chave
if not exist "%USERPROFILE%\.ssh\sisgab_key.pem" (
    mkdir "%USERPROFILE%\.ssh" 2>nul
    copy "%~dp0sisgab-server-ssh-key.key" "%USERPROFILE%\.ssh\sisgab_key.pem" /Y >nul
    icacls "%USERPROFILE%\.ssh\sisgab_key.pem" /inheritance:r >nul
    icacls "%USERPROFILE%\.ssh\sisgab_key.pem" /grant:r "%USERNAME%:(F)" >nul
)

:: Executa git pull e rebuild do docker na VPS
ssh -t -i "%USERPROFILE%\.ssh\sisgab_key.pem" ubuntu@193.122.207.129 "cd ~/sisgab 2>/dev/null || cd /home/ubuntu/sisgab 2>/dev/null || cd /app 2>/dev/null ; echo '>>> Atualizando repositorio...' ; git pull ; echo '>>> Reconstruindo containers...' ; sudo docker compose down && sudo docker compose up -d --build ; exec bash -l"

echo.
echo Atualizacao concluida com sucesso!
pause
