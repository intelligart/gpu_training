#!/usr/bin/env python3
"""
Slurm GPU Cluster MCP Server

Wraps the existing Slurm Dashboard REST API as MCP tools,
so AI agents (Claude Code, etc.) can directly submit jobs,
check GPU status, read logs, and manage the cluster.

Usage:
    python3 mcp_server.py                        # stdio mode (for Claude Code)
    python3 mcp_server.py --sse --port 8766      # SSE mode (for remote clients)
"""

import argparse
import json
from typing import Optional

import httpx
from mcp.server.mcpserver import MCPServer

DASHBOARD_URL = "http://ia-ai-server-5:8765"

mcp = MCPServer(
    "slurm-gpu-cluster",
    instructions="""Slurm GPU Cluster management tools.
Use these tools to submit training jobs, monitor GPU usage,
check job status and logs, and manage the cluster.
Data must be on Internal NAS (/storage/Internal_NAS/).
Venvs are shared at /storage/Internal_NAS/venvs/.""",
)


def _api(method: str, path: str, **kwargs) -> dict:
    """Call the Slurm Dashboard REST API."""
    url = f"{DASHBOARD_URL}{path}"
    with httpx.Client(timeout=15) as client:
        resp = client.request(method, url, **kwargs)
        resp.raise_for_status()
        return resp.json()


# ── Submit Job ──────────────────────────────────────────────

@mcp.tool()
def submit_job(
    command: str,
    username: str,
    gpu: int = 1,
    job_name: str = "job",
    nodelist: str = "",
    repo_url: str = "",
    branch: str = "main",
    venv: str = "",
    mem: str = "",
) -> str:
    """Submit a GPU training job to the Slurm cluster.

    Args:
        command: The training command, e.g. "python train.py --lr 1e-4"
        username: Your name, determines working dir at /storage/SSD2/slurmjob/<username>/
        gpu: Number of GPUs needed (default 1)
        job_name: A short name for the job
        nodelist: Target node (e.g. "AI-Server-6"), leave empty for auto
        repo_url: GitHub repo to clone, e.g. "git@github.com:org/repo.git"
        branch: Git branch (default "main")
        venv: Shared venv name (e.g. "ltx2") or full path
        mem: Memory limit (e.g. "32G"), leave empty for default
    """
    body = {
        "command": command,
        "username": username,
        "gpu": gpu,
        "job_name": job_name,
        "nodelist": nodelist,
        "repo_url": repo_url,
        "branch": branch,
        "venv": venv,
        "mem": mem,
    }
    try:
        result = _api("POST", "/submit", json=body)
        return json.dumps(result, ensure_ascii=False, indent=2)
    except httpx.HTTPStatusError as e:
        return f"Error: {e.response.text}"


# ── GPU Status ──────────────────────────────────────────────

@mcp.tool()
def gpu_status() -> str:
    """Get real-time GPU status across all cluster nodes.
    Shows VRAM usage, utilization %, running processes, and which user is using each GPU.
    """
    data = _api("GET", "/gpu-status")
    lines = []
    for node_name, gpus in data.items():
        lines.append(f"\n=== {node_name} ===")
        if isinstance(gpus, list):
            for g in gpus:
                used = g.get("mem_used_gb", "?")
                total = g.get("mem_total_gb", "?")
                util = g.get("utilization", "?")
                model = g.get("name", "")
                procs = g.get("processes", [])
                lines.append(f"  GPU {g.get('index', '?')}: {model}  {used}/{total} GB  util={util}%")
                for p in procs:
                    user = p.get("user", "?")
                    pname = p.get("name", "?")
                    pmem = p.get("used_memory_mb", "?")
                    lines.append(f"    └─ {user}: {pname} ({pmem} MB)")
        elif isinstance(gpus, dict) and "error" in gpus:
            lines.append(f"  Error: {gpus['error']}")
    return "\n".join(lines) if lines else "No GPU data available"


# ── Job Queue ───────────────────────────────────────────────

@mcp.tool()
def list_jobs(username: str = "") -> str:
    """List current jobs in the Slurm queue (running and pending).

    Args:
        username: Filter by username (optional, show all if empty)
    """
    params = {"user": username} if username else {}
    data = _api("GET", "/queue", params=params)
    jobs = data.get("jobs", [])
    if not jobs:
        return "No jobs in queue."
    lines = [f"{'ID':<8} {'Name':<20} {'User':<10} {'State':<10} {'Time':<10} {'Node':<15} {'GPU':<6}"]
    lines.append("-" * 80)
    for j in jobs:
        lines.append(
            f"{j.get('job_id',''):<8} {j.get('name',''):<20} {j.get('user',''):<10} "
            f"{j.get('state',''):<10} {j.get('time',''):<10} {j.get('nodes',''):<15} {j.get('gres',''):<6}"
        )
    return "\n".join(lines)


# ── Job Logs ────────────────────────────────────────────────

@mcp.tool()
def get_logs(job_id: str) -> str:
    """Get the output log of a job.

    Args:
        job_id: The Slurm job ID (e.g. "458")
    """
    data = _api("GET", f"/logs/{job_id}")
    log = data.get("log", "")
    file_path = data.get("file", "")
    header = f"[Log file: {file_path}]\n" if file_path else ""
    return header + log


# ── Cancel Job ──────────────────────────────────────────────

@mcp.tool()
def cancel_job(job_id: str) -> str:
    """Cancel a running or pending job.

    Args:
        job_id: The Slurm job ID to cancel
    """
    try:
        result = _api("DELETE", f"/cancel/{job_id}")
        return json.dumps(result, ensure_ascii=False, indent=2)
    except httpx.HTTPStatusError as e:
        return f"Error: {e.response.text}"


# ── Job History ─────────────────────────────────────────────

@mcp.tool()
def job_history(limit: int = 20) -> str:
    """Get recent job history (completed, failed, cancelled).

    Args:
        limit: Number of recent jobs to return (default 20)
    """
    data = _api("GET", "/history", params={"limit": limit})
    jobs = data.get("jobs", [])
    if not jobs:
        return "No job history."
    lines = [f"{'ID':<8} {'Name':<20} {'User':<10} {'Status':<10} {'Node':<15}"]
    lines.append("-" * 65)
    for j in jobs:
        lines.append(
            f"{j.get('job_id',''):<8} {j.get('job_name',''):<20} {j.get('username',''):<10} "
            f"{j.get('status',''):<10} {j.get('nodelist',''):<15}"
        )
    return "\n".join(lines)


# ── Cluster Info ────────────────────────────────────────────

@mcp.tool()
def cluster_info() -> str:
    """Get cluster node status (online/offline, GPU counts, etc.)."""
    data = _api("GET", "/cluster")
    return data.get("output", str(data))


# ── Available Venvs ─────────────────────────────────────────

@mcp.tool()
def list_venvs() -> str:
    """List available shared Python virtual environments on the NAS."""
    data = _api("GET", "/venvs")
    venvs = data.get("venvs", [])
    if not venvs:
        return "No venvs found."
    lines = []
    for v in venvs:
        if isinstance(v, dict):
            lines.append(f"  {v.get('name', '?')}: {v.get('path', '?')}")
        else:
            lines.append(f"  {v}")
    return "Available venvs:\n" + "\n".join(lines)


# ── Create Venv ─────────────────────────────────────────────

@mcp.tool()
def create_venv(name: str, python_version: str = "") -> str:
    """Create a new shared Python virtual environment on the NAS.

    Args:
        name: Name of the new venv (e.g. "mytrain"), will be created at /storage/Internal_NAS/venvs/<name>
        python_version: Python interpreter to use (e.g. "python3.10"), defaults to system python3
    """
    try:
        result = _api("POST", "/venvs/create", json={"name": name, "python_version": python_version})
        return json.dumps(result, ensure_ascii=False, indent=2)
    except httpx.HTTPStatusError as e:
        return f"Error: {e.response.text}"


# ── Main ────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Slurm GPU Cluster MCP Server")
    parser.add_argument("--sse", action="store_true", help="Run in SSE mode (HTTP)")
    parser.add_argument("--port", type=int, default=8766, help="SSE port (default 8766)")
    args = parser.parse_args()

    if args.sse:
        mcp.run(transport="streamable-http", host="0.0.0.0", port=args.port)
    else:
        mcp.run()
