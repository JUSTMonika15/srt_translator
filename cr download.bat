@echo off
setlocal enabledelayedexpansion

REM 获取脚本所在文件夹
set "SCRIPT_DIR=%~dp0"

REM 使用 %USERPROFILE% 替代硬编码路径
set "FFMPEG=%USERPROFILE%\OneDrive - UW-Madison\Computer Backup-Videos\critical role\download video\ffmpeg-7.1-full_build\bin"
set "YTDLP=%USERPROFILE%\OneDrive - UW-Madison\Computer Backup-Videos\critical role\download video\yt-dlp.exe"
set "COOKIES=%USERPROFILE%\OneDrive - UW-Madison\Computer Backup-Videos\critical role\download video\www.youtube.com_cookies.txt"

REM 自动更新 yt-dlp
echo Checking for yt-dlp updates...
"%YTDLP%" -U
echo.

cd /d "%USERPROFILE%\OneDrive - UW-Madison\Computer Backup-Videos\critical role"

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

REM 显示可用格式
"%YTDLP%" --cookies "%COOKIES%" -F "%cleanlink%"
echo.
set /p userformat=Download format (default: 137+140, or type 'best' for best 1080p): 

if "%userformat%"=="" (
    set "format=137+140"
) else if /i "%userformat%"=="best" (
    set "format=bestvideo[height>=1080]+bestaudio/best[height>=1080]"
) else (
    set "format=%userformat%"
)

set "output_template=%%(title)s.%%(ext)s"

"%YTDLP%" --ffmpeg-location "%FFMPEG%" --cookies "%COOKIES%" --force-ipv4 -f "%format%" --merge-output-format mp4 -o "%output_template%" "%cleanlink%"

REM 自动转换为PR兼容的mp4（H.264）
for %%f in (*.webm *.mkv) do (
    "%FFMPEG%\ffmpeg.exe" -i "%%f" -c:v libx264 -c:a aac "%%~nf-convert.mp4"
    echo Converted: %%~nf-convert.mp4
)

echo.
echo Download complete. Listing new files in this folder:
for %%f in (*.mp4 *.mkv *.webm) do (
    echo Output: "%cd%\%%f"
)
pause