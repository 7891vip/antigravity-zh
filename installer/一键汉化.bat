@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
title Antigravity 一键汉化
cd /d "%~dp0"
color 0F

set "PACK=%~dp0app.zh.asar"
set "HASHFILE=%~dp0pack.sha256"
set "MODE="
if /i "%~1"=="install" set "MODE=install"
if /i "%~1"=="restore" set "MODE=restore"

if not exist "%PACK%" (
    echo [错误] 同目录下缺少 app.zh.asar，请把压缩包完整解压后使用。
    echo.
    pause
    exit /b 1
)

set "APP="
if exist "%LOCALAPPDATA%\Programs\antigravity\resources\app.asar" set "APP=%LOCALAPPDATA%\Programs\antigravity"
if not defined APP if exist "%ProgramFiles%\Antigravity\resources\app.asar" set "APP=%ProgramFiles%\Antigravity"
if not defined APP if exist "C:\Program Files (x86)\Antigravity\resources\app.asar" set "APP=C:\Program Files (x86)\Antigravity"

if not defined APP (
    echo 没有自动找到 Antigravity 安装目录。
    echo.
    set /p "APP=请粘贴安装目录（其中包含 Antigravity.exe），直接回车退出: "
    if not defined APP exit /b 0
    if not exist "!APP!\resources\app.asar" (
        echo.
        echo [错误] 该目录下没有 resources\app.asar
        pause
        exit /b 1
    )
)

set "ASAR=!APP!\resources\app.asar"
set "BAK=!APP!\resources\app.asar.zh-backup"
set "WANT="
if exist "%HASHFILE%" for /f "usebackq delims=" %%A in ("%HASHFILE%") do set "WANT=%%A"

if /i "%MODE%"=="install" goto :install
if /i "%MODE%"=="restore" goto :restore

:menu
cls
call :showstatus
echo.
echo ==================================================
echo   Antigravity 简体中文汉化    v1.0.2
echo ==================================================
echo.
echo    [1] 安装 / 更新汉化
echo    [2] 还原英文（官方原版）
echo    [3] 打开安装目录
echo    [0] 退出
echo.
set "CH="
set /p "CH=请输入序号后回车: "
if not defined CH exit /b 0
set "CH=!CH:~0,1!"
if "!CH!"=="1" goto :install
if "!CH!"=="2" goto :restore
if "!CH!"=="3" goto :open
if "!CH!"=="0" exit /b 0
echo.
echo 输入无效，请重新选择。
ping -n 2 127.0.0.1 >nul
goto :menu

:install
cls
echo 安装目录: !APP!
echo.
call :killapp
if not exist "%BAK%" (
    copy /y "%ASAR%" "%BAK%" >nul
    if errorlevel 1 (
        echo [错误] 备份官方原版失败，已中止。
        if defined MODE exit /b 1
        pause
        goto :menu
    )
    echo [1/3] 已备份官方原版 app.asar.zh-backup
) else (
    echo [1/3] 官方备份已存在，跳过备份
)
copy /y "%PACK%" "%ASAR%" >nul
if errorlevel 1 (
    echo [错误] 写入 app.asar 失败，文件可能被占用。
    if defined MODE exit /b 1
        pause
        goto :menu
)
echo [2/3] 已写入汉化文件
call :gethash "%ASAR%" NOW
if /i "!NOW!"=="!WANT!" (
    echo [3/3] SHA256 校验通过
) else (
    echo [3/3] [警告] 校验值与 pack.sha256 不一致
)
echo.
echo 正在启动 Antigravity...
call :startapp
echo 完成，界面应为简体中文。
if defined MODE exit /b 0
pause
goto :menu

:restore
cls
if not exist "%BAK%" (
    echo [错误] 没有找到官方备份 app.asar.zh-backup，无法还原。
    echo        若是刚重装过客户端，当前本身就是英文界面。
    if defined MODE exit /b 2
        pause
        goto :menu
)
call :killapp
copy /y "%BAK%" "%ASAR%" >nul
if errorlevel 1 (
    echo [错误] 还原失败，文件可能被占用。
    if defined MODE exit /b 1
        pause
        goto :menu
)
echo 已还原官方原版，正在启动 Antigravity...
call :startapp
echo 完成。
if defined MODE exit /b 0
pause
goto :menu

:open
start "" "!APP!"
goto :menu

:showstatus
call :gethash "%ASAR%" CUR
if /i "!CUR!"=="!WANT!" (
    set "STATE=已汉化（中文界面）"
) else (
    set "STATE=官方原版或未知版本（英文界面）"
)
if exist "%BAK%" (set "BAKTXT=已备份") else (set "BAKTXT=未备份")
echo   安装目录 : !APP!
echo   当前状态 : !STATE!
echo   官方备份 : !BAKTXT!
exit /b 0

:startapp
set "TRY=0"
:startloop
tasklist /fi "imagename eq Antigravity.exe" 2>nul | find /i "Antigravity.exe" >nul
if not errorlevel 1 exit /b 0
set /a TRY+=1
if !TRY! gtr 4 exit /b 0
ping -n 5 127.0.0.1 >nul
start "" "!APP!\Antigravity.exe"
ping -n 5 127.0.0.1 >nul
goto :startloop

:killapp
tasklist /fi "imagename eq Antigravity.exe" 2>nul | find /i "Antigravity.exe" >nul
if not errorlevel 1 (
    echo 正在关闭 Antigravity 客户端...
    taskkill /f /im Antigravity.exe >nul 2>&1
    taskkill /f /im language_server.exe >nul 2>&1
    ping -n 5 127.0.0.1 >nul
)
exit /b 0

:gethash
set "H="
for /f "skip=1 delims=" %%A in ('certutil -hashfile "%~1" SHA256 2^>nul') do (
    if not defined H set "H=%%A"
)
set "H=!H: =!"
set "%~2=!H!"
exit /b 0
