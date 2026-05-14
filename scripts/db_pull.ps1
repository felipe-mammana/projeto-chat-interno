param(
    [string]$EnvFile = ".env.dbpull",
    [string]$OutDir = "db_backups",
    [switch]$Import
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Set-EnvFromFile([string]$Path) {
    if (-not (Test-Path $Path)) {
        return
    }

    Get-Content $Path | ForEach-Object {
        $line = $_.Trim()
        if (-not $line) { return }
        if ($line.StartsWith("#")) { return }

        $parts = $line.Split("=", 2)
        if ($parts.Count -ne 2) { return }

        $key = $parts[0].Trim()
        $value = $parts[1].Trim()
        if ($value.StartsWith('"') -and $value.EndsWith('"')) {
            $value = $value.Substring(1, $value.Length - 2)
        }
        if ($value.StartsWith("'") -and $value.EndsWith("'")) {
            $value = $value.Substring(1, $value.Length - 2)
        }

        if ($key) {
            $env:$key = $value
        }
    }
}

Set-EnvFromFile $EnvFile

$remoteHost = $env:REMOTE_DB_HOST
$remotePort = $env:REMOTE_DB_PORT
$remoteUser = $env:REMOTE_DB_USER
$remotePass = $env:REMOTE_DB_PASSWORD
$remoteName = $env:REMOTE_DB_NAME

if (-not $remoteHost -or -not $remoteUser -or -not $remoteName) {
    throw "Defina REMOTE_DB_HOST, REMOTE_DB_USER e REMOTE_DB_NAME (via $EnvFile ou variáveis de ambiente)."
}

if (-not $remotePort) { $remotePort = "3306" }

if (-not (Get-Command mysqldump -ErrorAction SilentlyContinue)) {
    throw "mysqldump não encontrado. Instale o MySQL Client e tente novamente."
}

if (-not (Test-Path $OutDir)) {
    New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
}

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$dumpFile = Join-Path $OutDir "clinica_$timestamp.sql"

$dumpArgs = @(
    "-h", $remoteHost,
    "-P", $remotePort,
    "-u", $remoteUser,
    "--single-transaction",
    "--routines",
    "--triggers",
    "--events",
    $remoteName
)

if ($remotePass) {
    $env:MYSQL_PWD = $remotePass
}

Write-Host "Gerando dump em $dumpFile ..."
& mysqldump @dumpArgs | Set-Content -Encoding utf8 $dumpFile

if (-not $Import) {
    Write-Host "Dump concluído. Para importar localmente, rode: .\\scripts\\db_pull.ps1 -Import"
    return
}

$localHost = $env:LOCAL_DB_HOST
$localPort = $env:LOCAL_DB_PORT
$localUser = $env:LOCAL_DB_USER
$localPass = $env:LOCAL_DB_PASSWORD
$localName = $env:LOCAL_DB_NAME

if (-not $localHost) { $localHost = "127.0.0.1" }
if (-not $localPort) { $localPort = "3306" }
if (-not $localUser) { $localUser = "root" }
if (-not $localName) { $localName = $remoteName }

if (-not (Get-Command mysql -ErrorAction SilentlyContinue)) {
    throw "mysql client não encontrado. Instale o MySQL Client e tente novamente."
}

if ($localPass) {
    $env:MYSQL_PWD = $localPass
} else {
    Remove-Item Env:MYSQL_PWD -ErrorAction SilentlyContinue
}

Write-Host "Criando banco local (se não existir): $localName"
& mysql -h $localHost -P $localPort -u $localUser -e "CREATE DATABASE IF NOT EXISTS \`$localName\` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"

Write-Host "Importando dump no banco local..."
& mysql -h $localHost -P $localPort -u $localUser $localName < $dumpFile

Write-Host "Importação concluída."
