@echo off
rem 编译单文件汉化工具 exe（需要 Windows 自带的 .NET Framework 4.x 编译器，无需安装 SDK）
setlocal
cd /d "%~dp0"

set CSC=%WINDIR%\Microsoft.NET\Framework64\v4.0.30319\csc.exe
if not exist "%CSC%" set CSC=%WINDIR%\Microsoft.NET\Framework\v4.0.30319\csc.exe
if not exist "%CSC%" (
  echo [error] 找不到 csc.exe，请确认已安装 .NET Framework 4.x
  exit /b 1
)

echo [1/4] 生成图标
python make_icon.py || (
  echo [error] 生成图标失败（需要 Python + Pillow）
  exit /b 1
)

echo [2/4] 复制内嵌载荷
copy /Y "..\..\dist\app.zh.asar" payload.asar >nul || exit /b 1
copy /Y "..\..\dist\manifest.json" manifest.json >nul || exit /b 1

echo [3/4] 编译
"%CSC%" /nologo /target:winexe /platform:anycpu /optimize+ /codepage:65001 ^
  /win32icon:app.ico ^
  /win32manifest:app.manifest ^
  /resource:payload.asar,payload.asar ^
  /resource:manifest.json,manifest.json ^
  /r:System.Windows.Forms.dll /r:System.Drawing.dll ^
  /out:Antigravity-ZH-Installer.exe Installer.cs
if errorlevel 1 exit /b 1

echo [4/4] 完成
dir /b Antigravity-ZH-Installer.exe
endlocal
