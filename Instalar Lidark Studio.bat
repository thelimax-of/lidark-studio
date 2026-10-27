@echo off
chcp 65001 >nul
title Instalar Lidark Studio
echo.
echo   ============================================
echo     LIDARK STUDIO - instalar atalhos
echo   ============================================
echo.
echo   Vai criar no MENU INICIAR (e na area de trabalho):
echo     - "Lidark Studio": liga o sistema e abre o painel como aplicativo
echo     - "Parar Lidark":  desliga o sistema
echo.
echo   O Lidark NAO inicia sozinho com o Windows: ele so roda quando voce abrir.
echo.
pause
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$root = '%~dp0'.TrimEnd('\');" ^
  "$ws = New-Object -ComObject WScript.Shell;" ^
  "$menu = [Environment]::GetFolderPath('Programs');" ^
  "$desk = [Environment]::GetFolderPath('Desktop');" ^
  "$old = [Environment]::GetFolderPath('Startup') + '\Lidark Channel.lnk'; if (Test-Path $old) { Remove-Item $old -Force };" ^
  "function New-Lnk($path, $vbs, $desc) { $l = $ws.CreateShortcut($path); $l.TargetPath = $env:WINDIR + '\System32\wscript.exe'; $l.Arguments = '\"' + $root + '\launcher\' + $vbs + '\"'; $l.WorkingDirectory = $root; $l.IconLocation = $root + '\backend\assets\lidark.ico'; $l.Description = $desc; $l.Save() };" ^
  "New-Lnk ($menu + '\Lidark Studio.lnk') 'Lidark Studio.vbs' 'Abrir o Lidark Studio';" ^
  "New-Lnk ($menu + '\Parar Lidark.lnk') 'Parar Lidark.vbs' 'Desligar o Lidark';" ^
  "New-Lnk ($desk + '\Lidark Studio.lnk') 'Lidark Studio.vbs' 'Abrir o Lidark Studio';" ^
  "Write-Host ''; Write-Host '  Pronto! Procure por Lidark Studio no Menu Iniciar.' -ForegroundColor Green"
echo.
echo   Dica: no Menu Iniciar, clique com o botao direito em "Lidark Studio" e escolha
echo   "Fixar no Inicio" ou "Fixar na barra de tarefas".
echo.
pause
