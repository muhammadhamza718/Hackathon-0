# Contract: Odoo Health Monitor

## Skill

`odoo-health-monitor`

## Purpose

Protect the cloud Odoo path through HTTPS-only access, operational checks, and draft-only accounting preparation.

## Inputs

- Odoo service URL behind HTTPS
- Cloud low-privilege credential set
- Backup status source
- Event triggers requiring accounting review

## Interface

### `heartbeat() -> OdooHeartbeat`
Runs a lightweight authenticated JSON-RPC health check.

### `verify_backup_status() -> BackupStatus`
Reports latest backup and restore-verification health.

### `prepare_draft(event) -> AccountingDraft`
Creates a local-approval-ready accounting package from a business event.

## Guarantees

- Cloud only performs read and draft-safe operations
- Health is visible to Local through heartbeat records
- Final accounting mutation remains Local-only
