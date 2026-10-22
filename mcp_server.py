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
import os

import httpx
from mcp.server.mcpserver import MCPServer
from onboarding import GUIDE_URI, PROMPT_NAME, get_guide

DASHBOARD_URL = os.environ.get("SLURM_API_URL", "http://127.0.0.1:8765")

mcp = MCPServer(
    "slurm-gpu-cluster",
    instructions="""Slurm GPU Cluster management tools.
Use these tools to submit training jobs, monitor GPU usage,
check job status and logs, and manage the cluster.
首次使用先呼叫 get_onboarding_guide；也可讀取 slurm://guides/onboarding
或取得 slurm_onboarding prompt。先做只讀 discovery，整理工作摘要並取得確認後才提交。
Data must be on Internal NAS (/storage/Internal_NAS/).
Venvs are shared at /storage/Internal_NAS/venvs/.

## 重要行為規則

當使用者要求 training、跑模型、或執行任何 python script 時，一律使用 submit_job 透過 Slurm 送出，不要直接在本機執行。

如果使用者沒有提供以下資訊，必須先問清楚再送：
- username：使用者的名字（決定工作目錄 /storage/SSD2/slurmjob/<username>/）
- venv：要用哪個虛擬環境（可用 list_venvs 列出選項）

如果使用者之前已經說過 username 和 venv，記住並沿用，不用每次重複問。

## 叢集資訊
- 使用 cluster_info/gpu_status 查即時狀態，不猜 GPU 型號或空閒資源。
- 所有 jobs 目前以 hank 執行，username 只用於稽核；尚未有 sandbox/強制唯讀隔離。
- 共享 venv 位置：/storage/Internal_NAS/venvs/
- Job 工作目錄：/storage/SSD2/slurmjob/<username>/""",
)


@mcp.tool()
def get_onboarding_guide() -> str:
    """首次使用必讀：只讀指南與提交/追蹤範本；不提交、取消或連接 backend。"""
    return get_guide()


@mcp.resource(GUIDE_URI, mime_type="text/markdown")
def onboarding_resource() -> str:
    """Read the same onboarding guide without side effects."""
    return get_guide()


@mcp.prompt(name=PROMPT_NAME)
def onboarding_prompt() -> str:
    """取得 onboarding 指南；閱讀後先收集工作資料，不自動提交。"""
    return get_guide()


def _api(method: str, path: str, **kwargs) -> dict:
    """Call the Slurm Dashboard REST API."""
    url = f"{DASHBOARD_URL}{path}"
    with httpx.Client(timeout=15) as client:
        resp = client.request(method, url, **kwargs)
        resp.raise_for_status()
        return resp.json()


# ── Submit Job ──────────────────────────────────────────────

def _submit_job_request(
    command: str,
    username: str,
    venv: str,
    gpu: int = 1,
    job_name: str = "job",
    nodelist: str = "",
    repo_url: str = "",
    branch: str = "main",
    mem: str = "",
) -> str:
    username = username.strip()
    venv = venv.strip()
    if not username or not venv:
        return "Error: username and venv are required; no Slurm job was submitted."

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
        result = _api(
            "POST",
            "/submit",
            json=body,
            headers={"X-Submission-Source": "mcp"},
        )
    except httpx.HTTPStatusError as exc:
        return f"Error: {exc.response.text}"
    except httpx.HTTPError as exc:
        return f"Error: Slurm submission service is unavailable: {exc}"

    if not result.get("success"):
        return f"Error: {result.get('error', 'submission failed')}"
    if not result.get("submission_id") or not result.get("job_id") or not result.get("status"):
        return "Error: submission service returned an incomplete success response."
    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.tool()
def submit_job(
    command: str,
    username: str,
    venv: str,
    gpu: int = 1,
    job_name: str = "job",
    nodelist: str = "",
    repo_url: str = "",
    branch: str = "main",
    mem: str = "",
) -> str:
    """Submit a GPU training job to the Slurm cluster.

    Args:
        command: The training command, e.g. "python train.py --lr 1e-4"
        username: Your name, determines working dir at /storage/SSD2/slurmjob/<username>/
        venv: Shared venv name (e.g. "ltx2") or full path
        gpu: Number of GPUs needed (default 1)
        job_name: A short name for the job
        nodelist: Target node (e.g. "AI-Server-6"), leave empty for auto
        repo_url: GitHub repo to clone, e.g. "git@github.com:org/repo.git"
        branch: Git branch (default "main")
        mem: Memory limit (e.g. "32G"), leave empty for default
    """
    return _submit_job_request(
        command=command,
        username=username,
        gpu=gpu,
        job_name=job_name,
        nodelist=nodelist,
        repo_url=repo_url,
        branch=branch,
        venv=venv,
        mem=mem,
    )


# ── GPU Status ──────────────────────────────────────────────

@mcp.tool()
def gpu_status() -> str:
    """Get real-time GPU status across all cluster nodes.
    Shows VRAM usage, utilization %, running processes, and which user is using each GPU.
    """
    data = _api("GET", "/gpu-status")
    lines = []
    for node_name, node_data in data.items():
        lines.append(f"\n=== {node_name} ===")
        gpus = node_data
        if isinstance(node_data, dict):
            if "error" in node_data:
                lines.append(f"  Error: {node_data['error']}")
                continue
            lines.append(f"  State: {node_data.get('state', 'unknown')}")
            gpus = node_data.get("gpus", [])
        if isinstance(gpus, list):
            if not gpus:
                lines.append("  No GPU device telemetry available; do not infer availability.")
            for g in gpus:
                if "mem_used_mb" in g or "mem_total_mb" in g:
                    used = g.get("mem_used_mb", "?")
                    total = g.get("mem_total_mb", "?")
                    unit = "MB"
                else:
                    used = g.get("mem_used_gb", "?")
                    total = g.get("mem_total_gb", "?")
                    unit = "GB"
                util = g.get("util_pct", g.get("utilization", "?"))
                model = g.get("name", "")
                procs = g.get("processes", [])
                lines.append(f"  GPU {g.get('index', '?')}: {model}  {used}/{total} {unit}  util={util}%")
                if isinstance(procs, str):
                    if procs:
                        lines.append(f"    Processes: {procs}")
                elif isinstance(procs, list):
                    for p in procs:
                        if not isinstance(p, dict):
                            raise ValueError(f"Invalid GPU process telemetry for {node_name}")
                        user = p.get("user", "?")
                        pname = p.get("name", "?")
                        pmem = p.get("used_memory_mb", "?")
                        lines.append(f"    └─ {user}: {pname} ({pmem} MB)")
                else:
                    raise ValueError(f"Invalid GPU process telemetry for {node_name}")
        else:
            lines.append("  Invalid GPU telemetry response; do not infer availability.")
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
    lines = [
        f"{'ID':<8} {'Submission':<32} {'Commit':<12} "
        f"{'Name':<20} {'User':<10} {'Status':<10} {'Node':<15}"
    ]
    lines.append("-" * 112)
    for j in jobs:
        submission_id = j.get("submission_id") or "legacy"
        source_commit = (j.get("source_commit") or "-")[:12]
        lines.append(
            f"{j.get('job_id',''):<8} {submission_id:<32} {source_commit:<12} "
            f"{j.get('job_name',''):<20} {j.get('username',''):<10} "
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


# ── Main ────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Slurm GPU Cluster MCP Server")
    parser.add_argument("--sse", action="store_true", help="Run in SSE mode (HTTP)")
    parser.add_argument("--host", default="127.0.0.1", help="HTTP bind host (default 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8766, help="SSE port (default 8766)")
    args = parser.parse_args()

    if args.sse:
        mcp.run(transport="streamable-http", host=args.host, port=args.port)
    else:
        mcp.run()
