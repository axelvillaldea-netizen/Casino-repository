@echo off
REM Lancer le bot Casino depuis le .venv

cd /d "%~dp0"

if not exist ".venv" (
    echo Erreur: Environnement virtuel non trouvé!
    echo Executez: python -m venv .venv
    pause
    exit /b 1
)

echo Lancement du bot Casino...
.venv\Scripts\python.exe main.py

if errorlevel 1 (
    echo Erreur au lancement du bot
    pause
)
