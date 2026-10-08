# Backup and restore

Backups contain confidential case data, preserved documents, and editorial notes. Store outside the repository with restricted access and encryption provided by the deployment. A backup is not verified until a restore exercise passes. Expire backup payloads within 30 days; retain the independently current deletion ledger at least through the lifetime of every backup it may protect.

## Backup

`./scripts/backup.ps1 -Destination 'E:/PrivateBackups/evidence-20261008'` requires the running stack and a new directory. It stops API/worker for a consistent database/artifact snapshot, writes PostgreSQL custom-format dump plus private `/data` files and SHA256 manifest, then restarts services even on failure. An incomplete directory must never be promoted to a verified backup. The ledger is also copied into `.data/deletion-ledger-history` independently of the snapshot. Production must preserve this ledger after each deletion, not only during backups: mirror append-only ledger records to a durable independent store, and verify monotonic completeness before accepting deletes. Local backup copies alone do not guarantee survival of host loss.

## Restore into an isolated environment

1. Keep API/worker offline and use a disposable isolated database/volume first. Verify every manifest hash against the saved files and the migration/application version.
2. Locate the independently latest complete deletion ledger. It must contain every deletion since the backup, not the stale ledger bundled in that backup. If completeness is uncertain, keep service offline.
3. Run `./scripts/restore.ps1 -Backup 'E:/PrivateBackups/evidence-20261008' -CurrentDeletionLedger 'E:/Independent/deletion-ledger.jsonl'`. This explicitly replaces the stack's database with the backup, copies artifacts, writes the current ledger, reapplies tenant/case tombstones and cancels nonterminal runs while advancing their fence generation. It intentionally leaves API/worker stopped.
4. Verify deleted cases and their source/export downloads remain inaccessible; review database head, artifact hashes, approved-pack reproduction and run checkpoints. Purge due deleted artifacts before exposing restored service. Restoring files cannot authorize access; each download still checks current case state.
5. Run migrations if upgrading, then `docker compose -f infra/compose.yml start api worker`. Check readiness and create/read a fixture case. Record restore duration, backup timestamp, latest ledger timestamp/count, application revision, and verification outcomes. An isolated synthetic drill passed on 8 October 2026: an older active-case snapshot restored with the later deletion ledger retained its hashes and denied case/source/export downloads. This does not establish production disaster recovery capacity or RPO/RTO.

Never restore over a running writer. The script targets this explicitly selected local Compose stack; do not point it at an unreviewed production context. Backup payload expiry and independent ledger retention require deployment automation outside this local stack.

Both scripts accept `-ComposeProject` to target an explicitly named isolated Compose project; default is `evidence-workspace`. APP_PORT and DB_PORT can select unused loopback ports for a restore drill. Restored `/data` ownership is repaired to UID/GID10001 before tombstone replay so the nonroot application can continue appending the ledger. Replay preserves ledger event order, including authorized restoration events, cancels previously active runs and never restores PURGED cases.
