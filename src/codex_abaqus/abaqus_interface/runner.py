"""Core interface to Abaqus CLI — submit jobs, run Python scripts, query status."""

import subprocess
import json
import tempfile
import time
import os
from pathlib import Path
from typing import Optional

from .config import ABAQUS_COMMAND, SCRATCH_DIR, WORK_DIR, DEFAULT_CPUS, DEFAULT_TIMEOUT


def _run_abaqus(args: list[str], timeout: int = DEFAULT_TIMEOUT, cwd: Optional[Path] = None) -> subprocess.CompletedProcess:
    """Run an Abaqus command and return the completed process."""
    cmd = [ABAQUS_COMMAND] + args
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=str(cwd or WORK_DIR),
    )
    return result


def _run_abaqus_python(script: str, timeout: int = DEFAULT_TIMEOUT) -> subprocess.CompletedProcess:
    """Write a script to a temp file and run it with `abaqus python`."""
    script_path = SCRATCH_DIR / f"_mcp_script_{int(time.time()*1000)}.py"
    script_path.write_text(script, encoding="utf-8")
    try:
        result = _run_abaqus(["python", str(script_path)], timeout=timeout)
        return result
    finally:
        # Clean up temp script
        if script_path.exists():
            script_path.unlink()


def _run_abaqus_cae(script: str, timeout: int = DEFAULT_TIMEOUT) -> subprocess.CompletedProcess:
    """Write a script to a temp file and run it with `abaqus cae noGUI=`."""
    script_path = SCRATCH_DIR / f"_mcp_cae_script_{int(time.time()*1000)}.py"
    script_path.write_text(script, encoding="utf-8")
    try:
        result = _run_abaqus(["cae", f"noGUI={script_path}"], timeout=timeout)
        return result
    finally:
        if script_path.exists():
            script_path.unlink()


# --- Job Operations ---

def submit_job(
    input_file: str,
    job_name: Optional[str] = None,
    cpus: int = DEFAULT_CPUS,
    double: bool = False,
    user_subroutine: Optional[str] = None,
    wait: bool = True,
    timeout: int = DEFAULT_TIMEOUT,
) -> dict:
    """Submit an Abaqus analysis job.

    Args:
        input_file: Path to the .inp input file (absolute or relative to work dir).
        job_name: Job name (defaults to input file stem).
        cpus: Number of CPUs to use.
        double: Use double precision.
        user_subroutine: Path to user subroutine file (Fortran .f/.for).
        wait: Wait for job completion before returning.
        timeout: Maximum wait time in seconds.

    Returns:
        dict with job_name, status, and output paths.
    """
    inp_path = Path(input_file)
    if not inp_path.is_absolute():
        inp_path = WORK_DIR / inp_path

    if not inp_path.exists():
        return {"error": f"Input file not found: {inp_path}"}

    job = job_name or inp_path.stem
    args = [f"job={job}", f"input={inp_path}"]
    args.append(f"cpus={cpus}")
    if double:
        args.append("double")
    if user_subroutine:
        args.append(f"user={Path(user_subroutine)}")

    cmd = " ".join(args)

    if wait:
        # Interactive mode — waits for completion
        result = _run_abaqus(["job=" + job, f"input={inp_path}", f"cpus={cpus}"] + 
                            (["double"] if double else []) +
                            ([f"user={user_subroutine}"] if user_subroutine else []) +
                            ["interactive"],
                            timeout=timeout)
    else:
        result = _run_abaqus([f"job={job}", f"input={inp_path}", f"cpus={cpus}"] +
                            (["double"] if double else []) +
                            ([f"user={user_subroutine}"] if user_subroutine else []),
                            timeout=timeout)

    # Gather output file paths
    output_files = {
        "odb": str(inp_path.with_suffix(".odb")),
        "dat": str(inp_path.with_suffix(".dat")),
        "msg": str(inp_path.with_suffix(".msg")),
        "sta": str(inp_path.with_suffix(".sta")),
        "log": str(inp_path.with_suffix(".log")),
    }
    # Filter to files that actually exist
    output_files = {k: v for k, v in output_files.items() if Path(v).exists()}

    return {
        "job_name": job,
        "return_code": result.returncode,
        "stdout": result.stdout[-5000:] if result.stdout else "",
        "stderr": result.stderr[-2000:] if result.stderr else "",
        "output_files": output_files,
        "status": "completed" if result.returncode == 0 else "failed",
        "elapsed_seconds": None,  # can parse from .sta
    }


def check_job_status(job_name: str) -> dict:
    """Check the status of an Abaqus job by reading its .sta and .log files."""
    sta_path = WORK_DIR / f"{job_name}.sta"
    log_path = WORK_DIR / f"{job_name}.log"
    msg_path = WORK_DIR / f"{job_name}.msg"
    odb_path = WORK_DIR / f"{job_name}.odb"

    status = "unknown"
    errors = []
    warnings = []

    # Check log file for errors
    if log_path.exists():
        log_text = log_path.read_text(encoding="utf-8", errors="replace")
        if "ABAQUS JOB COMPLETED" in log_text:
            status = "completed"
        elif "ABAQUS ERROR" in log_text:
            status = "error"
            # Extract error lines
            for line in log_text.splitlines():
                if "ERROR" in line.upper():
                    errors.append(line.strip())
        elif "ABAQUS JOB ABORTED" in log_text:
            status = "aborted"

    # Check .msg for warnings
    if msg_path.exists():
        msg_text = msg_path.read_text(encoding="utf-8", errors="replace")
        for line in msg_text.splitlines():
            if "WARNING" in line.upper():
                warnings.append(line.strip())

    # Check .sta for progress
    progress = None
    if sta_path.exists():
        sta_text = sta_path.read_text(encoding="utf-8", errors="replace")
        lines = sta_text.strip().splitlines()
        if lines:
            progress = lines[-1].strip()

    return {
        "job_name": job_name,
        "status": status,
        "odb_exists": odb_path.exists(),
        "odb_path": str(odb_path) if odb_path.exists() else None,
        "progress": progress,
        "errors": errors[-10:] if errors else [],
        "warnings": warnings[-10:] if warnings else [],
    }
