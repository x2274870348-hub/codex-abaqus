"""Codex-Abaqus MCP Server.

Bridges Codex AI with Abaqus FEA software via the Model Context Protocol.
Provides tools for job submission, ODB result reading, Python API modeling,
and arbitrary Abaqus script execution.
"""

import mcp.server.stdio
from mcp.server import Server
from mcp.types import Tool, TextContent

from .tools.job import abaqus_submit_job, abaqus_job_status
from .tools.odb import read_odb_field, read_odb_history, list_odb_contents
from .tools.modeling import abaqus_run_modeling
from .tools.scripting import abaqus_run_python

server = Server("codex-abaqus")


@server.list_tools()
async def handle_list_tools() -> list[Tool]:
    return [
        Tool(
            name="abaqus_submit_job",
            description="Submit an Abaqus analysis job from an input file (.inp). Supports multi-CPU, double precision, and Fortran user subroutines. Returns job name and output file paths.",
            inputSchema={
                "type": "object",
                "properties": {
                    "input_file": {"type": "string", "description": "Path to the .inp input file"},
                    "job_name": {"type": "string", "description": "Optional job name (defaults to input file stem)"},
                    "cpus": {"type": "integer", "description": "Number of CPUs (default 4)"},
                    "double": {"type": "boolean", "description": "Use double precision"},
                    "user_subroutine": {"type": "string", "description": "Path to Fortran user subroutine file"},
                    "wait": {"type": "boolean", "description": "Wait for job completion before returning (default false)"},
                    "timeout": {"type": "integer", "description": "Timeout in seconds (default 3600)"},
                },
                "required": ["input_file"],
            },
        ),
        Tool(
            name="abaqus_job_status",
            description="Check the status of an Abaqus job. Reads .sta, .log, and .msg files. Returns status, progress, errors, and warnings.",
            inputSchema={
                "type": "object",
                "properties": {
                    "job_name": {"type": "string", "description": "Name of the job to check"},
                },
                "required": ["job_name"],
            },
        ),
        Tool(
            name="abaqus_read_odb_field",
            description="Read field output (stress, displacement, strain, etc.) from an Abaqus ODB file. Can filter by step, frame, node/element labels. If no field names given, lists all available field outputs.",
            inputSchema={
                "type": "object",
                "properties": {
                    "odb_path": {"type": "string", "description": "Absolute path to the .odb file"},
                    "field_names": {"type": "string", "description": "Comma-separated field names (e.g. 'S,U,RF'). Empty to list available."},
                    "step_index": {"type": "integer", "description": "0-based step index (default 0)"},
                    "frame_index": {"type": "integer", "description": "0-based frame index, -1 for last (default -1)"},
                    "node_labels": {"type": "string", "description": "Comma-separated node labels to filter"},
                    "element_labels": {"type": "string", "description": "Comma-separated element labels to filter"},
                    "max_per_field": {"type": "integer", "description": "Maximum values per field (default 500)"},
                },
                "required": ["odb_path"],
            },
        ),
        Tool(
            name="abaqus_read_odb_history",
            description="Read history output (time-series data at specific nodes/elements) from an Abaqus ODB file. If no history names given, lists all available history outputs.",
            inputSchema={
                "type": "object",
                "properties": {
                    "odb_path": {"type": "string", "description": "Absolute path to the .odb file"},
                    "history_names": {"type": "string", "description": "Comma-separated history output names. Empty to list available."},
                    "step_index": {"type": "integer", "description": "0-based step index (default 0)"},
                },
                "required": ["odb_path"],
            },
        ),
        Tool(
            name="abaqus_list_odb_contents",
            description="List the contents of an ODB file: available steps, frames, and field outputs.",
            inputSchema={
                "type": "object",
                "properties": {
                    "odb_path": {"type": "string", "description": "Absolute path to the .odb file"},
                },
                "required": ["odb_path"],
            },
        ),
        Tool(
            name="abaqus_run_modeling",
            description="Execute an Abaqus Python modeling script via 'abaqus cae noGUI='. Gives full access to the Abaqus CAE API (mdb, session, abaqusConstants, etc.) for creating parts, materials, sections, steps, loads, BCs, mesh, and jobs.",
            inputSchema={
                "type": "object",
                "properties": {
                    "script": {"type": "string", "description": "Abaqus Python script content using CAE API"},
                    "save_model": {"type": "boolean", "description": "Save model database (.cae) after execution"},
                    "model_name": {"type": "string", "description": "Base name for saved .cae file"},
                    "timeout": {"type": "integer", "description": "Timeout in seconds (default 3600)"},
                },
                "required": ["script"],
            },
        ),
        Tool(
            name="abaqus_run_python",
            description="Execute an arbitrary Python script using the Abaqus Python interpreter ('abaqus python'). Gives access to odbAccess, abaqusConstants, and other Abaqus modules. For full CAE API access, use abaqus_run_modeling instead.",
            inputSchema={
                "type": "object",
                "properties": {
                    "script": {"type": "string", "description": "Python script to execute in Abaqus Python environment"},
                    "timeout": {"type": "integer", "description": "Timeout in seconds (default 3600)"},
                },
                "required": ["script"],
            },
        ),
    ]


@server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> list[TextContent]:
    handler = _TOOL_HANDLERS.get(name)
    if handler is None:
        return [TextContent(type="text", text=f"Unknown tool: {name}")]
    try:
        result = await handler(**arguments)
        return [TextContent(type="text", text=result)]
    except Exception as e:
        return [TextContent(type="text", text=f"Tool error: {e}")]


_TOOL_HANDLERS = {
    "abaqus_submit_job": abaqus_submit_job,
    "abaqus_job_status": abaqus_job_status,
    "abaqus_read_odb_field": read_odb_field,
    "abaqus_read_odb_history": read_odb_history,
    "abaqus_list_odb_contents": list_odb_contents,
    "abaqus_run_modeling": abaqus_run_modeling,
    "abaqus_run_python": abaqus_run_python,
}


def main():
    """Entry point for the MCP server."""
    import asyncio
    async def run():
        async with mcp.server.stdio.stdio_server() as (read, write):
            await server.run(read, write, server.create_initialization_options())
    asyncio.run(run())


if __name__ == "__main__":
    main()
