@echo off
chcp 65001 >nul
title AI Football Shorts Studio
if exist "venv\Scripts\python.exe" (
    start "" "venv\Scripts\pythonw.exe" app.py
) else (
    echo [ЕСКЕРТУ] Алдымен "install.bat" файлын іске қосып, бағдарламаны орнатып алыңыз!
    pause
)
