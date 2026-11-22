@echo off
chcp 65001 >nul
title Antigravity Chinese Pack Installer
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1"
