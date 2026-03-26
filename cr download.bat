@echo off
setlocal enabledelayedexpansion

REM 获取脚本所在文件夹
set "SCRIPT_DIR=%~dp0"

REM 使用 %USERPROFILE% 替代硬编码路径
set "FFMPEG=%USERPROFILE%\OneDrive - UW-Madison\Computer Backup-Videos\critical role\download video\ffmpeg-7.1-full_build\bin"
set "PHANTOMJS=%USERPROFILE%\OneDrive - UW-Madison\Computer Backup-Videos\critical role\download video\phantomjs-2.1.1-windows\bin\phantomjs.exe"
set "YTDLP=%USERPROFILE%\OneDrive - UW-Madison\Computer Backup-Videos\critical role\download video\yt-dlp.exe"
set "COOKIES=%USERPROFILE%\OneDrive - UW-Madison\Computer Backup-Videos\critical role\download video\www.youtube.com_cookies.txt"
set "THUMB_CONVERTER=%SCRIPT_DIR%convert_thumbnail_4x3.py"

REM 添加 PhantomJS 到 PATH
set "PATH=%USERPROFILE%\OneDrive - UW-Madison\Computer Backup-Videos\critical role\download video\phantomjs-2.1.1-windows\bin;%PATH%"

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

REM 选择下载类型
echo.
echo Select download type:
echo 1. Video (default)
echo 2. Subtitles
echo 3. Thumbnail (download and convert to 4:3)
echo 4. All (Video + Subtitles + Thumbnail)
echo.
set /p download_type=Enter choice (1/2/3/4, default: 1): 

if "%download_type%"=="" set "download_type=1"

set /p link=Paste the YouTube link: 

REM 去掉&t=xxx参数
for /f "delims=&" %%a in ("%link%") do set "cleanlink=%%a"

REM 根据选择执行
if "%download_type%"=="2" goto DOWNLOAD_SUBTITLES
if "%download_type%"=="3" goto DOWNLOAD_THUMBNAIL
if "%download_type%"=="4" (
    call :DOWNLOAD_VIDEO
    call :DOWNLOAD_SUBTITLES
    call :DOWNLOAD_THUMBNAIL
    goto END
)

REM ========== 下载视频 ==========
:DOWNLOAD_VIDEO
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

REM 使用 ffmpeg 作为下载器处理 HLS，添加更多重试参数
"%YTDLP%" ^
  --remote-components ejs:github ^
  --cookies "%COOKIES%" ^
  --ffmpeg-location "%FFMPEG%" ^
  --retries 20 --fragment-retries 20 ^
  --sleep-interval 2 --max-sleep-interval 10 ^
  --concurrent-fragments 1 ^
  --force-ipv4 ^
  -f "%format%" ^
  --merge-output-format mp4 ^
  -o "%output_template%" ^
  "%cleanlink%"

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
if "%download_type%"=="4" exit /b
goto END

REM ========== 下载字幕 ==========
:DOWNLOAD_SUBTITLES
echo.
echo Listing available subtitles...
"%YTDLP%" --cookies "%COOKIES%" --list-subs "%cleanlink%"
echo.

echo Downloading MANUAL English subtitles only [en]...
"%YTDLP%" --cookies "%COOKIES%" ^
  --skip-download ^
  --write-subs ^
  --sub-langs "en" ^
  --sub-format "vtt" ^
  --convert-subs srt ^
  -o "%%(title)s.%%(ext)s" ^
  "%cleanlink%"

echo.
echo Subtitle download complete. Listing new subtitle files:
dir /b *.srt 2>nul
if errorlevel 1 (
    echo No SRT files found. Manual English subtitles may not be available for this video.
) else (
    for %%f in (*.srt) do echo Output: "%cd%\%%f"
)
if "%download_type%"=="4" exit /b
goto END

REM ========== 下载并处理封面 ==========
:DOWNLOAD_THUMBNAIL
echo.
echo Downloading thumbnail...

REM 下载最高质量的缩略图
"%YTDLP%" --cookies "%COOKIES%" ^
  --skip-download ^
  --write-thumbnail ^
  --convert-thumbnails jpg ^
  -o "%%(title)s.%%(ext)s" ^
  "%cleanlink%"

REM 等待文件下载完成
timeout /t 2 /nobreak >nul

REM 查找下载的缩略图
set "thumb_file="
for /f "delims=" %%f in ('dir /b /od *.jpg 2^>nul') do (
    set "thumb_file=%%f"
)

if not defined thumb_file (
    echo.
    echo Error: No thumbnail file found!
    if "%download_type%"=="4" exit /b
    goto END
)

echo.
echo Found thumbnail: !thumb_file!
echo Converting to 4:3 aspect ratio...
echo.

REM 检查 Python 转换器是否存在
if not exist "%THUMB_CONVERTER%" (
    echo Error: Converter script not found: %THUMB_CONVERTER%
    echo Please make sure convert_thumbnail_4x3.py is in the same folder as this batch file.
    pause
    if "%download_type%"=="4" exit /b
    goto END
)

REM 调用 Python 转换器
python "%THUMB_CONVERTER%" "!thumb_file!"

if errorlevel 1 (
    echo.
    echo Error: Conversion failed. Make sure Pillow is installed:
    echo   pip install pillow
    echo.
    pause
)

echo.
echo Thumbnail processing complete!

if "%download_type%"=="4" exit /b
goto END

:END
pause