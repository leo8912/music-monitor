@echo off
REM ===========================================================================
REM  music-monitor one-click launcher (Windows)
REM  Double-click = dev mode; or run from cmd with -Prod for single-process
REM ===========================================================================
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_dev.ps1" %*
pause
