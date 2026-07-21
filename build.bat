@echo off
REM ============================================================
REM  Build EnvLock.exe  (a lancer sous Windows)
REM ============================================================
setlocal

REM 1. Environnement virtuel
if not exist ".venv\Scripts\python.exe" (
    echo [EnvLock] Creation de l'environnement virtuel...
    python -m venv .venv || goto :error
)

call .venv\Scripts\activate.bat

REM 2. Dependances + PyInstaller
echo [EnvLock] Installation des dependances...
python -m pip install --upgrade pip >nul
python -m pip install -r requirements.txt || goto :error
python -m pip install pyinstaller || goto :error

REM 3. Nettoyage puis build
echo [EnvLock] Compilation...
rmdir /s /q build dist 2>nul
pyinstaller --clean EnvLock.spec || goto :error

echo.
echo [EnvLock] OK -^> dist\EnvLock.exe
goto :eof

:error
echo.
echo [EnvLock] ECHEC du build.
exit /b 1
