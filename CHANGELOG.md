# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [Unreleased]

### Added
- Gold Tier: Autonomous Employee with Ralph Wiggum Loop
- Gold Tier: Odoo 19+ JSON-RPC accounting integration
- Gold Tier: Multi-platform social media management (X, Facebook, Instagram)
- Gold Tier: CEO Briefing Engine with revenue analysis and bottleneck detection
- Gold Tier: Resilient executor with exponential backoff and circuit breaker
- Gold Tier: Safety gate with $100 payment threshold and social post gating
- Gold Tier: JSON audit logging with mandatory rationale field
- Pydantic v2 validation for all Gold Tier models
- Centralized configuration module with environment variable overrides
- Loop-specific exceptions (LoopExitError, CheckpointError, StateCorruptionError)

### Changed
- Converted Gold Tier dataclasses to Pydantic v2 models with runtime validation
- Enhanced autonomous loop error handling with specific exception types
- Extracted Gold Tier constants to dedicated config module
- Updated loop resume to create fresh session instead of returning None

### Documentation
- Added Gold Tier architecture documentation with Mermaid diagrams
- Added configuration reference for all Gold Tier settings
- Added security guide for credential handling and HITL safety gates

---

## [0.5.0] - 2026-03-08

### Added
- Gold Tier foundation with autonomous loop and Odoo integration
- Social media bridge with platform adapters
- CEO Briefing Engine for weekly business audits
- Resilient executor with three-layer error handling
- Safety gate for HITL approval workflow
- JSON audit logger with rationale tracking

---

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
