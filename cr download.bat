@echo off
setlocal enabledelayedexpansion

set "FFMPEG=C:\Users\10279\OneDrive - UW-Madison\Computer Backup-Videos\critical role\download video\ffmpeg-7.1-full_build\bin"

cd /d "C:\Users\10279\OneDrive - UW-Madison\Computer Backup-Videos\critical role"

set /p subfolder=Enter subfolder (leave blank for current): 
if not "%subfolder%"=="" (
    if exist "%subfolder%\" (
        cd "%subfolder%"
    ) else (
        echo Subfolder "%subfolder%" does not exist. Exiting.
        pause
        exit /b
    )
)

set /p link=Paste the YouTube link: 

REM 去掉&t=xxx参数
for /f "delims=&" %%a in ("%link%") do set "cleanlink=%%a"

REM 只下载最好的1080p（137+140），不可用则报错不降级
set "format=137+140"

set "output_template=%%(title)s.%%(ext)s"

yt-dlp --ffmpeg-location "%FFMPEG%" -f "%format%" --abort-on-unavailable-fragment -o "%output_template%" "%cleanlink%"

echo.
echo Download complete. Listing new files in this folder:
for %%f in (*.mp4 *.mkv *.webm) do (
    echo Output: "%cd%\%%f"
)
pause