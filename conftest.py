"""
Pytest configuration and fixtures.

Sets up Python path to allow imports from agents/skills/managing-obsidian-vault
and the sentinel package.
"""

import sys
from pathlib import Path

# Add the managing-obsidian-vault skill directory to Python path
skill_path = Path(__file__).parent / "agents" / "skills" / "managing-obsidian-vault"
if str(skill_path) not in sys.path:
    sys.path.insert(0, str(skill_path))

# Add sentinel src to Python path
sentinel_src = Path(__file__).parent / "sentinel" / "src"
if str(sentinel_src) not in sys.path:
    sys.path.insert(0, str(sentinel_src))

# Add project root for agents package
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
