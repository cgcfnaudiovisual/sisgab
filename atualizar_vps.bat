@echo off
:: =========================================================
:: Script de Atualização FORÇADA (Sem Cache) do SisGAB na VPS
:: =========================================================
title Atualizar SisGAB na VPS (Forcar Rebuild)

echo =========================================================
echo  [SisGAB] Conectando e Forcando Rebuild na VPS...
echo =========================================================
echo.

:: Garante permissões seguras da chave
if not exist "%USERPROFILE%\.ssh\sisgab_key.pem" (
    mkdir "%USERPROFILE%\.ssh" 2>nul
    copy "%~dp0sisgab-server-ssh-key.key" "%USERPROFILE%\.ssh\sisgab_key.pem" /Y >nul
    icacls "%USERPROFILE%\.ssh\sisgab_key.pem" /inheritance:r >nul
    icacls "%USERPROFILE%\.ssh\sisgab_key.pem" /grant:r "%USERNAME%:(F)" >nul
)

:: Executa git pull + docker compose build --no-cache + force-recreate
ssh -t -i "%USERPROFILE%\.ssh\sisgab_key.pem" ubuntu@193.122.207.129 "cd ~/sisgab 2>/dev/null || cd /home/ubuntu/sisgab 2>/dev/null || cd /app 2>/dev/null ; echo '>>> 1/3 Baixando arquivos atualizados do GitHub...' ; git pull ; echo '>>> 2/3 Reconstruindo container SEM CACHE...' ; sudo docker compose build --no-cache ; echo '>>> 3/3 Reiniciando container...' ; sudo docker compose up -d --force-recreate ; exec bash -l"

echo.
echo Atualizacao concluida com sucesso!
pause
