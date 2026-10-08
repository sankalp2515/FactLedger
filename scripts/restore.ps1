param([Parameter(Mandatory=$true)][string]$Backup, [Parameter(Mandatory=$true)][string]$CurrentDeletionLedger, [ValidatePattern('^[a-z0-9][a-z0-9_-]*$')][string]$ComposeProject = 'evidence-workspace')
$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path $PSScriptRoot -Parent
$composePath = Join-Path $repoRoot 'infra/compose.yml'
$backupPath = [System.IO.Path]::GetFullPath($Backup)
$ledgerPath = [System.IO.Path]::GetFullPath($CurrentDeletionLedger)
if (-not (Test-Path -LiteralPath $ledgerPath -PathType Leaf)) { throw 'An independently current ledger is required. Do not use the old backup ledger.' }
if (-not (Test-Path -LiteralPath (Join-Path $backupPath 'database.dump'))) { throw 'Backup database missing.' }
$manifestPath = Join-Path $backupPath 'checksums.json'
if (-not (Test-Path -LiteralPath $manifestPath)) { throw 'Backup checksum manifest missing.' }
foreach ($entry in (Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json)) {
    $itemPath = [System.IO.Path]::GetFullPath((Join-Path $backupPath $entry.Path))
    if (-not $itemPath.StartsWith($backupPath + [System.IO.Path]::DirectorySeparatorChar, [System.StringComparison]::OrdinalIgnoreCase)) { throw 'Manifest path escapes backup directory.' }
    if (-not (Test-Path -LiteralPath $itemPath -PathType Leaf)) { throw 'Backup manifest file missing.' }
    if ((Get-FileHash -LiteralPath $itemPath -Algorithm SHA256).Hash -ne $entry.Hash) { throw 'Backup checksum mismatch; restore aborted.' }
}
function Invoke-Docker { & docker @args; if ($LASTEXITCODE -ne 0) { throw 'Docker restore failed; keep application offline.' } }
Invoke-Docker compose -p $ComposeProject -f $composePath stop api worker
$pgId = & docker compose -p $ComposeProject -f $composePath ps -q postgres
$apiId = & docker compose -p $ComposeProject -f $composePath ps -aq api
Invoke-Docker cp (Join-Path $backupPath 'database.dump') "${pgId}:/tmp/evidence-restore.dump"
Invoke-Docker exec $pgId pg_restore -U evidence -d evidence --clean --if-exists --no-owner --exit-on-error /tmp/evidence-restore.dump
Invoke-Docker cp (Join-Path $backupPath 'data/.') "${apiId}:/data"
Invoke-Docker cp $ledgerPath "${apiId}:/data/deletion-ledger.jsonl"
Invoke-Docker compose -p $ComposeProject -f $composePath run --rm --no-deps --user 0 worker chown -R 10001:10001 /data
Invoke-Docker compose -p $ComposeProject -f $composePath run --rm --no-deps worker python /app/scripts/reapply_deletions.py /data/deletion-ledger.jsonl
Write-Output 'Restore completed with tombstones reapplied. Verify deleted case access, artifact hashes and migrations before docker compose start api worker.'
