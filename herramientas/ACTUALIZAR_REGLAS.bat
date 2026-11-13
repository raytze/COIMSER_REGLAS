@echo off
rem Trae la ultima version de las reglas COIMSER desde el repositorio (git pull).
rem iLogic debe tener como carpeta de reglas externas:  <esta carpeta>\..\iLogic
cd /d "%~dp0.."
git pull
echo.
echo Listo. Si Inventor estaba abierto, reinicialo para que iLogic cargue las reglas nuevas.
pause
