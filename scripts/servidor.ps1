# Mantém o Chatbot Tutor no ar neste PC, independente de qualquer terminal ou sessão.
#
#   powershell -File mvp\scripts\servidor.ps1 iniciar        # app (Uvicorn) + túnel público (Cloudflare)
#   powershell -File mvp\scripts\servidor.ps1 reiniciar-app  # após mudar código: o link público continua o mesmo
#   powershell -File mvp\scripts\servidor.ps1 status         # link público e se está respondendo
#   powershell -File mvp\scripts\servidor.ps1 vigiar         # religa o que caiu (usado pela tarefa agendada)
#   powershell -File mvp\scripts\servidor.ps1 parar
#
# Os processos são criados pelo WMI (Win32_Process), sem janela e fora da árvore do terminal que chamou.
# O link do túnel rápido muda toda vez que o túnel reinicia (não ao reiniciar só o app); o atual fica
# em mvp\.servidor\link.txt, e cada religada do vigia fica em mvp\logs\vigia.log.
param([Parameter(Position = 0)][ValidateSet("iniciar", "parar", "reiniciar-app", "status", "vigiar")][string]$Acao = "status")

$ErrorActionPreference = "Stop"
$Mvp = Split-Path -Parent $PSScriptRoot
$Estado = Join-Path $Mvp ".servidor"
$Logs = Join-Path $Mvp "logs"
$Uvicorn = Join-Path $Mvp ".venv\Scripts\uvicorn.exe"
$Python = Join-Path $Mvp ".venv\Scripts\python.exe"
$Cloudflared = Join-Path $env:USERPROFILE "ferramentas\cloudflared\cloudflared.exe"
$Porta = 8765
New-Item -ItemType Directory -Force $Estado, $Logs | Out-Null

function Iniciar-Processo([string]$Nome, [string]$Comando) {
    # Sem janela (ShowWindow = 0): fechar uma janela por engano derrubava o site.
    $inicio = New-CimInstance -ClassName Win32_ProcessStartup -ClientOnly -Property @{ ShowWindow = [uint16]0 }
    $r = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{
        # Aspas extras em volta de tudo: o cmd /c tira o primeiro e o último par de aspas.
        CommandLine = "cmd.exe /c `"$Comando`""; CurrentDirectory = $Mvp; ProcessStartupInformation = $inicio
    }
    if ($r.ReturnValue -ne 0) { throw "falha ao iniciar $Nome (código $($r.ReturnValue))" }
    Set-Content -Path (Join-Path $Estado "$Nome.pid") -Value $r.ProcessId -Encoding ascii
    Write-Output "$Nome iniciado (PID $($r.ProcessId))"
}

function Parar-Processo([string]$Nome) {
    $arquivo = Join-Path $Estado "$Nome.pid"
    if (-not (Test-Path $arquivo)) { return }
    $processoId = Get-Content $arquivo
    # /T encerra o cmd.exe e o processo filho (uvicorn ou cloudflared) que ele abriu.
    & cmd.exe /c "taskkill /PID $processoId /T /F >nul 2>&1"
    Remove-Item $arquivo -Force
    Write-Output "$Nome parado"
}

function Link-Publico {
    $log = Join-Path $Logs "tunel.log"
    if (-not (Test-Path $log)) { return $null }
    $m = Select-String -Path $log -Pattern "https://[a-z0-9-]+\.trycloudflare\.com" | Select-Object -Last 1
    if ($m) { return $m.Matches[0].Value } else { return $null }
}

function Responde([string]$Url) {
    try { return (Invoke-WebRequest -UseBasicParsing "$Url/entrar/" -TimeoutSec 20).StatusCode -eq 200 } catch { return $false }
}

function Vivo([string]$Nome) {
    $arquivo = Join-Path $Estado "$Nome.pid"
    if (-not (Test-Path $arquivo)) { return $false }
    return [bool](Get-Process -Id (Get-Content $arquivo) -ErrorAction SilentlyContinue)
}

function Iniciar-App {
    & $Python (Join-Path $Mvp "manage.py") collectstatic --noinput -v0
    Iniciar-Processo "app" "`"$Uvicorn`" config.asgi:application --host 127.0.0.1 --port $Porta --proxy-headers >> `"$Logs\uvicorn.log`" 2>&1"
}

function Iniciar-Tunel {
    Remove-Item (Join-Path $Logs "tunel.log") -ErrorAction SilentlyContinue
    Iniciar-Processo "tunel" "`"$Cloudflared`" tunnel --no-autoupdate --url http://127.0.0.1:$Porta > `"$Logs\tunel.log`" 2>&1"
    for ($i = 0; $i -lt 30 -and -not (Link-Publico); $i++) { Start-Sleep -Seconds 1 }
    $link = Link-Publico
    if ($link) { Set-Content -Path (Join-Path $Estado "link.txt") -Value $link -Encoding utf8 }
    Write-Output "link público: $link"
}

switch ($Acao) {
    "iniciar" { Iniciar-App; Iniciar-Tunel }
    "reiniciar-app" { Parar-Processo "app"; Start-Sleep -Seconds 1; Iniciar-App }
    "parar" { Parar-Processo "tunel"; Parar-Processo "app" }
    "status" {
        $link = Link-Publico
        try { $local = (Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:$Porta/entrar/" -TimeoutSec 10).StatusCode } catch { $local = "fora do ar" }
        Write-Output "app local: $local"
        Write-Output "link público: $link"
    }
    "vigiar" {
        # Tarefa agendada (a cada 10 min e no logon): religa o que caiu e registra em logs\vigia.log.
        $registro = Join-Path $Logs "vigia.log"
        $agora = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
        if (-not (Responde "http://127.0.0.1:$Porta")) {
            Parar-Processo "app" | Out-Null
            Iniciar-App | Out-Null
            Start-Sleep -Seconds 8
            Add-Content $registro "$agora app fora do ar: religado" -Encoding utf8
        }
        $link = Link-Publico
        if (-not (Vivo "tunel") -or -not $link -or -not (Responde $link)) {
            Start-Sleep -Seconds 20   # uma falha de rede passageira não deve trocar o link
            $link = Link-Publico
            if (-not (Vivo "tunel") -or -not $link -or -not (Responde $link)) {
                Parar-Processo "tunel" | Out-Null
                $saida = Iniciar-Tunel
                Add-Content $registro "$agora tunel fora do ar: religado, $($saida | Select-Object -Last 1)" -Encoding utf8
            }
        }
    }
}
