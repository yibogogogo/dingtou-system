@echo off
chcp 65001 >nul
title 量化定投择时系统 v2.1
echo ========================================
echo   量化定投择时系统 v2.1
echo ========================================
echo.
echo   正在启动Web服务...
echo.

cd /d "%~dp0"
python run_app.py

pause
