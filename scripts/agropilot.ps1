# Atalho Windows para o CLI cross-platform (scripts/agropilot.py).
#
#   powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\agropilot.ps1
#   powershell ... -File .\scripts\agropilot.ps1 doctor
#   powershell ... -File .\scripts\agropilot.ps1 -Stop     (alias de down)
#
# O CLI em Python substituiu a logica que morava aqui (instalar por SO,
# restaurar seed, subir/derrubar processos). Duplicar essa regra em duas
# linguagens foi o que fez os dois scripts divergirem; agora este arquivo so
# acha o interpretador certo e repassa o comando.
#
# O Python vem antes do PATH no Windows, e `py -3` falha com codigo 9009 se o
# launcher da Microsoft nao estiver instalado - por isso a busca explicita.
[CmdletBinding()]
param(
    [Parameter(Position = 0)]
    [string]$Comando = 'tudo',
    [switch]$Stop,
    [switch]$Status,
    [switch]$Setup,
    [switch]$Seed,
    [switch]$Force
)

$ErrorActionPreference = 'Stop'

# Atalhos com nome de PowerShell -> comandos do CLI.
if ($Stop)   { $Comando = 'down' }
if ($Status) { $Comando = 'status' }
if ($Setup)  { $Comando = 'setup' }
if ($Seed)   { $Comando = 'seed' }

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

function Find-Python {
    foreach ($cand in @('python', 'python3', 'py')) {
        $cmd = Get-Command $cand -ErrorAction SilentlyContinue
        if (-not $cmd) { continue }
        try {
            $v = & $cmd.Source -c 'import sys;print(sys.version_info[0])' 2>$null
            if ($LASTEXITCODE -eq 0 -and [int]$v -ge 3) { return $cmd.Source }
        } catch { continue }
    }
    return $null
}

$py = Find-Python
if (-not $py) {
    Write-Host '[agropilot] ERRO: Python 3.11+ nao encontrado no PATH.' -ForegroundColor Red
    Write-Host '  Instale: winget install --id Python.Python.3.12'
    Write-Host '  Docs    : https://www.python.org/downloads/'
    exit 1
}

$cliArgs = @((Join-Path $ScriptDir 'agropilot.py'), $Comando)
if ($Force) { $cliArgs += '--force' }

& $py @cliArgs
exit $LASTEXITCODE