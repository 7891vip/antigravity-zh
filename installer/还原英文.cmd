@echo off
chcp 65001 >nul
title Antigravity Chinese Pack Uninstaller
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0uninstall.ps1"
