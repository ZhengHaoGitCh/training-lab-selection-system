# 开发环境启动管理（Windows PowerShell 5.1）
[CmdletBinding()]
param(
    [ValidateSet('start', 'stop', 'restart', 'status')]
    [string]$Action = 'start',

    [ValidateSet('all', 'backend', 'frontend')]
    [string]$Target = 'all',

    [switch]$OpenBrowser
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$runDir = Join-Path $root '.run'
$logDir = Join-Path $root 'logs'
$python = Join-Path $root '.venv\Scripts\python.exe'
$frontendDir = Join-Path $root 'frontend'
$viteEntry = Join-Path $frontendDir 'node_modules\vite\bin\vite.js'
$backendUrl = 'http://127.0.0.1:8000'
$frontendUrl = 'http://127.0.0.1:5173'
$backendPort = 8000
$frontendPort = 5173

function Write-Step([string]$Message) {
    Write-Host "[dev] $Message" -ForegroundColor Cyan
}

function Write-Ok([string]$Message) {
    Write-Host "[dev] $Message" -ForegroundColor Green
}

function Write-Warn([string]$Message) {
    Write-Host "[dev] $Message" -ForegroundColor Yellow
}

function Ensure-Directories {
    foreach ($dir in @($runDir, $logDir)) {
        if (-not (Test-Path $dir)) {
            New-Item -ItemType Directory -Force -Path $dir | Out-Null
        }
    }
}

function Get-PortOwner([int]$Port) {
    try {
        $connection = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction Stop |
            Select-Object -First 1
        if ($connection) {
            return [int]$connection.OwningProcess
        }
    } catch {
        $lines = & netstat.exe -ano | Select-String -Pattern ":$Port\s+.*LISTENING"
        foreach ($line in $lines) {
            $parts = $line.ToString().Trim() -split '\s+'
            if ($parts.Length -ge 5) {
                return [int]$parts[-1]
            }
        }
    }
    return $null
}

function Get-ProcessCommandLine([int]$ProcessId) {
    try {
        $info = Get-CimInstance Win32_Process -Filter "ProcessId=$ProcessId" -ErrorAction Stop
        if ($info) {
            return [string]$info.CommandLine
        }
    } catch {
        return ''
    }
    return ''
}

function Test-ProjectProcess([int]$ProcessId, [string]$Kind) {
    if (-not $ProcessId) {
        return $false
    }
    if (-not (Get-Process -Id $ProcessId -ErrorAction SilentlyContinue)) {
        return $false
    }
    $commandLine = Get-ProcessCommandLine $ProcessId
    if (-not $commandLine) {
        return $false
    }
    $escapedRoot = [regex]::Escape($root)
    if ($Kind -eq 'backend') {
        return ($commandLine -match 'uvicorn') -and ($commandLine -match $escapedRoot)
    }
    if ($Kind -eq 'frontend') {
        return ($commandLine -match 'vite') -and ($commandLine -match $escapedRoot)
    }
    return $false
}

function Get-TrackedPid([string]$Name) {
    $pidFile = Join-Path $runDir "$Name.pid"
    if (-not (Test-Path $pidFile)) {
        return $null
    }
    try {
        return [int]((Get-Content -Path $pidFile -Raw).Trim())
    } catch {
        return $null
    }
}

function Wait-HttpReady([string]$Url, [int]$TimeoutSeconds = 30) {
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        try {
            $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 2
            if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 400) {
                return $true
            }
        } catch {
            Start-Sleep -Milliseconds 500
        }
    }
    return $false
}

function Show-LogTail([string]$Path, [int]$Lines = 20) {
    if (Test-Path $Path) {
        Write-Warn "最近日志 $Path"
        Get-Content -Path $Path -Tail $Lines -ErrorAction SilentlyContinue |
            ForEach-Object { Write-Host "  $_" }
    }
}

function Stop-ServiceByName([string]$Name, [int]$Port, [string]$Kind) {
    $trackedPid = Get-TrackedPid $Name
    $ownerPid = Get-PortOwner $Port
    $targetPid = $null

    if ($trackedPid -and (Test-ProjectProcess $trackedPid $Kind)) {
        $targetPid = $trackedPid
    } elseif ($ownerPid -and (Test-ProjectProcess $ownerPid $Kind)) {
        $targetPid = $ownerPid
    }

    if ($targetPid) {
        Write-Step "停止 $Name (PID $targetPid)"
        & taskkill.exe /PID $targetPid /T /F | Out-Null
        for ($i = 0; $i -lt 20; $i++) {
            if (-not (Get-PortOwner $Port)) {
                break
            }
            Start-Sleep -Milliseconds 250
        }
    } else {
        Write-Warn "$Name 未运行或不是本项目进程，跳过"
    }

    $pidFile = Join-Path $runDir "$Name.pid"
    if (Test-Path $pidFile) {
        Remove-Item -Path $pidFile -Force -ErrorAction SilentlyContinue
    }

    $remainingPid = Get-PortOwner $Port
    if ($remainingPid) {
        Write-Warn "端口 $Port 仍被 PID $remainingPid 占用"
    } else {
        Write-Ok "$Name 已停止，端口 $Port 已释放"
    }
}

function Start-Backend {
    Ensure-Directories
    $ownerPid = Get-PortOwner $backendPort
    if ($ownerPid) {
        if (Test-ProjectProcess $ownerPid 'backend') {
            Write-Warn "后端已在运行 (PID $ownerPid)"
            return $false
        }
        throw "端口 $backendPort 被其他进程占用 (PID $ownerPid)"
    }
    if (-not (Test-Path $python)) {
        throw "未找到 .venv。请先运行: uv venv --python 3.12 .venv; uv pip install -r backend\requirements.txt"
    }

    $pidFile = Join-Path $runDir 'backend.pid'
    if (Test-Path $pidFile) {
        Remove-Item -Path $pidFile -Force -ErrorAction SilentlyContinue
    }

    $stdout = Join-Path $logDir 'backend.out.log'
    $stderr = Join-Path $logDir 'backend.err.log'
    $arguments = @(
        '-m', 'uvicorn', 'app.main:app',
        '--app-dir', (Join-Path $root 'backend'),
        '--reload',
        '--host', '127.0.0.1',
        '--port', "$backendPort"
    )
    Write-Step "启动后端 $backendUrl"
    $process = Start-Process -FilePath $python -ArgumentList $arguments `
        -WorkingDirectory $root -WindowStyle Hidden -PassThru `
        -RedirectStandardOutput $stdout -RedirectStandardError $stderr
    Set-Content -Path $pidFile -Value $process.Id -Encoding ASCII

    if (-not (Wait-HttpReady "$backendUrl/health" 30)) {
        Show-LogTail $stderr
        Show-LogTail $stdout
        Stop-ServiceByName 'backend' $backendPort 'backend'
        throw '后端启动失败，请检查日志'
    }
    Write-Ok "后端就绪 $backendUrl/docs"
    return $true
}

function Start-Frontend {
    Ensure-Directories
    $ownerPid = Get-PortOwner $frontendPort
    if ($ownerPid) {
        if (Test-ProjectProcess $ownerPid 'frontend') {
            Write-Warn "前端已在运行 (PID $ownerPid)"
            return $false
        }
        throw "端口 $frontendPort 被其他进程占用 (PID $ownerPid)"
    }
    if (-not (Test-Path $viteEntry)) {
        throw "未找到前端依赖。请先运行: cd frontend; npm install"
    }
    $node = Join-Path $env:ProgramFiles 'nodejs\node.exe'
    if (-not (Test-Path $node)) {
        $nodeCommand = Get-Command node.exe -ErrorAction SilentlyContinue
        if (-not $nodeCommand) {
            throw '未找到 node.exe，请安装 Node.js 或把 C:\Program Files\nodejs 加入 PATH'
        }
        $node = $nodeCommand.Source
    }

    $pidFile = Join-Path $runDir 'frontend.pid'
    if (Test-Path $pidFile) {
        Remove-Item -Path $pidFile -Force -ErrorAction SilentlyContinue
    }

    $stdout = Join-Path $logDir 'frontend.out.log'
    $stderr = Join-Path $logDir 'frontend.err.log'
    $arguments = @(
        $viteEntry,
        '--host', '127.0.0.1',
        '--port', "$frontendPort",
        '--strictPort'
    )
    Write-Step "启动前端 $frontendUrl"
    $process = Start-Process -FilePath $node -ArgumentList $arguments `
        -WorkingDirectory $frontendDir -WindowStyle Hidden -PassThru `
        -RedirectStandardOutput $stdout -RedirectStandardError $stderr
    Set-Content -Path $pidFile -Value $process.Id -Encoding ASCII

    if (-not (Wait-HttpReady $frontendUrl 30)) {
        Show-LogTail $stderr
        Show-LogTail $stdout
        Stop-ServiceByName 'frontend' $frontendPort 'frontend'
        throw '前端启动失败，请检查日志'
    }
    Write-Ok "前端就绪 $frontendUrl"
    return $true
}

function Start-Selected {
    $startedBackend = $false
    if ($Target -eq 'all' -or $Target -eq 'backend') {
        $startedBackend = Start-Backend
    }
    if ($Target -eq 'all' -or $Target -eq 'frontend') {
        try {
            Start-Frontend | Out-Null
        } catch {
            if ($startedBackend) {
                Stop-ServiceByName 'backend' $backendPort 'backend'
            }
            throw
        }
    }
    if ($OpenBrowser -and ($Target -eq 'all' -or $Target -eq 'frontend')) {
        Start-Process $frontendUrl
    }
    Write-Ok '启动完成；停止请运行 .\dev.cmd stop'
    if ($Target -eq 'all' -or $Target -eq 'backend') {
        Write-Host "  后端: $backendUrl/docs"
    }
    if ($Target -eq 'all' -or $Target -eq 'frontend') {
        Write-Host "  前端: $frontendUrl"
    }
    Write-Host "  日志: $logDir"
}

function Show-Status {
    if ($Target -eq 'all' -or $Target -eq 'backend') {
        $ownerPid = Get-PortOwner $backendPort
        $trackedPid = Get-TrackedPid 'backend'
        if ($ownerPid) {
            $kind = if (Test-ProjectProcess $ownerPid 'backend') { '本项目' } else { '其他进程' }
            $health = 'unavailable'
            try {
                $health = (Invoke-WebRequest -Uri "$backendUrl/health" -UseBasicParsing -TimeoutSec 2).StatusCode
            } catch {
                $health = 'unavailable'
            }
            Write-Host "后端: 运行中  PID $ownerPid  端口 $backendPort  $kind  health=$health"
        } elseif ($trackedPid) {
            Write-Warn "后端: 未运行，但存在陈旧 PID 文件 ($trackedPid)"
        } else {
            Write-Host '后端: 未运行'
        }
    }

    if ($Target -eq 'all' -or $Target -eq 'frontend') {
        $ownerPid = Get-PortOwner $frontendPort
        $trackedPid = Get-TrackedPid 'frontend'
        if ($ownerPid) {
            $kind = if (Test-ProjectProcess $ownerPid 'frontend') { '本项目' } else { '其他进程' }
            $httpStatus = 'unavailable'
            try {
                $httpStatus = (Invoke-WebRequest -Uri $frontendUrl -UseBasicParsing -TimeoutSec 2).StatusCode
            } catch {
                $httpStatus = 'unavailable'
            }
            Write-Host "前端: 运行中  PID $ownerPid  端口 $frontendPort  $kind  http=$httpStatus"
        } elseif ($trackedPid) {
            Write-Warn "前端: 未运行，但存在陈旧 PID 文件 ($trackedPid)"
        } else {
            Write-Host '前端: 未运行'
        }
    }

    Write-Host "日志目录: $logDir"
    Write-Host "PID 目录: $runDir"
}

try {
    Ensure-Directories
    switch ($Action) {
        'start' {
            Start-Selected
        }
        'stop' {
            if ($Target -eq 'all' -or $Target -eq 'frontend') {
                Stop-ServiceByName 'frontend' $frontendPort 'frontend'
            }
            if ($Target -eq 'all' -or $Target -eq 'backend') {
                Stop-ServiceByName 'backend' $backendPort 'backend'
            }
        }
        'restart' {
            if ($Target -eq 'all' -or $Target -eq 'frontend') {
                Stop-ServiceByName 'frontend' $frontendPort 'frontend'
            }
            if ($Target -eq 'all' -or $Target -eq 'backend') {
                Stop-ServiceByName 'backend' $backendPort 'backend'
            }
            Start-Sleep -Seconds 1
            Start-Selected
        }
        'status' {
            Show-Status
        }
    }
} catch {
    Write-Host "[dev] 失败: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
