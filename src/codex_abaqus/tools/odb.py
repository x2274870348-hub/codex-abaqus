"""MCP tools for reading Abaqus ODB output databases."""

import json
import os
from pathlib import Path
from typing import Optional

from ..abaqus_interface.runner import _run_abaqus_python
from ..abaqus_interface.config import SCRATCH_DIR

_TEMPLATES_DIR = Path(__file__).parent.parent / "templates"


def _read_template(name: str) -> str:
    """Read a template script file."""
    path = _TEMPLATES_DIR / name
    return path.read_text(encoding="utf-8")


async def read_odb_field(
    odb_path: str,
    field_names: Optional[str] = None,
    step_index: int = 0,
    frame_index: int = -1,
    node_labels: Optional[str] = None,
    element_labels: Optional[str] = None,
    max_per_field: int = 500,
) -> str:
    """Read field output from an Abaqus ODB file.

    Args:
        odb_path: Absolute path to the .odb file.
        field_names: Comma-separated field names (e.g., "S,U,RF"). If empty, lists available fields.
        step_index: 0-based step index.
        frame_index: 0-based frame index, -1 for last frame.
        node_labels: Comma-separated node labels to filter.
        element_labels: Comma-separated element labels to filter.
        max_per_field: Maximum values to return per field.

    Returns:
        JSON string with field output data.
    """
    if not Path(odb_path).exists():
        return json.dumps({"error": f"ODB file not found: {odb_path}"})

    script = _read_template("read_odb_field.py")

    env = os.environ.copy()
    env["ODB_PATH"] = odb_path
    env["FIELD_OUTPUT"] = field_names or ""
    env["STEP_INDEX"] = str(step_index)
    env["FRAME_INDEX"] = str(frame_index)
    env["NODE_LABELS"] = node_labels or ""
    env["ELEMENT_LABELS"] = element_labels or ""
    env["MAX_PER_FIELD"] = str(max_per_field)

    # Write the script to a temp file with env vars prepended
    import time
    script_path = SCRATCH_DIR / f"_mcp_odb_field_{int(time.time() * 1000)}.py"
    script_path.write_text(script, encoding="utf-8")

    # Run with env vars
    import subprocess
    from ..abaqus_interface.config import ABAQUS_COMMAND, DEFAULT_TIMEOUT

    try:
        result = subprocess.run(
            [ABAQUS_COMMAND, "python", str(script_path)],
            capture_output=True, text=True, timeout=DEFAULT_TIMEOUT,
            env=env, cwd=str(SCRATCH_DIR),
        )
        if result.stdout.strip():
            return result.stdout.strip()
        return json.dumps({"error": "No output", "stderr": result.stderr[-2000:]})
    finally:
        if script_path.exists():
            script_path.unlink()


async def read_odb_history(
    odb_path: str,
    history_names: Optional[str] = None,
    step_index: int = 0,
) -> str:
    """Read history output from an Abaqus ODB file.

    Args:
        odb_path: Absolute path to the .odb file.
        history_names: Comma-separated history output names. If empty, lists available.
        step_index: 0-based step index.

    Returns:
        JSON string with history output data.
    """
    if not Path(odb_path).exists():
        return json.dumps({"error": f"ODB file not found: {odb_path}"})

    script = _read_template("read_odb_history.py")

    env = os.environ.copy()
    env["ODB_PATH"] = odb_path
    env["HISTORY_NAMES"] = history_names or ""
    env["STEP_INDEX"] = str(step_index)

    import time
    import subprocess
    from ..abaqus_interface.config import ABAQUS_COMMAND, DEFAULT_TIMEOUT

    script_path = SCRATCH_DIR / f"_mcp_odb_hist_{int(time.time() * 1000)}.py"
    script_path.write_text(script, encoding="utf-8")

    try:
        result = subprocess.run(
            [ABAQUS_COMMAND, "python", str(script_path)],
            capture_output=True, text=True, timeout=DEFAULT_TIMEOUT,
            env=env, cwd=str(SCRATCH_DIR),
        )
        if result.stdout.strip():
            return result.stdout.strip()
        return json.dumps({"error": "No output", "stderr": result.stderr[-2000:]})
    finally:
        if script_path.exists():
            script_path.unlink()


async def list_odb_contents(odb_path: str) -> str:
    """List the contents of an ODB file: steps, frames, field outputs, history.

    Args:
        odb_path: Absolute path to the .odb file.

    Returns:
        JSON string with ODB structure summary.
    """
    if not Path(odb_path).exists():
        return json.dumps({"error": f"ODB file not found: {odb_path}"})

    # Reuse field read with no field filter to get available fields
    return await read_odb_field(odb_path, field_names=None, step_index=0)
