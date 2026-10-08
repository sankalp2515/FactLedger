param([Parameter(Mandatory=$true)][string]$Destination, [ValidatePattern('^[a-z0-9][a-z0-9_-]*$')][string]$ComposeProject = 'evidence-workspace')
$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path $PSScriptRoot -Parent
$composePath = Join-Path $repoRoot 'infra/compose.yml'
$targetPath = [System.IO.Path]::GetFullPath($Destination)
if (Test-Path -LiteralPath $targetPath) { throw 'Destination must be a new backup directory.' }
New-Item -ItemType Directory -Path $targetPath | Out-Null
function Invoke-Docker { & docker @args; if ($LASTEXITCODE -ne 0) { throw 'Docker backup command failed; backup is incomplete.' } }
$apiId = & docker compose -p $ComposeProject -f $composePath ps -q api
if (-not $apiId) { throw 'Start the local stack before backup.' }
$pgId = & docker compose -p $ComposeProject -f $composePath ps -q postgres
Invoke-Docker compose -p $ComposeProject -f $composePath stop api worker
try {
    Invoke-Docker exec $pgId pg_dump -U evidence -d evidence -Fc -f /tmp/evidence-backup.dump
    Invoke-Docker cp "${pgId}:/tmp/evidence-backup.dump" (Join-Path $targetPath 'database.dump')
    Invoke-Docker cp "${apiId}:/data" (Join-Path $targetPath 'data')
    $ledgerPath = Join-Path $targetPath 'data/deletion-ledger.jsonl'
    if (Test-Path -LiteralPath $ledgerPath) {
        $independentPath = Join-Path $repoRoot '.data/deletion-ledger-history'
        New-Item -ItemType Directory -Force -Path $independentPath | Out-Null
        Copy-Item -LiteralPath $ledgerPath -Destination (Join-Path $independentPath ((Get-Date -Format 'yyyyMMddHHmmss') + '.jsonl'))
    }
    $manifest = @(Get-ChildItem -LiteralPath $targetPath -File -Recurse | ForEach-Object {
        [PSCustomObject]@{ Path = $_.FullName.Substring($targetPath.Length + 1); Hash = (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash }
    })
    ConvertTo-Json -InputObject $manifest | Set-Content (Join-Path $targetPath 'checksums.json')
} finally {
    Invoke-Docker compose -p $ComposeProject -f $composePath start api worker
}
Write-Output "Backup written to $targetPath. Preserve the deletion ledger independently through backup expiry."
