"""MCP tools for executing arbitrary Abaqus Python scripts."""

import json
import time

from ..abaqus_interface.runner import _run_abaqus_python
from ..abaqus_interface.config import SCRATCH_DIR, DEFAULT_TIMEOUT


async def abaqus_run_python(
    script: str,
    timeout: int = DEFAULT_TIMEOUT,
) -> str:
    """Execute an arbitrary Python script using the Abaqus Python interpreter.

    The script runs via `abaqus python`, which gives access to Abaqus-specific
    modules like odbAccess, abaqusConstants, etc. (but NOT the full CAE API).
    For full CAE API access, use abaqus_run_modeling instead.

    Args:
        script: Python script to execute.
        timeout: Timeout in seconds.

    Returns:
        JSON string with stdout, stderr, and return code.
    """
    result = _run_abaqus_python(script, timeout=timeout)

    return json.dumps({
        "return_code": result.returncode,
        "stdout": result.stdout[-5000:] if result.stdout else "",
        "stderr": result.stderr[-2000:] if result.stderr else "",
        "status": "completed" if result.returncode == 0 else "failed",
    }, default=str)
