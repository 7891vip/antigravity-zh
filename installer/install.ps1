# Antigravity 简体中文汉化包 · 安装脚本
# 用法：双击“安装汉化.cmd”，或在 PowerShell 中执行本脚本。
$ErrorActionPreference = 'Stop'
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch {}

$here = Split-Path -Parent $MyInvocation.MyCommand.Path

# 兼容两种布局：脚本与 app.zh.asar 同级（Release 包），或脚本在 installer/、文件在 dist/
$root = $null
foreach ($c in @($here, (Join-Path $here 'dist'), (Join-Path $here '..\dist'))) {
    if ($c -and (Test-Path (Join-Path $c 'app.zh.asar')) -and (Test-Path (Join-Path $c 'manifest.json'))) {
        $root = (Resolve-Path $c).Path
        break
    }
}

Write-Host ''
Write-Host '==============================================' -ForegroundColor Cyan
Write-Host '  Antigravity 简体中文汉化包  v1.0' -ForegroundColor Cyan
Write-Host '==============================================' -ForegroundColor Cyan
Write-Host ''

if (-not $root) {
    Write-Host '[错误] 未找到 app.zh.asar / manifest.json。' -ForegroundColor Red
    Write-Host '       请保留完整目录结构：installer\ 与 dist\ 需在同一级。' -ForegroundColor Yellow
    Read-Host '按回车退出'
    exit 1
}
$packAsar = Join-Path $root 'app.zh.asar'
$manifest = Get-Content (Join-Path $root 'manifest.json') -Raw -Encoding UTF8 | ConvertFrom-Json

function Find-Antigravity {
    $cands = @(
        (Join-Path $env:LOCALAPPDATA 'Programs\antigravity'),
        (Join-Path $env:ProgramFiles 'Antigravity'),
        (Join-Path ${env:ProgramFiles(x86)} 'Antigravity')
    )
    foreach ($c in $cands) {
        if ($c -and (Test-Path (Join-Path $c 'resources\app.asar'))) { return $c }
    }
    $keys = @(
        'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*',
        'HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*',
        'HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*'
    )
    foreach ($k in $keys) {
        $items = Get-ItemProperty $k -ErrorAction SilentlyContinue |
            Where-Object { $_.DisplayName -and $_.DisplayName -like '*Antigravity*' }
        foreach ($it in $items) {
            if ($it.InstallLocation) {
                $p = $it.InstallLocation.TrimEnd('\')
                if (Test-Path (Join-Path $p 'resources\app.asar')) { return $p }
            }
        }
    }
    return $null
}

$app = Find-Antigravity
if (-not $app) {
    Write-Host '[提示] 未自动找到 Antigravity 安装目录。' -ForegroundColor Yellow
    $app = Read-Host '请粘贴安装目录（其中包含 Antigravity.exe），直接回车退出'
    $app = $app.Trim('"').TrimEnd('\')
    if (-not $app -or -not (Test-Path (Join-Path $app 'resources\app.asar'))) {
        Write-Host '[错误] 该目录下没有 resources\app.asar。' -ForegroundColor Red
        Read-Host '按回车退出'
        exit 1
    }
}

$asar = Join-Path $app 'resources\app.asar'
$backup = Join-Path $app 'resources\app.asar.zh-backup'
Write-Host ("安装目录：" + $app)
Write-Host ("核心文件：" + $asar)
Write-Host ("汉化包  ：" + $packAsar)
Write-Host ''

# 关闭正在运行的客户端
$procs = Get-Process Antigravity -ErrorAction SilentlyContinue
if ($procs) {
    Write-Host '正在关闭 Antigravity（安装需要写入 app.asar）…' -ForegroundColor Yellow
    $procs | Stop-Process -Force -ErrorAction SilentlyContinue
    for ($i = 0; $i -lt 20; $i++) {
        Start-Sleep -Milliseconds 500
        if (-not (Get-Process Antigravity -ErrorAction SilentlyContinue)) { break }
    }
    Start-Sleep -Milliseconds 500
}

$curHash = (Get-FileHash $asar -Algorithm SHA256).Hash.ToLower()
$already = ($curHash -eq $manifest.packAsarSha256.ToLower())
$isOfficial = ($curHash -eq $manifest.sourceAsarSha256.ToLower())

if ($already) {
    Write-Host '检测到已经安装过汉化包，直接启动。' -ForegroundColor Green
}
else {
    if (-not $isOfficial) {
        Write-Host '[提示] 当前 app.asar 与制作汉化包时的官方版本不一致（客户端可能已升级）。' -ForegroundColor Yellow
        Write-Host '       汉化仍会生效，但新版本新增的英文文案可能未被翻译。' -ForegroundColor Yellow
        $ans = Read-Host '仍要继续安装吗？(Y/N)'
        if ($ans -notmatch '^[Yy]') { Write-Host '已取消。'; Read-Host '按回车退出'; exit 0 }
    }
    if (-not (Test-Path $backup)) {
        Copy-Item $asar $backup -Force
        Write-Host ("已备份官方原版 → " + $backup) -ForegroundColor Green
    }
    Copy-Item $packAsar $asar -Force
    Write-Host '汉化包已写入。' -ForegroundColor Green
}

Write-Host '正在启动 Antigravity…'
# 某些终端（如 Electron 系 IDE）会带 ELECTRON_RUN_AS_NODE，会导致客户端以 Node 模式启动后立即退出
if (Test-Path env:ELECTRON_RUN_AS_NODE) { Remove-Item env:ELECTRON_RUN_AS_NODE -ErrorAction SilentlyContinue }
Start-Process -FilePath (Join-Path $app 'Antigravity.exe') -WorkingDirectory $app
Start-Sleep -Seconds 2
Write-Host ''
Write-Host '完成！界面应已切换为简体中文。' -ForegroundColor Green
Write-Host '如需还原英文，双击“还原英文.cmd”。'
Write-Host '客户端自动更新后若变回英文，重新运行一次“安装汉化.cmd”即可。'
Write-Host ''
Read-Host '按回车退出'
