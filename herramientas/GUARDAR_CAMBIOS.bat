@echo off
rem Sube al repositorio los cambios hechos en las reglas (git add + commit + push).
cd /d "%~dp0.."
git status --short
echo.
set /p MSG=Describe el cambio (ej. "CUT_LIST v1.3: hoja de retazos"): 
if "%MSG%"=="" goto fin
git add -A
git commit -m "%MSG%"
git push
:fin
pause
