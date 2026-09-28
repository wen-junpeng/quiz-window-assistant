@echo off
setlocal
set "PIP_CACHE_DIR=D:\codex\cache\pip"
set "TEMP=D:\codex\tmp\quiz-window-assistant-demo"
set "TMP=D:\codex\tmp\quiz-window-assistant-demo"
set "APP=D:\codex\venvs\quiz-assistant-demo\Scripts\quiz-window-assistant.exe"

if /I "%~1"=="--check" (
  if exist "%APP%" (
    echo READY
    exit /b 0
  )
  echo NOT_READY
  exit /b 1
)

if not exist "%APP%" (
  echo NOT_INSTALLED. Run scripts\setup-demo.ps1 first.
  pause
  exit /b 1
)

pushd "%~dp0"
start "" "%APP%"
popd
