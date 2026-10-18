@echo off
chcp 65001 >nul
title AI Football Shorts Studio - Орнату
color 0A

echo ================================================================
echo   ⚽ AI FOOTBALL SHORTS STUDIO - АВТОМАТТЫ ОРНАТУ БАСТАЛДЫ...
echo ================================================================
echo.

python --version >nul 2>&1
if %errorlevel% neq 0 (
    color 0C
    echo [ҚАТЕ] Компьютерден Python табылмады!
    pause
    exit /b
)

echo [1/4] FFmpeg тексерілуде...
ffmpeg -version >nul 2>&1
if %errorlevel% neq 0 (
    winget install Gyan.FFmpeg --accept-source-agreements --accept-package-agreements
)

echo.
echo [2/4] Виртуалды орта (venv) құрылуда...
if not exist "venv" (
    python -m venv venv
)

echo.
echo [3/4] Кітапханалар жүктелуде (3-5 минут күтіңіз)...
call venv\Scripts\activate
python -m pip install --upgrade pip
pip install customtkinter yt-dlp librosa faster-whisper ultralytics opencv-python moviepy==1.0.3 numpy scipy pillow requests beautifulsoup4

echo.
echo ================================================================
echo   ✅ БАРЛЫҒЫ СӘТТІ ОРНАТЫЛДЫ!
echo   Енді бағдарламаны қосу үшін "start.bat" файлын екі рет басыңыз!
echo ================================================================
pause
