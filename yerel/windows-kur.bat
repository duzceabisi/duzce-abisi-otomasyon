@echo off
chcp 65001 >nul
rem Duzce Abisi - Windows kurulumu: bu dosyaya cift tiklayin
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0kur.ps1" %*
pause
