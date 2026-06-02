"""MCP tools for Abaqus job submission and status checking."""

import json
from typing import Optional

from ..abaqus_interface.runner import submit_job, check_job_status


async def abaqus_submit_job(
    input_file: str,
    job_name: Optional[str] = None,
    cpus: int = 4,
    double: bool = False,
    user_subroutine: Optional[str] = None,
    wait: bool = False,
    timeout: int = 3600,
) -> str:
    """Submit an Abaqus analysis job.

    Args:
        input_file: Path to the .inp input file.
        job_name: Optional job name (defaults to input file stem).
        cpus: Number of CPUs.
        double: Use double precision if True.
        user_subroutine: Path to Fortran user subroutine file.
        wait: If True, wait for job completion.
        timeout: Timeout in seconds.

    Returns:
        JSON string with job submission result.
    """
    result = submit_job(
        input_file=input_file,
        job_name=job_name,
        cpus=cpus,
        double=double,
        user_subroutine=user_subroutine,
        wait=wait,
        timeout=timeout,
    )
    return json.dumps(result, default=str)


async def abaqus_job_status(job_name: str) -> str:
    """Check the status of a submitted Abaqus job.

    Args:
        job_name: Name of the job to check.

    Returns:
        JSON string with job status information.
    """
    result = check_job_status(job_name)
    return json.dumps(result, default=str)
