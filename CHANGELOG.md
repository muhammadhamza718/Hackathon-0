# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [Unreleased]

## [0.3.0] - 2026-03-02

### Added
- Audit logger with append-only log files
- Inbox scanner with priority extraction
- Task templates for simple and HITL tasks
- Frontmatter parser and builder
- Complexity detector with scoring
- Sentinel health checker
- Custom exception hierarchy
- Vault initializer module

---

## [0.2.0] - 2026-02-01

### Added
- Silver Tier: autonomous plan creation (`/Plans/PLAN-*.md`)
- Reconciliation-first startup for session resumption
- HITL approval gate with `/Pending_Approval/` routing
- Reasoning logs with ISO-8601 timestamps

### Changed
- Upgraded vault manager to support Silver Tier plan files

---

## [0.1.0] - 2026-01-01

### Added
- Bronze Tier: Obsidian Vault-based AI Employee
- Inbox triage with `/Inbox/`, `/Needs_Action/`, `/Done/` routing
- Sentinel file system watcher
- Vault manager agent
- Dashboard.md auto-update
- Audit logging
