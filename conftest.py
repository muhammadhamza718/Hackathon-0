"""
Pytest configuration and fixtures.

Sets up Python path to allow imports from agents/skills/managing-obsidian-vault
"""

import sys
from pathlib import Path

# Add the managing-obsidian-vault skill directory to Python path
skill_path = Path(__file__).parent / "agents" / "skills" / "managing-obsidian-vault"
if str(skill_path) not in sys.path:
    sys.path.insert(0, str(skill_path))
