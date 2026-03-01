# API Reference

## agents package

### agents.vault_router
| Function | Description |
|----------|-------------|
| `classify_task(content)` | Classify task content as "simple" or "complex" |
| `route_file(file_path, vault_root)` | Route a file from Inbox to appropriate folder |
| `mark_done(file_path, vault_root)` | Move completed task to Done |

### agents.dashboard_writer
| Function | Description |
|----------|-------------|
| `count_files(directory)` | Count .md files in a directory |
| `generate_dashboard(vault_root)` | Generate Dashboard.md markdown string |
| `write_dashboard(vault_root)` | Write Dashboard.md to vault root |

### agents.plan_manager
| Function | Description |
|----------|-------------|
| `next_plan_id(vault_root)` | Generate next PLAN-YYYY-NNN ID |
| `create_plan(vault_root, objective, steps)` | Create a new plan file |
| `update_plan_status(plan_path, new_status)` | Update plan frontmatter status |

### agents.plan_parser
| Function | Description |
|----------|-------------|
| `parse_frontmatter(content)` | Extract frontmatter metadata |
| `parse_steps(content)` | Extract roadmap steps |
| `next_pending_step(steps)` | Find first incomplete step |

### agents.hitl_gate
| Class | Method | Description |
|-------|--------|-------------|
| `HITLGate` | `submit_for_approval(path)` | Submit file for human review |
| | `get_pending()` | List pending approval items |
| | `check_decision(filename)` | Check approval status |

### agents.reconciler
| Function | Description |
|----------|-------------|
| `find_incomplete_plans(vault_root)` | Find plans not yet complete |
| `prioritize_plans(plans)` | Sort by priority (active > blocked > draft) |
| `reconcile(vault_root)` | Run full startup reconciliation |

### agents.inbox_scanner
| Function | Description |
|----------|-------------|
| `scan_inbox(vault_root)` | List inbox files, newest first |
| `extract_priority(content)` | Extract priority from content |
| `prioritize_inbox(vault_root)` | Scan and sort by priority |

### agents.audit_logger
| Function | Description |
|----------|-------------|
| `append_log(vault_root, action, detail)` | Add audit log entry |
| `read_log(vault_root, date)` | Read audit log for a date |

### agents.validators
| Function | Description |
|----------|-------------|
| `is_valid_plan_id(plan_id)` | Validate PLAN-YYYY-NNN format |
| `is_valid_priority(priority)` | Check priority value |
| `is_valid_status(status)` | Check status value |
| `has_frontmatter(content)` | Check for YAML frontmatter |
| `is_safe_filename(name)` | Validate filename safety |
| `validate_vault_structure(vault_root)` | Check required directories |

### agents.vault_init
| Function | Description |
|----------|-------------|
| `init_vault(vault_root)` | Create all vault directories |
| `is_vault_initialized(vault_root)` | Check if vault is ready |

## sentinel package

### sentinel.config
| Class | Description |
|-------|-------------|
| `WatcherConfig` | Dataclass for watcher configuration |

### sentinel.events
| Class | Description |
|-------|-------------|
| `EventType` | Enum: CREATED, MODIFIED, DELETED, MOVED |
| `FileEvent` | Immutable event with type, path, timestamp |

### sentinel.health
| Class | Description |
|-------|-------------|
| `HealthChecker` | Monitor watcher health status |
