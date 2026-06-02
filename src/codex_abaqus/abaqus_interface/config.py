"""Codex-Abaqus MCP Server — configuration."""

import os
import platform
from pathlib import Path

# --- Abaqus command detection ---

def _find_abaqus_command() -> str:
    """Auto-detect Abaqus command. Respects ABAQUS_COMMAND env var if set."""
    env_cmd = os.environ.get("ABAQUS_COMMAND")
    if env_cmd:
        return env_cmd

    # Common install locations on Windows
    candidates = []
    if platform.system() == "Windows":
        for ver in range(2020, 2030):
            candidates.append(Path(f"D:/SIMULIA/EstProducts/{ver}/win_b64/code/bin/abq2023.bat"))
            candidates.append(Path(f"C:/SIMULIA/EstProducts/{ver}/win_b64/code/bin/abq2023.bat"))
        candidates.append(Path("D:/SIMULIA/Commands/abaqus.bat"))
        candidates.append(Path("C:/SIMULIA/Commands/abaqus.bat"))
    else:
        candidates.append(Path("/usr/local/bin/abaqus"))
        candidates.append(Path("/opt/abaqus/Commands/abaqus"))

    for p in candidates:
        if p.exists():
            return str(p)

    # Fallback — assume it''s on PATH
    return "abaqus"


ABAQUS_COMMAND = _find_abaqus_command()

# --- I/O Paths ---

SCRATCH_DIR = Path(os.environ.get("ABAQUS_SCRATCH", os.getcwd())) / ".abaqus_mcp_scratch"
WORK_DIR = Path(os.environ.get("ABAQUS_WORK_DIR", os.getcwd()))

# Ensure scratch exists
SCRATCH_DIR.mkdir(parents=True, exist_ok=True)

# --- Defaults ---

DEFAULT_CPUS = int(os.environ.get("ABAQUS_CPUS", "4"))
DEFAULT_TIMEOUT = int(os.environ.get("ABAQUS_TIMEOUT", "3600"))  # 1 hour
