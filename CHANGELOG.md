# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [1.0.0-gold] - 2026-03-08

### Gold Tier Features - Complete Implementation

#### Social Media Management (Commits 9-13)
- **Hashtag & Emoji Support**: Suggestion engine with keyword matching, emoji optimization per platform
- **Image Optimization**: Validation, compression, EXIF stripping, platform-specific limits
- **Analytics Aggregation**: WoW/MoM trend analysis, engagement metrics, top-performing posts
- **Browser MCP Automation**: Posting scripts for X, Facebook, Instagram with session handling
- **Comprehensive Testing**: 34+ test cases covering all social media modules

#### CEO Briefing Engine (Commits 14-17)
- **Revenue Trend Analysis**: Week-over-week and month-over-month comparisons
- **Visual Indicators**: Trend emojis (🟢🟡⚪🟠🔴) for quick status assessment
- **Subscription Tracking**: Usage monitoring, login date checks, savings calculations
- **Bottleneck Escalation**: Age-based priority increases, notification system
- **Customizable Templates**: Service, Product, and Freelance business templates

#### Ralph Wiggum Loop (Commits 18-20)
- **Progress Tracking**: Iteration reporting, step completion percentages, time estimates
- **Smart Backoff**: Exponential backoff for HITL-blocked tasks (1s to 300s)
- **State Visualization**: Text-based state diagrams with blocked plan highlighting

#### Documentation (Commits 21-24)
- **README Update**: Gold Tier features section, architecture overview
- **CONTRIBUTING.md**: Development workflow, code standards, PR templates
- **API Documentation**: Module docstrings, usage examples, type hints
- **Deployment Guide**: Local, cloud (Oracle/AWS), Docker setups, security hardening

### Added
- `agents/gold/image_optimizer.py`: Image validation and compression module
- `agents/gold/social_automation.py`: Browser MCP automation scripts
- `agents/gold/briefing_templates.py`: Customizable briefing templates
- `LoopProgress` dataclass for iteration tracking
- `_escalate_priority()` method for age-based escalation
- `_track_subscription_usage()` for login date monitoring
- `render_state_diagram()` for loop visualization
- `generate_briefing_with_trends()` for markdown output

### Changed
- Enhanced `SocialBridge.draft_post()` with image optimization options
- Updated `CEOBriefingEngine` with trend analysis integration
- Improved `AutonomousLoop` with progress tracking and smart backoff

### Security
- All social posts route through `/Pending_Approval/`
- Financial actions > $100 require HITL approval
- EXIF data stripping for privacy compliance
- Credential redaction in audit logs

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
