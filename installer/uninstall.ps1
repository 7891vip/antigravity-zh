# Antigravity 简体中文汉化包 · 还原英文
$ErrorActionPreference = 'Stop'
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch {}

Write-Host ''
Write-Host '==============================================' -ForegroundColor Cyan
Write-Host '  还原 Antigravity 官方英文界面' -ForegroundColor Cyan
Write-Host '==============================================' -ForegroundColor Cyan
Write-Host ''

function Find-Antigravity {
    $cands = @(
        (Join-Path $env:LOCALAPPDATA 'Programs\antigravity'),
        (Join-Path $env:ProgramFiles 'Antigravity'),
        (Join-Path ${env:ProgramFiles(x86)} 'Antigravity')
    )
    foreach ($c in $cands) {
        if ($c -and (Test-Path (Join-Path $c 'resources\app.asar'))) { return $c }
    }
    return $null
}

$app = Find-Antigravity
if (-not $app) {
    $app = Read-Host '请粘贴 Antigravity 安装目录（其中包含 Antigravity.exe）'
    $app = $app.Trim('"').TrimEnd('\')
}

$asar = Join-Path $app 'resources\app.asar'
$backup = Join-Path $app 'resources\app.asar.zh-backup'

if (-not (Test-Path $backup)) {
    Write-Host '[错误] 没有找到官方原版备份 app.asar.zh-backup，无法还原。' -ForegroundColor Red
    Write-Host '       如已卸载重装，当前应已是英文界面。' -ForegroundColor Yellow
    Read-Host '按回车退出'
    exit 1
}

$procs = Get-Process Antigravity -ErrorAction SilentlyContinue
if ($procs) {
    Write-Host '正在关闭 Antigravity…' -ForegroundColor Yellow
    $procs | Stop-Process -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
}

Copy-Item $backup $asar -Force
Write-Host '已还原官方原版文件。' -ForegroundColor Green
if (Test-Path env:ELECTRON_RUN_AS_NODE) { Remove-Item env:ELECTRON_RUN_AS_NODE -ErrorAction SilentlyContinue }
Start-Process -FilePath (Join-Path $app 'Antigravity.exe') -WorkingDirectory $app
Start-Sleep -Seconds 2
Write-Host '完成。' -ForegroundColor Green
Write-Host ''
Read-Host '按回车退出'
