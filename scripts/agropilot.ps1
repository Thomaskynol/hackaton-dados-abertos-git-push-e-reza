# Sobe o AgroPilot inteiro no Windows sem Docker: instala o que falta, popula o
# banco e deixa a API (8000) e o front (3000) rodando em background.
# Idempotente: pode rodar varias vezes sem quebrar nada.
# Uso:
#   powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\agropilot.ps1
#   ... -Setup    # so instala o que falta e popula o banco
#   ... -Seed     # forca o mongorestore mesmo com o banco ja cheio
#   ... -Status   # mostra o que esta de pe
#   ... -Stop     # mata a API e o front que este script subiu
[CmdletBinding()]
param(
    [switch]$Setup,
    [switch]$Seed,
    [switch]$Stop,
    [switch]$Status
)

$ErrorActionPreference = 'Stop'

# --- caminhos / constantes ---
$RepoRoot    = Split-Path -Parent $PSScriptRoot
$BackDir     = Join-Path $RepoRoot 'back'
$FrontDir    = Join-Path $RepoRoot 'front'
$SeedDir     = Join-Path $RepoRoot 'seed'
$SeedArchive = Join-Path $SeedDir 'agropilot.gz'
$ReleaseRepo = 'Thomaskynol/hackaton-dados-abertos-sql-injection'
$ReleaseUrl  = 'https://github.com/Thomaskynol/hackaton-dados-abertos-sql-injection/releases/download/data/agropilot.gz'

$MongoService = 'MongoDB'
$MongoPort    = 27017

$ApiUrl   = 'http://127.0.0.1:8000'
$FrontUrl = 'http://localhost:3000'

# logs e PIDs ficam no TEMP: nao cria pasta nova no repo
$ApiLog        = Join-Path $env:TEMP 'agropilot-api.log'
$ApiErrLog     = Join-Path $env:TEMP 'agropilot-api.err.log'
$FrontLog      = Join-Path $env:TEMP 'agropilot-front.log'
$FrontErrLog   = Join-Path $env:TEMP 'agropilot-front.err.log'
$ApiPidFile    = Join-Path $env:TEMP 'agropilot-api.pid'
$FrontPidFile  = Join-Path $env:TEMP 'agropilot-front.pid'

# --- funcoes auxiliares ---
function Say($msg) { Write-Host "[agropilot] $msg" }
function Aviso($msg) { Write-Host "[agropilot] AVISO: $msg" -ForegroundColor Yellow }
function Die($msg) { Write-Host "[agropilot] ERRO: $msg" -ForegroundColor Red; exit 1 }

# roda binario nativo tolerando stderr (mongosh/mongorestore escrevem aviso ali)
function Invoke-Quiet($exe, $argv) {
    $ErrorActionPreference = 'Continue'
    return (& $exe @argv 2>&1 | Out-String)
}

# o instalador do MongoDB/mongosh nao atualiza o PATH da sessao atual:
# rele de Machine + User no processo para o Get-Command enxergar os .exe novos
function Update-SessionPath {
    $parts = @()
    $machine = [System.Environment]::GetEnvironmentVariable('Path', 'Machine')
    $user = [System.Environment]::GetEnvironmentVariable('Path', 'User')
    if ($machine) { $parts += $machine }
    if ($user) { $parts += $user }
    if ($parts.Count -eq 0) { return }
    [System.Environment]::SetEnvironmentVariable('Path', ($parts -join ';'), 'Process')
}

# procura no PATH e, se nao achar, nos diretorios padrao do instalador MongoDB
function Resolve-Tool($name, $extraDirs) {
    $cmd = Get-Command $name -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    foreach ($dir in $extraDirs) {
        if (-not $dir) { continue }
        # -Recurse: o instalador põe em Tools\<versao>\bin, nao na raiz
        $hit = Get-ChildItem -Path $dir -Filter "$name.exe" -Recurse -ErrorAction SilentlyContinue |
               Select-Object -First 1
        if ($hit) { return $hit.FullName }
    }
    return $null
}

# winget ja pula o que esta instalado; so chamamos quando algo falta
function Install-Winget($id, $rotulo) {
    Say "instalando $rotulo (winget install --id $id) ..."
    Invoke-Quiet 'winget' @('install', '--id', $id, '--source', 'winget',
                             '--accept-source-agreements', '--accept-package-agreements', '--silent') | Out-Null
    Update-SessionPath
}

# npm e um .cmd; o cmd.exe do front tambem precisa acha-lo no PATH
function Resolve-Npm {
    $cmd = Get-Command 'npm.cmd' -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    return 'npm.cmd'
}

function Test-Port($port) {
    $client = New-Object System.Net.Sockets.TcpClient
    try {
        $task = $client.BeginConnect('127.0.0.1', $port, $null, $null)
        if (-not $task.AsyncWaitHandle.WaitOne(500)) { return $false }
        $client.EndConnect($task)
        return $true
    } catch {
        return $false
    } finally {
        $client.Close()
    }
}

function Wait-Port($port, $timeoutSec) {
    $deadline = (Get-Date).AddSeconds($timeoutSec)
    while ((Get-Date) -lt $deadline) {
        if (Test-Port $port) { return $true }
        Start-Sleep -Milliseconds 700
    }
    return $false
}

function Test-Url($url) {
    try {
        Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 3 | Out-Null
        return $true
    } catch {
        return $false
    }
}

function Wait-Url($url, $timeoutSec) {
    $deadline = (Get-Date).AddSeconds($timeoutSec)
    while ((Get-Date) -lt $deadline) {
        if (Test-Url $url) { return $true }
        Start-Sleep -Milliseconds 700
    }
    return $false
}

# true se o venv ja tem as dependencias minimas (evita reinstall desnecessario)
function Test-Imports($python) {
    $ErrorActionPreference = 'Continue'
    & $python -c 'import fastapi, uvicorn, pymongo' 2>&1 | Out-Null
    return ($LASTEXITCODE -eq 0)
}

# documentos no banco agropilot (0 se a base ainda nao existir)
# aspas simples no JS porque o PowerShell 5.1 remove as duplas ao pasar para .exe
function Get-AgroCount($mongosh) {
    if (-not $mongosh) { return 0 }
    $js = "try { print('COUNT=' + Number(db.getSiblingDB('agropilot').stats().objects)) } catch (e) { print('COUNT=0') }"
    $out = Invoke-Quiet $mongosh @('--quiet', '--eval', $js)
    $hit = [regex]::Match($out, '(?m)^COUNT=(\d+)\s*$')
    if ($hit.Success) { return [int]$hit.Groups[1].Value }
    return 0
}

# le o PID salvo antes; devolve $null se nao houver
function Get-SavedPid($file) {
    if (-not (Test-Path -LiteralPath $file)) { return $null }
    $line = Get-Content -LiteralPath $file -ErrorAction SilentlyContinue | Select-Object -First 1
    if (-not $line) { return $null }
    $num = 0
    if ([int]::TryParse($line.Trim(), [ref]$num)) { return $num }
    return $null
}

function Test-ProcAlive($procId) {
    if (-not $procId) { return $false }
    return ($null -ne (Get-Process -Id $procId -ErrorAction SilentlyContinue))
}

function Get-MongoService {
    return (Get-Service -Name $MongoService -ErrorAction SilentlyContinue)
}

# --- seed ---
function Invoke-Seed($force) {
    $count = Get-AgroCount $script:mongosh
    if ((-not $force) -and ($count -gt 0)) {
        Say "agropilot ja tem $count documentos; seed ignorado"
        return
    }
    if (-not $script:mongorestore) {
        Aviso 'mongorestore ausente (winget install --id MongoDB.DatabaseTools); seed pulado'
        return
    }
    if (-not (Test-Path -LiteralPath $SeedArchive)) {
        New-Item -ItemType Directory -Path $SeedDir -Force | Out-Null
        $gh = Get-Command 'gh' -ErrorAction SilentlyContinue
        if ($gh) {
            Say 'baixando o dump da release data (gh release download) ...'
            Invoke-Quiet $gh.Source @('release', 'download', 'data', '--repo', $ReleaseRepo,
                                      '--pattern', 'agropilot.gz', '--dir', $SeedDir) | Out-Null
        } else {
            Aviso 'GitHub CLI (gh) nao encontrado no PATH'
        }
    }
    if (-not (Test-Path -LiteralPath $SeedArchive)) {
        Aviso "dump ausente. A release e privada: baixe manualmente $ReleaseUrl"
        Aviso "e salve o arquivo em $SeedArchive; depois rode: powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\agropilot.ps1 -Seed"
        return
    }
    Say 'restaurando seed\agropilot.gz com mongorestore (pode demorar) ...'
    Invoke-Quiet $script:mongorestore @('--gzip', "--archive=$SeedArchive", '--drop') | Out-Null
    $novo = Get-AgroCount $script:mongosh
    if ($novo -gt 0) {
        Say "agropilot populado ($novo documentos)"
    } else {
        Aviso 'mongorestore rodou, mas a contagem de documentos continua 0'
    }
}

# --- processos ---
function Start-ApiProcess {
    $salvo = Get-SavedPid $ApiPidFile
    if (Test-ProcAlive $salvo) {
        Say "API ja esta no ar (pid $salvo)"
        return
    }
    if (Test-Url "$ApiUrl/api/health") {
        Aviso 'ja ha uma API respondendo em 8000 (fora deste script); nao subindo outra'
        return
    }
    Say 'subindo a API em 127.0.0.1:8000 ...'
    $proc = Start-Process -FilePath $VenvPython `
        -ArgumentList @('-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', '8000') `
        -WorkingDirectory $BackDir `
        -RedirectStandardOutput $ApiLog `
        -RedirectStandardError $ApiErrLog `
        -WindowStyle Hidden -PassThru
    # uvicorn morre na hora se a 8000 estiver ocupada por outro processo
    if ($proc.HasExited) { Die "a API morreu ao subir (porta 8000 ocupada?). Log: $ApiErrLog" }
    Set-Content -LiteralPath $ApiPidFile -Value $proc.Id
    if (Wait-Url "$ApiUrl/api/health" 90) {
        Say 'API respondendo em /api/health'
    } else {
        Aviso "API nao respondeu /api/health em 90s. Log: $ApiErrLog"
    }
}

function Start-FrontProcess {
    $salvo = Get-SavedPid $FrontPidFile
    if (Test-ProcAlive $salvo) {
        Say "front ja esta no ar (pid $salvo)"
        return
    }
    if (Test-Url $FrontUrl) {
        Aviso 'ja ha algo respondendo em 3000 (fora deste script); nao subindo outro front'
        return
    }
    Say 'subindo o front em 3000 (npm run dev) ...'
    # via cmd.exe porque npm e um .cmd e nao roda direto no Start-Process com redirect
    $proc = Start-Process -FilePath 'cmd.exe' `
        -ArgumentList @('/c', 'npm run dev') `
        -WorkingDirectory $FrontDir `
        -RedirectStandardOutput $FrontLog `
        -RedirectStandardError $FrontErrLog `
        -WindowStyle Hidden -PassThru
    Set-Content -LiteralPath $FrontPidFile -Value $proc.Id
    if (Wait-Url $FrontUrl 120) {
        Say 'front respondendo'
    } else {
        Aviso "front nao respondeu em 120s. Log: $FrontLog"
    }
}

function Stop-SavedProcess($rotulo, $file) {
    $salvo = Get-SavedPid $file
    if (-not $salvo) {
        Say "$rotulo : nenhum PID salvo em $file"
        return
    }
    if (-not (Test-ProcAlive $salvo)) {
        Say "$rotulo : processo $salvo ja encerrado"
        Remove-Item -LiteralPath $file -Force -ErrorAction SilentlyContinue
        return
    }
    Say "parando $rotulo (pid $salvo) ..."
    # /T derruba o node/npm filho do cmd.exe
    Invoke-Quiet 'taskkill' @('/PID', $salvo, '/T', '/F') | Out-Null
    Remove-Item -LiteralPath $file -Force -ErrorAction SilentlyContinue
}

# --- relatorios ---
function Show-Status {
    Write-Host ''
    Say 'status:'
    $svc = Get-MongoService
    if (-not $svc) {
        Write-Host "  MongoDB : servico ausente (rode o script sem -Status para instalar)"
    } elseif (Test-Port $MongoPort) {
        Write-Host "  MongoDB : $($svc.Status), porta $MongoPort aberta"
    } else {
        Write-Host "  MongoDB : $($svc.Status), porta $MongoPort fechada"
    }

    if (Test-Url "$ApiUrl/api/health") {
        $apiPid = Get-SavedPid $ApiPidFile
        Write-Host "  API     : no ar em $ApiUrl/api/health (pid salvo: $apiPid)"
    } else {
        Write-Host "  API     : fora do ar em $ApiUrl/api/health"
    }

    if (Test-Port 3000) {
        $frontPid = Get-SavedPid $FrontPidFile
        Write-Host "  front   : no ar em $FrontUrl (pid salvo: $frontPid)"
    } else {
        Write-Host "  front   : fora do ar na porta 3000"
    }

    $shell = Resolve-Tool 'mongosh' @("$env:LOCALAPPDATA\Programs\mongosh", "$env:ProgramFiles\mongodb\mongodb shell")
    if ($shell) {
        Write-Host "  banco   : agropilot com $(Get-AgroCount $shell) documentos"
    } else {
        Write-Host '  banco   : mongosh ausente, nao da para contar os documentos'
    }
    Write-Host ''
}

function Show-Summary {
    Write-Host ''
    Say 'pronto:'
    Write-Host '  front    : http://localhost:3000'
    Write-Host '  swagger  : http://localhost:8000/docs'
    Write-Host '  health   : http://localhost:8000/api/health'
    Write-Host ''
    Write-Host "logs api   : $ApiLog  (stderr: $ApiErrLog)"
    Write-Host "logs front : $FrontLog  (stderr: $FrontErrLog)"
    Write-Host "pids       : $ApiPidFile | $FrontPidFile"
    Write-Host 'parar tudo: powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\agropilot.ps1 -Stop'
}

# --- -Stop / -Status saem antes de qualquer instalacao ---
if ($Stop) {
    Stop-SavedProcess 'API' $ApiPidFile
    Stop-SavedProcess 'front' $FrontPidFile
    Say 'processos deste script parados (o servico MongoDB continua no ar)'
    exit 0
}
if ($Status) {
    Show-Status
    exit 0
}

# =========================== FASE 1: instalar o que falta ===========================
Say 'fase 1: dependencias'

# MongoDB server (servico Windows)
$svc = Get-MongoService
if (-not $svc) {
    Install-Winget 'MongoDB.Server' 'MongoDB Server'
    $svc = Get-MongoService
    if (-not $svc) {
        Die "servico Windows '$MongoService' nao apareceu. Instale com: winget install --id MongoDB.Server e rode o script de novo"
    }
}
if ($svc.Status -ne 'Running') {
    Say 'iniciando o servico MongoDB ...'
    try {
        Start-Service -Name $MongoService
    } catch {
        Die "nao deu para iniciar o servico '$MongoService'. Rode o PowerShell como Administrador"
    }
}
if (-not (Wait-Port $MongoPort 60)) {
    Die "porta $MongoPort nao respondeu em 60s (MongoDB parado?)"
}
Say "MongoDB ok (porta $MongoPort)"

# mongosh (contagem do banco) e mongorestore (restaurar o dump)
$script:mongosh = Resolve-Tool 'mongosh' @("$env:LOCALAPPDATA\Programs\mongosh", "$env:ProgramFiles\mongodb\mongodb shell")
if (-not $script:mongosh) {
    Install-Winget 'MongoDB.Shell' 'mongosh'
    $script:mongosh = Resolve-Tool 'mongosh' @("$env:LOCALAPPDATA\Programs\mongosh", "$env:ProgramFiles\mongodb\mongodb shell")
}
$script:mongorestore = Resolve-Tool 'mongorestore' @("$env:ProgramFiles\MongoDB\Tools", "${env:ProgramFiles(x86)}\MongoDB\Tools")
if (-not $script:mongorestore) {
    Install-Winget 'MongoDB.DatabaseTools' 'MongoDB Database Tools'
    $script:mongorestore = Resolve-Tool 'mongorestore' @("$env:ProgramFiles\MongoDB\Tools", "${env:ProgramFiles(x86)}\MongoDB\Tools")
}
if (-not $script:mongosh) { Aviso 'mongosh nao encontrado: a contagem do banco vai ficar indisponivel' }
if (-not $script:mongorestore) { Aviso 'mongorestore nao encontrado: o seed automatico vai ser pulado' }

# venv + requirements do backend
$VenvPython  = Join-Path $BackDir '.venv\Scripts\python.exe'
$Requirements = Join-Path $BackDir 'requirements.txt'
if (-not (Test-Path -LiteralPath $VenvPython)) {
    $py = Get-Command 'python' -ErrorAction SilentlyContinue
    if (-not $py) { Die 'python nao encontrado no PATH (instale Python 3.12+)' }
    Say 'criando back\.venv ...'
    Invoke-Quiet 'python' @('-m', 'venv', (Join-Path $BackDir '.venv')) | Out-Null
    if (-not (Test-Path -LiteralPath $VenvPython)) { Die 'falha ao criar o venv (instale Python 3.12+)' }
}
if (-not (Test-Imports $VenvPython)) {
    Say 'instalando back\requirements.txt ...'
    Invoke-Quiet $VenvPython @('-m', 'pip', 'install', '-r', $Requirements) | Out-Null
}
if (-not (Test-Imports $VenvPython)) {
    Die 'venv sem fastapi/uvicorn/pymongo (rode: back\.venv\Scripts\python -m pip install -r back\requirements.txt)'
}
Say 'venv ok (fastapi/uvicorn/pymongo)'

# node_modules do front
$NodeModules = Join-Path $FrontDir 'node_modules'
if (-not (Test-Path -LiteralPath $NodeModules)) {
    Say 'node_modules ausente; rodando npm install em front ...'
    $npm = Resolve-Npm
    Push-Location $FrontDir
    Invoke-Quiet $npm @('install') | Out-Null
    Pop-Location
    if (-not (Test-Path -LiteralPath $NodeModules)) { Die 'npm install falhou em front\' }
}
Say 'front ok (node_modules)'

# seed do banco agropilot
Invoke-Seed ([bool]$Seed)

if ($Setup) {
    Say 'setup concluido (-Setup): nada foi iniciado em background'
    exit 0
}

# =========================== FASE 2: subir API e front ===========================
Say 'fase 2: subindo a aplicacao'
Start-ApiProcess
Start-FrontProcess
Show-Summary