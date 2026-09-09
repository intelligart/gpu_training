"""
Slurm MCP + HTTP Server
- MCP: Claude 可以直接用工具管理 job
- HTTP: Scientist 可以用 curl 提交 job

啟動方式:
  # MCP mode (給 Claude Code 用)
  python3 slurm_server.py

  # HTTP mode (給 scientist 用)
  python3 slurm_server.py --http --port 8765
"""

import subprocess
import os
import re
import argparse
import tempfile
import shlex
import sqlite3
import socket
import threading
from pathlib import Path
from typing import Optional
from datetime import datetime

SLURM_CONF = "/etc/slurm/slurm.conf"
SBATCH = "/usr/bin/sbatch"
SQUEUE = "/usr/bin/squeue"
SCANCEL = "/usr/bin/scancel"
SINFO = "/usr/bin/sinfo"
JOBS_DIR = Path("/home/hank/Code/slurm-jobs")
GENERATED_SCRIPTS_DIR = Path("/tmp/slurm-generated")

ENV = {**os.environ, "SLURM_CONF": SLURM_CONF}

# Shared venvs on NAS — 放在這個目錄下的子目錄會自動被偵測為可用 venv
VENVS_BASE = Path("/storage/Internal_NAS/venvs")

def get_available_venvs() -> list[dict]:
    """掃描 VENVS_BASE 下的目錄，自動偵測可用 venvs"""
    venvs = []
    if VENVS_BASE.exists():
        for d in sorted(VENVS_BASE.iterdir()):
            if d.is_dir():
                activate = d / "bin" / "activate"
                venvs.append({"name": d.name, "path": str(d), "exists": activate.exists()})
    return venvs

def resolve_venv(venv: str) -> str:
    """解析 venv 名稱或路徑，回傳完整路徑"""
    if not venv:
        return ""
    # 如果已經是絕對路徑，直接回傳
    if venv.startswith("/"):
        return venv
    # 當作 VENVS_BASE 下的名稱，組成完整路徑
    return str(VENVS_BASE / venv)

DEFAULT_REPO_DIR = "/storage/SSD2/hank/gpu_training"
SLURMJOB_BASE = Path("/storage/SSD2/slurmjob")
DB_PATH = Path("/storage/SSD2/hank/gpu_training/slurm_history.db")


def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id TEXT,
            username TEXT,
            job_name TEXT,
            command TEXT,
            gpu INTEGER,
            nodelist TEXT,
            repo_dir TEXT,
            repo_url TEXT,
            branch TEXT,
            submit_time TEXT
        )
    """)
    conn.commit()
    conn.close()


def record_job(job_id: str, username: str, job_name: str, command: str,
               gpu: int, nodelist: str, repo_dir: str, repo_url: str, branch: str):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        INSERT INTO jobs (job_id, username, job_name, command, gpu, nodelist, repo_dir, repo_url, branch, submit_time)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (job_id, username, job_name, command, gpu, nodelist, repo_dir, repo_url, branch,
          datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()


def get_history(limit: int = 100) -> list[dict]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM jobs ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def cleanup_old_jobs(days: int = 30):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "DELETE FROM jobs WHERE submit_time < datetime('now', ?)",
        (f"-{days} days",)
    )
    conn.commit()
    conn.close()


def get_stats() -> dict:
    conn = sqlite3.connect(DB_PATH)
    stats = {}
    # jobs per user
    rows = conn.execute(
        "SELECT username, COUNT(*) as count, SUM(gpu) as total_gpu FROM jobs GROUP BY username ORDER BY count DESC"
    ).fetchall()
    stats["by_user"] = [{"username": r[0], "jobs": r[1], "total_gpu": r[2] or 0} for r in rows]
    # jobs per node
    rows = conn.execute(
        "SELECT nodelist, COUNT(*) as count FROM jobs WHERE nodelist != '' GROUP BY nodelist ORDER BY count DESC"
    ).fetchall()
    stats["by_node"] = [{"node": r[0], "jobs": r[1]} for r in rows]
    # total
    row = conn.execute("SELECT COUNT(*), SUM(gpu) FROM jobs").fetchone()
    stats["total_jobs"] = row[0] or 0
    stats["total_gpu_requested"] = row[1] or 0
    conn.close()
    return stats


init_db()
cleanup_old_jobs(days=30)


def run_cmd(cmd: list[str]) -> tuple[str, str, int]:
    result = subprocess.run(cmd, capture_output=True, text=True, env=ENV)
    return result.stdout.strip(), result.stderr.strip(), result.returncode


def generate_script(
    command: str,
    gpu: int = 1,
    job_name: str = "job",
    nodelist: Optional[str] = None,
    branch: str = "main",
    repo_dir: str = "",
    repo_url: str = "",
    mem: str = "",
    venv: str = "",
) -> Path:
    """動態產生 sbatch script，回傳路徑"""
    GENERATED_SCRIPTS_DIR.mkdir(parents=True, exist_ok=True)

    nodelist_line = f"#SBATCH --nodelist={nodelist}" if nodelist else ""
    mem_line = f"#SBATCH --mem={mem}" if mem else ""
    work_dir = repo_dir or DEFAULT_REPO_DIR

    if venv:
        venv_path = resolve_venv(venv)
        venv_activate = f"source {venv_path}/bin/activate"
    else:
        venv_activate = "# no venv specified"

    if repo_url:
        if branch == "main":
            # Auto-detect default branch from remote
            branch_cmd = "BRANCH=$(git remote show origin 2>/dev/null | sed -n 's/.*HEAD branch: //p'); BRANCH=${BRANCH:-main}"
        else:
            branch_cmd = f"BRANCH={branch}"
        git_sync = f"""
if [ ! -d "{work_dir}/.git" ]; then
    git clone {repo_url} {work_dir}
fi
cd {work_dir}
git config --local --add safe.directory '{work_dir}'
{branch_cmd}
flock -w 60 .git/config sh -c "git fetch origin && git checkout $BRANCH && git pull origin $BRANCH"
"""
    else:
        git_sync = f"""
cd {work_dir}
git config --local --add safe.directory '{work_dir}'
flock -w 60 .git/config git pull origin {branch}
"""

    script = f"""#!/bin/bash
#SBATCH --job-name={job_name}
#SBATCH --gres=gpu:{gpu}
#SBATCH --cpus-per-task=4
#SBATCH --output=/tmp/slurm_{job_name}_%j.out
{nodelist_line}
{mem_line}
{venv_activate}
{git_sync}
{command}
"""

    # 用 job_name 命名，方便識別
    script_path = GENERATED_SCRIPTS_DIR / f"{job_name}.sh"
    script_path.write_text(script)
    script_path.chmod(0o755)
    return script_path


def submit_job(
    script_path: Optional[str] = None,
    gpu: int = 1,
    job_name: Optional[str] = None,
    nodelist: Optional[str] = None,
    command: Optional[str] = None,
    branch: str = "main",
    repo_dir: str = "",
    repo_url: str = "",
    mem: str = "",
    venv: str = "",
) -> dict:
    """提交 sbatch job。可指定現有 script_path 或直接給 command 動態產生"""
    if command:
        name = job_name or "job"
        path = generate_script(command, gpu=gpu, job_name=name, nodelist=nodelist, branch=branch, repo_dir=repo_dir, repo_url=repo_url, mem=mem, venv=venv)
    elif script_path:
        if not Path(script_path).exists():
            return {"success": False, "error": f"Script not found: {script_path}"}
        path = Path(script_path)
    else:
        return {"success": False, "error": "Must provide either command or script_path"}

    cmd = [SBATCH]
    if gpu and not command:  # command 模式已寫在 script 裡
        cmd += [f"--gres=gpu:{gpu}"]
    if job_name and not command:
        cmd += [f"--job-name={job_name}"]
    if nodelist and not command:
        cmd += [f"--nodelist={nodelist}"]
    cmd.append(str(path))

    stdout, stderr, rc = run_cmd(cmd)
    if rc == 0:
        job_id = stdout.split()[-1]
        return {"success": True, "job_id": job_id, "message": stdout, "script": str(path)}
    return {"success": False, "error": stderr}


def parse_queue_output(stdout: str) -> list[dict]:
    """Parse squeue output into list of job dicts"""
    lines = stdout.strip().splitlines()
    if len(lines) < 2:
        return []
    jobs = []
    for line in lines[1:]:  # skip header
        parts = line.split()
        if len(parts) >= 5:
            jobs.append({
                "job_id": parts[0],
                "name": parts[1],
                "user": parts[2],
                "state": parts[3],
                "time": parts[4],
                "gres": parts[5] if len(parts) > 5 else "",
                "nodes": parts[6] if len(parts) > 6 else "",
                "req_nodes": parts[7] if len(parts) > 7 else "",
            })
    return jobs


def get_gpu_alloc() -> dict:
    """計算每台節點已分配的 GPU 數量"""
    # 從 sinfo 取得每台節點的 GPU 總數
    stdout, _, rc = run_cmd([SINFO, "-N", "-o", "%N %G"])
    node_total = {}
    if rc == 0:
        for line in stdout.splitlines()[1:]:
            parts = line.split()
            if len(parts) >= 2:
                node = parts[0]
                m = __import__('re').search(r'gpu:(\d+)', parts[1])
                node_total[node] = int(m.group(1)) if m else 0

    # 從 squeue 取得 RUNNING job 的 GPU 分配
    stdout, _, rc = run_cmd([SQUEUE, "-t", "RUNNING", "-o", "%N %b"])
    node_alloc = {n: 0 for n in node_total}
    if rc == 0:
        for line in stdout.splitlines()[1:]:
            parts = line.split()
            if len(parts) >= 2:
                node = parts[0]
                m = __import__('re').search(r'gpu:(\d+)', parts[1])
                if m and node in node_alloc:
                    node_alloc[node] += int(m.group(1))

    return {
        node: {"alloc": node_alloc.get(node, 0), "total": total}
        for node, total in node_total.items()
    }


def _get_node_gpu_status(node: str) -> list[dict]:
    """SSH into a node and query nvidia-smi for GPU details."""
    hostname = socket.gethostname()
    is_local = (node == hostname or node == hostname.split('.')[0])

    nvidia_cmd = "nvidia-smi --query-gpu=index,name,memory.used,memory.total,utilization.gpu --format=csv,noheader,nounits"
    proc_cmd = "nvidia-smi --query-compute-apps=gpu_bus_id,pid,process_name,used_memory --format=csv,noheader,nounits"
    bus_cmd = "nvidia-smi --query-gpu=index,gpu_bus_id --format=csv,noheader"

    if is_local:
        shell_cmd = f"{nvidia_cmd} && echo '---PROCS---' && {proc_cmd} && echo '---BUS---' && {bus_cmd}"
    else:
        shell_cmd = f"ssh -o ConnectTimeout=3 -o StrictHostKeyChecking=no {node} \"{nvidia_cmd} && echo '---PROCS---' && {proc_cmd} && echo '---BUS---' && {bus_cmd}\""

    try:
        result = subprocess.run(shell_cmd, shell=True, capture_output=True, text=True, timeout=8)
        if result.returncode != 0:
            return []
    except (subprocess.TimeoutExpired, Exception):
        return []

    output = result.stdout.strip()
    parts = output.split('---PROCS---')
    gpu_section = parts[0].strip()
    rest = parts[1].strip() if len(parts) > 1 else ""
    bus_parts = rest.split('---BUS---')
    proc_section = bus_parts[0].strip()
    bus_section = bus_parts[1].strip() if len(bus_parts) > 1 else ""

    # Parse bus_id to index mapping
    bus_to_idx = {}
    for line in bus_section.splitlines():
        cols = [c.strip() for c in line.split(',')]
        if len(cols) >= 2:
            bus_to_idx[cols[1]] = int(cols[0])

    # Collect all PIDs from proc section, then batch-query usernames via ps
    all_pids = set()
    for line in proc_section.splitlines():
        cols = [c.strip() for c in line.split(',')]
        if len(cols) >= 4:
            all_pids.add(cols[1].strip())

    pid_to_user = {}
    if all_pids:
        ps_cmd_str = f"ps -o pid=,user= -p {','.join(all_pids)}"
        if is_local:
            ps_shell = ps_cmd_str
        else:
            ps_shell = f"ssh -o ConnectTimeout=3 -o StrictHostKeyChecking=no {node} \"{ps_cmd_str}\""
        try:
            ps_result = subprocess.run(ps_shell, shell=True, capture_output=True, text=True, timeout=5)
            for line in ps_result.stdout.strip().splitlines():
                fields = line.strip().split()
                if len(fields) >= 2:
                    pid_to_user[fields[0]] = fields[1]
        except Exception:
            pass

    # Parse processes
    gpu_procs: dict[int, list[dict]] = {}
    for line in proc_section.splitlines():
        cols = [c.strip() for c in line.split(',')]
        if len(cols) >= 4:
            bus_id = cols[0]
            idx = bus_to_idx.get(bus_id, -1)
            pid = cols[1].strip()
            proc_name = cols[2].split('/')[-1]  # just the binary name
            user = pid_to_user.get(pid, "")
            mem = int(cols[3]) if cols[3].strip().isdigit() else 0
            if idx not in gpu_procs:
                gpu_procs[idx] = []
            gpu_procs[idx].append({"name": proc_name, "user": user, "mem_mb": mem})

    # Parse GPU info
    gpus = []
    for line in gpu_section.splitlines():
        cols = [c.strip() for c in line.split(',')]
        if len(cols) >= 5:
            idx = int(cols[0])
            procs = gpu_procs.get(idx, [])
            # Summarize processes: "user/process (XXXMB)"
            proc_summary = ", ".join(
                f"{p['user']}/{p['name']} ({p['mem_mb']}MB)" if p['user'] else f"{p['name']} ({p['mem_mb']}MB)"
                for p in sorted(procs, key=lambda x: -x['mem_mb'])
            ) if procs else ""
            gpus.append({
                "index": idx,
                "name": cols[1],
                "mem_used_mb": int(cols[2]),
                "mem_total_mb": int(cols[3]),
                "util_pct": int(cols[4]),
                "processes": proc_summary,
            })
    return gpus


def get_gpu_status() -> dict:
    """Get real-time GPU status from all cluster nodes via nvidia-smi."""
    # Get node list from sinfo
    stdout, _, rc = run_cmd([SINFO, "-N", "-o", "%N %T", "--noheader"])
    nodes = {}
    if rc == 0:
        for line in stdout.splitlines():
            parts = line.split()
            if parts:
                nodes[parts[0]] = parts[1] if len(parts) > 1 else "unknown"

    # Query all nodes in parallel
    results = {}
    lock = threading.Lock()

    def query_node(node, state):
        gpus = _get_node_gpu_status(node)
        with lock:
            results[node] = {"state": state, "gpus": gpus}

    threads = [threading.Thread(target=query_node, args=(n, s)) for n, s in nodes.items()]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=10)

    return results


def get_queue(user: Optional[str] = None) -> str:
    """查看 job queue"""
    cmd = [SQUEUE, "-o", "%.8i %15j %10u %10T %10M %10b %N %v"]
    if user:
        cmd += ["-u", user]
    stdout, stderr, rc = run_cmd(cmd)
    return stdout if rc == 0 else f"Error: {stderr}"


def get_queue_json(user: Optional[str] = None) -> list[dict]:
    """查看 job queue，回傳結構化 JSON"""
    cmd = [SQUEUE, "-o", "%.8i %15j %10u %10T %10M %10b %N %v"]
    if user:
        cmd += ["-u", user]
    stdout, stderr, rc = run_cmd(cmd)
    if rc != 0:
        return []
    return parse_queue_output(stdout)


def get_job_status(job_id: str) -> str:
    """查看特定 job 狀態"""
    cmd = [SQUEUE, "-j", job_id, "-o", "%.8i %15j %10u %10T %10M %N"]
    stdout, stderr, rc = run_cmd(cmd)
    if rc == 0 and stdout:
        return stdout
    return f"Job {job_id} not found (may have completed)"


def get_job_status_json(job_id: str) -> dict:
    """查看特定 job 狀態，回傳結構化 JSON"""
    cmd = [SQUEUE, "-j", job_id, "-o", "%.8i %15j %10u %10T %10M %N"]
    stdout, stderr, rc = run_cmd(cmd)
    if rc == 0 and stdout:
        jobs = parse_queue_output(stdout)
        return jobs[0] if jobs else {"status": f"Job {job_id} not found"}
    return {"status": f"Job {job_id} not found (may have completed)"}


def cancel_job(job_id: str) -> dict:
    """取消 job"""
    stdout, stderr, rc = run_cmd([SCANCEL, job_id])
    if rc == 0:
        return {"success": True, "message": f"Job {job_id} cancelled"}
    return {"success": False, "error": stderr}


def get_cluster_info() -> str:
    """查看叢集資源狀態"""
    stdout, stderr, rc = run_cmd([SINFO, "-N", "-o", "%20N %10G %15C %T"])
    return stdout if rc == 0 else f"Error: {stderr}"


def list_scripts() -> list[str]:
    """列出可用的 job scripts"""
    scripts = []
    for path in [JOBS_DIR, Path("/home/hank/Code/slurm-demo")]:
        if path.exists():
            scripts.extend([str(p) for p in path.glob("*.sh")])
    return scripts


# ─── MCP Server ───────────────────────────────────────────────────────────────

def run_mcp_server():
    from mcp.server.mcpserver import MCPServer

    mcp = MCPServer("Slurm Manager")

    @mcp.tool()
    def slurm_submit(
        command: str,
        gpu: int = 1,
        job_name: str = "job",
        nodelist: str = "",
        branch: str = "main",
        repo_dir: str = "",
        repo_url: str = "",
        mem: str = "",
        venv: str = "",
    ) -> str:
        """
        提交 Slurm job。自動產生 sbatch script 並提交。
        command: 要執行的指令，例如 "python3 -u train.py --lr 0.001 --epochs 50"
        gpu: 需要幾個 GPU（預設 1）
        job_name: job 名稱（預設 job）
        nodelist: 指定節點，例如 ia-ai-server-5（選填，不填則自動分派）
        branch: git branch（預設 main）
        repo_dir: repo 在節點上的本地路徑（選填，預設 /storage/SSD2/hank/gpu_training）
        repo_url: git remote URL，若 repo_dir 不存在會自動 clone（選填）
        mem: 記憶體大小，例如 32G（選填，預設 4GB/CPU）
        venv: venv 路徑，例如 /storage/SSD2/alice/venv（選填）
        """
        result = submit_job(
            command=command,
            gpu=gpu,
            job_name=job_name or "job",
            nodelist=nodelist or None,
            branch=branch,
            repo_dir=repo_dir,
            repo_url=repo_url,
            mem=mem,
            venv=venv,
        )
        if result["success"]:
            return f"✓ Job submitted! Job ID: {result['job_id']}\nScript: {result['script']}"
        return f"✗ Failed: {result['error']}"

    @mcp.tool()
    def slurm_queue(user: str = "") -> str:
        """
        查看 job queue。
        user: 指定使用者（選填，不填則顯示所有人）
        """
        return get_queue(user or None)

    @mcp.tool()
    def slurm_status(job_id: str) -> str:
        """
        查看特定 job 的狀態。
        job_id: Job ID
        """
        return get_job_status(job_id)

    @mcp.tool()
    def slurm_cancel(job_id: str) -> str:
        """
        取消一個 job。
        job_id: 要取消的 Job ID
        """
        result = cancel_job(job_id)
        if result["success"]:
            return f"✓ {result['message']}"
        return f"✗ Failed: {result['error']}"

    @mcp.tool()
    def slurm_cluster() -> str:
        """查看叢集各節點 GPU 資源狀態"""
        return get_cluster_info()

    @mcp.tool()
    def slurm_list_scripts() -> str:
        """列出可用的 job scripts"""
        scripts = list_scripts()
        if not scripts:
            return "No scripts found"
        return "\n".join(scripts)

    mcp.run()


# ─── HTTP Server ───────────────────────────────────────────────────────────────

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Slurm Dashboard</title>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { background: #0f1117; color: #e2e8f0; font-family: 'SF Mono', 'Fira Code', monospace; min-height: 100vh; }

    header { background: #1a1d27; border-bottom: 1px solid #2d3148; padding: 18px 32px; display: flex; align-items: center; justify-content: space-between; }
    header h1 { font-size: 18px; font-weight: 600; color: #a78bfa; letter-spacing: 0.05em; }
    header h1 span { color: #64748b; font-weight: 400; }
    .status-dot { width: 8px; height: 8px; border-radius: 50%; background: #22c55e; display: inline-block; margin-right: 8px; box-shadow: 0 0 6px #22c55e; animation: pulse 2s infinite; }
    @keyframes pulse { 0%,100% { opacity: 1; } 50% { opacity: 0.4; } }
    .last-update { font-size: 12px; color: #475569; }

    main { padding: 24px 32px; display: grid; gap: 20px; }

    .section-title { font-size: 11px; font-weight: 600; letter-spacing: 0.1em; text-transform: uppercase; color: #64748b; margin-bottom: 12px; }

    /* Cluster cards */
    .cluster-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 12px; }
    .node-card { background: #1a1d27; border: 1px solid #2d3148; border-radius: 10px; padding: 16px 20px; }
    .node-card.idle { border-color: #1e3a2f; }
    .node-card.busy { border-color: #3b2020; }
    .node-name { font-size: 14px; font-weight: 600; color: #c4b5fd; margin-bottom: 10px; }
    .node-meta { font-size: 12px; color: #64748b; margin-bottom: 10px; }
    .gpu-bar-wrap { background: #0f1117; border-radius: 4px; height: 6px; overflow: hidden; }
    .gpu-bar { height: 100%; border-radius: 4px; background: linear-gradient(90deg, #7c3aed, #a78bfa); transition: width 0.5s ease; }
    .gpu-bar.full { background: linear-gradient(90deg, #dc2626, #f87171); }
    .node-state { display: inline-block; margin-top: 10px; font-size: 11px; padding: 2px 8px; border-radius: 20px; font-weight: 600; }
    .state-idle { background: #14532d; color: #4ade80; }
    .state-alloc { background: #7c2d12; color: #fb923c; }
    .state-mix { background: #713f12; color: #fbbf24; }
    .state-down { background: #1e1b4b; color: #818cf8; }

    /* Queue table */
    .queue-wrap { background: #1a1d27; border: 1px solid #2d3148; border-radius: 10px; overflow: hidden; }
    table { width: 100%; border-collapse: collapse; }
    thead tr { background: #12141f; }
    th { padding: 10px 16px; text-align: left; font-size: 11px; font-weight: 600; letter-spacing: 0.08em; text-transform: uppercase; color: #475569; border-bottom: 1px solid #2d3148; }
    td { padding: 11px 16px; font-size: 13px; border-bottom: 1px solid #1e2235; }
    tr:last-child td { border-bottom: none; }
    tr:hover td { background: #1e2235; }
    .badge { display: inline-block; padding: 2px 8px; border-radius: 20px; font-size: 11px; font-weight: 700; }
    .badge-running { background: #14532d; color: #4ade80; }
    .badge-pending { background: #713f12; color: #fbbf24; }
    .badge-other { background: #1e1b4b; color: #818cf8; }
    .empty-state { text-align: center; padding: 40px; color: #475569; font-size: 13px; }

    /* Submit form */
    .form-card { background: #1a1d27; border: 1px solid #2d3148; border-radius: 10px; padding: 20px 24px; }
    .form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
    .form-full { grid-column: 1 / -1; }
    label { display: block; font-size: 11px; color: #64748b; margin-bottom: 5px; font-weight: 600; letter-spacing: 0.05em; text-transform: uppercase; }
    input, select { width: 100%; background: #0f1117; border: 1px solid #2d3148; border-radius: 6px; padding: 8px 12px; color: #e2e8f0; font-family: inherit; font-size: 13px; outline: none; transition: border-color 0.2s; }
    input:focus, select:focus { border-color: #7c3aed; }
    .btn-submit { margin-top: 16px; width: 100%; padding: 10px; background: #7c3aed; border: none; border-radius: 6px; color: #fff; font-family: inherit; font-size: 14px; font-weight: 600; cursor: pointer; transition: background 0.2s; }
    .btn-submit:hover { background: #6d28d9; }
    .btn-submit:disabled { background: #3b3460; color: #64748b; cursor: not-allowed; }
    .toast { position: fixed; bottom: 24px; right: 24px; padding: 12px 20px; border-radius: 8px; font-size: 13px; font-weight: 600; opacity: 0; transform: translateY(10px); transition: all 0.3s; pointer-events: none; }
    .toast.show { opacity: 1; transform: translateY(0); }
    .toast.success { background: #14532d; color: #4ade80; border: 1px solid #166534; }
    .toast.error { background: #7f1d1d; color: #fca5a5; border: 1px solid #991b1b; }

    /* Stats */
    .stat-card { background: #1a1d27; border: 1px solid #2d3148; border-radius: 10px; padding: 16px 20px; }
    .stat-number { font-size: 28px; font-weight: 700; color: #a78bfa; margin-bottom: 4px; }
    .stat-label { font-size: 11px; color: #64748b; text-transform: uppercase; letter-spacing: 0.08em; }
    .stat-row { margin-top: 10px; font-size: 12px; color: #64748b; display: flex; justify-content: space-between; border-top: 1px solid #2d3148; padding-top: 8px; }

    /* GPU status table */
    .gpu-util-bar { display: inline-block; width: 60px; height: 6px; background: #0f1117; border-radius: 3px; vertical-align: middle; margin-right: 6px; }
    .gpu-util-fill { height: 100%; border-radius: 3px; background: linear-gradient(90deg, #22c55e, #4ade80); }
    .gpu-util-fill.high { background: linear-gradient(90deg, #f59e0b, #fbbf24); }
    .gpu-util-fill.critical { background: linear-gradient(90deg, #dc2626, #f87171); }
    .vram-text { font-size: 12px; color: #94a3b8; }
    .vram-text .used { color: #a78bfa; font-weight: 600; }
    .proc-text { font-size: 11px; color: #64748b; }
    .gpu-node-offline { color: #475569; font-style: italic; }

    /* Log modal */
    .modal-backdrop { display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.7); z-index: 100; align-items: center; justify-content: center; }
    .modal-backdrop.show { display: flex; }
    .modal { background: #1a1d27; border: 1px solid #2d3148; border-radius: 12px; width: 800px; max-width: 95vw; max-height: 80vh; display: flex; flex-direction: column; }
    .modal-header { display: flex; align-items: center; justify-content: space-between; padding: 16px 20px; border-bottom: 1px solid #2d3148; }
    .modal-title { font-size: 14px; font-weight: 600; color: #a78bfa; }
    .modal-close { background: none; border: none; color: #64748b; font-size: 20px; cursor: pointer; line-height: 1; }
    .modal-close:hover { color: #e2e8f0; }
    .modal-body { flex: 1; overflow-y: auto; padding: 16px 20px; }
    .log-content { font-family: 'SF Mono', 'Fira Code', monospace; font-size: 12px; color: #94a3b8; white-space: pre-wrap; word-break: break-all; line-height: 1.6; }
    .log-file { font-size: 11px; color: #475569; margin-bottom: 12px; }
  </style>
</head>
<body>
  <header>
    <h1><span class="status-dot"></span>Slurm <span>Dashboard</span></h1>
    <div class="last-update" id="last-update">Connecting...</div>
  </header>

  <main>
    <div>
      <div class="section-title">Cluster Nodes</div>
      <div class="cluster-grid" id="cluster-grid"><div class="node-card"><div class="node-name" style="color:#475569">Loading...</div></div></div>
    </div>

    <div>
      <div class="section-title">GPU Status (Real-time)</div>
      <div class="queue-wrap">
        <table>
          <thead><tr><th>Node</th><th>GPU</th><th>Model</th><th>VRAM Usage</th><th>Utilization</th><th>Processes</th></tr></thead>
          <tbody id="gpu-status-body"><tr><td colspan="6" class="empty-state">Loading...</td></tr></tbody>
        </table>
      </div>
    </div>

    <div>
      <div class="section-title">Job Queue</div>
      <div class="queue-wrap">
        <table>
          <thead><tr><th>Job ID</th><th>Name</th><th>User</th><th>State</th><th>Time</th><th>GPU</th><th>Node</th><th>Requested</th><th></th></tr></thead>
          <tbody id="queue-body"><tr><td colspan="7" class="empty-state">Loading...</td></tr></tbody>
        </table>
      </div>
    </div>

    <div>
      <div class="section-title">Statistics (Last 30 Days)</div>
      <div class="cluster-grid" id="stats-grid"><div class="node-card"><div class="node-name" style="color:#475569">Loading...</div></div></div>
    </div>

    <div>
      <div class="section-title">Job History</div>
      <div class="queue-wrap">
        <table>
          <thead><tr><th>Job ID</th><th>Name</th><th>User</th><th>GPU</th><th>Node</th><th>Branch</th><th>Submitted</th><th></th></tr></thead>
          <tbody id="history-body"><tr><td colspan="8" class="empty-state">Loading...</td></tr></tbody>
        </table>
      </div>
    </div>

    <div>
      <div class="section-title">Submit Job</div>
      <div class="form-card">
        <div class="form-grid">
          <div class="form-full">
            <label>Command</label>
            <input id="f-command" type="text" placeholder="python3 -u train.py --lr 0.001 --epochs 50">
          </div>
          <div>
            <label>Username <span style="color:#f87171">*</span></label>
            <input id="f-username" type="text" placeholder="alice">
          </div>
          <div>
            <label>Job Name</label>
            <input id="f-jobname" type="text" placeholder="my-experiment">
          </div>
          <div>
            <label>GPU Count</label>
            <select id="f-gpu">
              <option value="1">1 GPU</option>
              <option value="2">2 GPUs</option>
              <option value="4">4 GPUs</option>
            </select>
          </div>
          <div>
            <label>Branch</label>
            <input id="f-branch" type="text" placeholder="main" value="main">
          </div>
          <div>
            <label>Node (optional)</label>
            <input id="f-nodelist" type="text" placeholder="ia-ai-server-4">
          </div>
          <div class="form-full">
            <label>Repo Dir (optional)</label>
            <input id="f-repodir" type="text" placeholder="/storage/SSD2/hank/gpu_training">
          </div>
          <div class="form-full">
            <label>Repo URL (optional, auto-clone if dir missing)</label>
            <input id="f-repourl" type="text" placeholder="git@github.com:org/repo.git">
          </div>
          <div class="form-full">
            <label>Venv</label>
            <select id="f-venv" onchange="toggleCustomVenv()">
              <option value="">-- None (no venv) --</option>
            </select>
            <input id="f-venv-custom" type="text" placeholder="/storage/SSD2/alice/venv" style="display:none;margin-top:6px">
          </div>
        </div>
        <button class="btn-submit" id="btn-submit" onclick="submitJob()">Submit Job</button>
      </div>
    </div>
  </main>

  <!-- Log Modal -->
  <div class="modal-backdrop" id="log-modal" onclick="closeLogModal(event)">
    <div class="modal">
      <div class="modal-header">
        <div class="modal-title" id="modal-title">Job Log</div>
        <button class="modal-close" onclick="closeModal()">✕</button>
      </div>
      <div class="modal-body">
        <div class="log-file" id="log-file"></div>
        <div class="log-content" id="log-content">Loading...</div>
      </div>
    </div>
  </div>

  <div class="toast" id="toast"></div>

  <script>
    function parseCluster(raw) {
      const lines = raw.trim().split('\\n').filter(l => l && !l.startsWith('NODELIST'));
      return lines.map(line => {
        const parts = line.trim().split(/\\s+/);
        return { name: parts[0], gres: parts[1] || '', cpus: parts[2] || '', state: parts[3] || '' };
      });
    }

    function nodeCardHTML(node, gpuData) {
      const state = node.state.toLowerCase();
      const stateClass = state.includes('idle') ? 'state-idle' :
                         state.includes('alloc') ? 'state-alloc' :
                         state.includes('mix') ? 'state-mix' : 'state-down';
      const cardClass = state.includes('idle') ? 'idle' : 'busy';

      // GPU alloc from /gpu-alloc endpoint
      const gpuInfo = (gpuData || {})[node.name] || {};
      const gpuAlloc = gpuInfo.alloc || 0;
      const gpuTotal = gpuInfo.total || 0;
      const gpuPct = gpuTotal > 0 ? Math.round(gpuAlloc / gpuTotal * 100) : 0;

      // parse CPU allocated/total from "A/I/O/T"
      const cpuParts = node.cpus.split('/');
      const cpuAlloc = parseInt(cpuParts[0]) || 0;
      const cpuTotal = parseInt(cpuParts[3]) || 1;

      return `
        <div class="node-card ${cardClass}">
          <div class="node-name">${node.name}</div>
          <div class="node-meta">GPU: ${gpuAlloc}/${gpuTotal} allocated &nbsp;|&nbsp; CPU: ${cpuAlloc}/${cpuTotal}</div>
          <div class="gpu-bar-wrap"><div class="gpu-bar ${gpuPct > 80 ? 'full' : ''}" style="width:${gpuPct}%"></div></div>
          <span class="node-state ${stateClass}">${node.state}</span>
        </div>`;
    }

    function queueRowHTML(job) {
      const badgeClass = job.state === 'RUNNING' ? 'badge-running' :
                         job.state === 'PENDING' ? 'badge-pending' : 'badge-other';
      const gpuMatch = job.gres ? job.gres.match(/gpu:(\d+)/) : null;
      const gpuCount = gpuMatch ? gpuMatch[1] : '—';
      return `<tr>
        <td style="color:#94a3b8">${job.job_id}</td>
        <td style="color:#e2e8f0;font-weight:600">${job.name}</td>
        <td style="color:#94a3b8">${job.user}</td>
        <td><span class="badge ${badgeClass}">${job.state}</span></td>
        <td style="color:#64748b">${job.time}</td>
        <td style="color:#a78bfa;font-weight:600">${gpuCount}</td>
        <td style="color:#64748b">${job.nodes || '—'}</td>
        <td style="color:#475569;font-size:12px">${job.req_nodes && job.req_nodes !== 'N/A' ? job.req_nodes : '—'}</td>
        <td style="display:flex;gap:4px">
          <button onclick="showLog('${job.job_id}','${job.name}')" style="background:none;border:1px solid #1e3a5f;color:#60a5fa;border-radius:4px;padding:2px 8px;cursor:pointer;font-size:11px">log</button>
          <button onclick="cancelJob('${job.job_id}')" style="background:none;border:1px solid #3b3460;color:#94a3b8;border-radius:4px;padding:2px 8px;cursor:pointer;font-size:11px">cancel</button>
        </td>
      </tr>`;
    }

    async function refreshStats() {
      try {
        const [statsRes, histRes] = await Promise.all([fetch('/stats'), fetch('/history?limit=50')]);
        const stats = await statsRes.json();
        const hist = await histRes.json();

        // Stats cards
        const byUser = stats.by_user || [];
        let statsHtml = `
          <div class="stat-card">
            <div class="stat-number">${stats.total_jobs}</div>
            <div class="stat-label">Total Jobs</div>
            <div class="stat-row"><span>GPU hours requested</span><span style="color:#a78bfa">${stats.total_gpu_requested}</span></div>
          </div>`;
        byUser.forEach(u => {
          statsHtml += `
            <div class="stat-card">
              <div class="stat-number">${u.jobs}</div>
              <div class="stat-label">${u.username}</div>
              <div class="stat-row"><span>Total GPU requested</span><span style="color:#a78bfa">${u.total_gpu}</span></div>
            </div>`;
        });
        document.getElementById('stats-grid').innerHTML = statsHtml;

        // History table
        const jobs = hist.jobs || [];
        document.getElementById('history-body').innerHTML = jobs.length
          ? jobs.map(j => `<tr>
              <td style="color:#94a3b8">${j.job_id}</td>
              <td style="color:#e2e8f0;font-weight:600">${j.job_name}</td>
              <td style="color:#94a3b8">${j.username}</td>
              <td style="color:#a78bfa;font-weight:600">${j.gpu}</td>
              <td style="color:#64748b">${j.nodelist || '—'}</td>
              <td style="color:#64748b">${j.branch}</td>
              <td style="color:#475569;font-size:12px">${j.submit_time}</td>
              <td><button onclick="showLog('${j.job_id}','${j.job_name}')" style="background:none;border:1px solid #1e3a5f;color:#60a5fa;border-radius:4px;padding:2px 8px;cursor:pointer;font-size:11px">log</button></td>
            </tr>`).join('')
          : '<tr><td colspan="8" class="empty-state">No history yet</td></tr>';
      } catch(e) {}
    }

    function toggleCustomVenv() {
      const sel = document.getElementById('f-venv');
      const custom = document.getElementById('f-venv-custom');
      custom.style.display = sel.value === '__custom__' ? 'block' : 'none';
      if (sel.value !== '__custom__') custom.value = '';
    }

    function getVenvValue() {
      const sel = document.getElementById('f-venv');
      if (sel.value === '__custom__') return document.getElementById('f-venv-custom').value.trim();
      return sel.value;
    }

    async function loadVenvs() {
      try {
        const res = await fetch('/venvs');
        const data = await res.json();
        const sel = document.getElementById('f-venv');
        (data.venvs || []).forEach(v => {
          const opt = document.createElement('option');
          opt.value = v.name;
          opt.textContent = v.name + (v.exists ? '' : ' (missing)');
          sel.appendChild(opt);
        });
        const custom = document.createElement('option');
        custom.value = '__custom__';
        custom.textContent = 'Custom path...';
        sel.appendChild(custom);
      } catch(e) {}
    }

    function renderGpuStatus(data) {
      let rows = '';
      const nodeNames = Object.keys(data).sort();
      for (const node of nodeNames) {
        const info = data[node];
        if (!info.gpus || info.gpus.length === 0) {
          rows += `<tr><td style="color:#c4b5fd;font-weight:600">${node}</td><td colspan="5" class="gpu-node-offline">${info.state === 'down' || info.state === 'down*' ? 'Node down' : 'No GPU data'}</td></tr>`;
          continue;
        }
        info.gpus.forEach((gpu, i) => {
          const memPct = gpu.mem_total_mb > 0 ? Math.round(gpu.mem_used_mb / gpu.mem_total_mb * 100) : 0;
          const memUsedGB = (gpu.mem_used_mb / 1024).toFixed(1);
          const memTotalGB = (gpu.mem_total_mb / 1024).toFixed(0);
          const utilClass = gpu.util_pct > 80 ? 'critical' : gpu.util_pct > 40 ? 'high' : '';
          rows += `<tr>
            <td style="color:#c4b5fd;font-weight:600">${i === 0 ? node : ''}</td>
            <td style="color:#94a3b8">GPU ${gpu.index}</td>
            <td style="color:#e2e8f0">${gpu.name}</td>
            <td><span class="vram-text"><span class="used">${memUsedGB}</span> / ${memTotalGB} GB</span></td>
            <td><div class="gpu-util-bar"><div class="gpu-util-fill ${utilClass}" style="width:${gpu.util_pct}%"></div></div> ${gpu.util_pct}%</td>
            <td class="proc-text">${gpu.processes || '—'}</td>
          </tr>`;
        });
      }
      document.getElementById('gpu-status-body').innerHTML = rows || '<tr><td colspan="6" class="empty-state">No nodes found</td></tr>';
    }

    async function refresh() {
      try {
        const [clusterRes, queueRes, gpuRes, gpuStatusRes] = await Promise.all([
          fetch('/cluster'), fetch('/queue'), fetch('/gpu-alloc'), fetch('/gpu-status')
        ]);
        const clusterData = await clusterRes.json();
        const queueData = await queueRes.json();
        const gpuData = await gpuRes.json();
        const gpuStatusData = await gpuStatusRes.json();

        const nodes = parseCluster(clusterData.output || '');
        document.getElementById('cluster-grid').innerHTML =
          nodes.length ? nodes.map(n => nodeCardHTML(n, gpuData)).join('') : '<div style="color:#475569;padding:16px">No nodes found</div>';

        renderGpuStatus(gpuStatusData);

        const jobs = queueData.jobs || [];
        document.getElementById('queue-body').innerHTML =
          jobs.length ? jobs.map(queueRowHTML).join('') :
          '<tr><td colspan="7" class="empty-state">No jobs in queue</td></tr>';

        document.getElementById('last-update').textContent =
          'Updated ' + new Date().toLocaleTimeString();
      } catch(e) {
        document.getElementById('last-update').textContent = 'Connection error';
      }
    }

    async function submitJob() {
      const command = document.getElementById('f-command').value.trim();
      const username = document.getElementById('f-username').value.trim();
      if (!command) { showToast('Command is required', 'error'); return; }
      if (!username) { showToast('Username is required', 'error'); return; }
      const btn = document.getElementById('btn-submit');
      btn.disabled = true; btn.textContent = 'Submitting...';
      try {
        const res = await fetch('/submit', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            command,
            username,
            job_name: document.getElementById('f-jobname').value || 'job',
            gpu: parseInt(document.getElementById('f-gpu').value),
            branch: document.getElementById('f-branch').value || 'main',
            nodelist: document.getElementById('f-nodelist').value,
            repo_dir: document.getElementById('f-repodir').value,
            repo_url: document.getElementById('f-repourl').value,
            venv: getVenvValue(),
          })
        });
        const data = await res.json();
        if (res.ok) {
          showToast('Job ' + data.job_id + ' submitted!', 'success');
          document.getElementById('f-command').value = '';
          document.getElementById('f-jobname').value = '';
          refresh();
        } else {
          showToast(data.detail || 'Submit failed', 'error');
        }
      } catch(e) {
        showToast('Network error', 'error');
      }
      btn.disabled = false; btn.textContent = 'Submit Job';
    }

    async function cancelJob(jobId) {
      if (!confirm('Cancel job ' + jobId + '?')) return;
      await fetch('/cancel/' + jobId, { method: 'DELETE' });
      refresh();
    }

    function showToast(msg, type) {
      const t = document.getElementById('toast');
      t.textContent = msg; t.className = 'toast ' + type + ' show';
      setTimeout(() => { t.className = 'toast'; }, 3000);
    }

    async function showLog(jobId, jobName) {
      document.getElementById('modal-title').textContent = `Log — ${jobName} (${jobId})`;
      document.getElementById('log-file').textContent = '';
      document.getElementById('log-content').textContent = 'Loading...';
      document.getElementById('log-modal').classList.add('show');
      try {
        const res = await fetch('/logs/' + jobId);
        const data = await res.json();
        document.getElementById('log-file').textContent = data.file || '';
        document.getElementById('log-content').textContent = data.log || '(empty)';
      } catch(e) {
        document.getElementById('log-content').textContent = 'Error loading log';
      }
    }

    function closeModal() {
      document.getElementById('log-modal').classList.remove('show');
    }

    function closeLogModal(e) {
      if (e.target === document.getElementById('log-modal')) closeModal();
    }

    refresh();
    refreshStats();
    loadVenvs();
    setInterval(refresh, 5000);
    setInterval(refreshStats, 30000);
  </script>
</body>
</html>"""


def run_http_server(port: int = 8765):
    from fastapi import FastAPI, HTTPException
    from fastapi.responses import HTMLResponse
    from pydantic import BaseModel
    import uvicorn

    app = FastAPI(title="Slurm API", description="Submit and manage Slurm jobs")

    class SubmitRequest(BaseModel):
        command: str                  # e.g. "python3 -u train.py --lr 0.001"
        username: str                 # e.g. "alice" — determines /storage/SSD2/slurmjob/<username>/
        gpu: int = 1
        job_name: str = "job"
        nodelist: str = ""
        branch: str = "main"
        repo_dir: str = ""           # must be under /storage/SSD2/slurmjob/<username>/
        repo_url: str = ""           # e.g. "git@github.com:org/repo.git"
        mem: str = ""                # e.g. "32G", "16G" (預設用 DefMemPerCPU)
        venv: str = ""               # e.g. "/storage/SSD2/alice/venv"
        script_path: str = ""        # legacy: 直接指定現有 script

    @app.post("/submit")
    def submit(req: SubmitRequest):
        if not req.username:
            raise HTTPException(status_code=400, detail="username is required")

        user_base = SLURMJOB_BASE / req.username

        # Determine repo_dir: default to user base if not specified
        if req.repo_dir:
            repo_dir_path = Path(req.repo_dir).resolve()
            user_base_resolved = user_base.resolve()
            # Enforce repo_dir must be under /storage/SSD2/slurmjob/<username>/
            try:
                repo_dir_path.relative_to(user_base_resolved)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"repo_dir must be under {user_base}/ (got: {req.repo_dir})"
                )
            repo_dir = str(repo_dir_path)
        else:
            repo_dir = str(user_base)

        result = submit_job(
            command=req.command or None,
            script_path=req.script_path or None,
            gpu=req.gpu,
            job_name=req.job_name or None,
            nodelist=req.nodelist or None,
            branch=req.branch,
            repo_dir=repo_dir,
            repo_url=req.repo_url,
            mem=req.mem,
            venv=req.venv,
        )
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["error"])
        # Record to SQLite
        record_job(
            job_id=result["job_id"],
            username=req.username,
            job_name=req.job_name or "job",
            command=req.command,
            gpu=req.gpu,
            nodelist=req.nodelist or "",
            repo_dir=repo_dir,
            repo_url=req.repo_url,
            branch=req.branch,
        )
        return result

    @app.get("/queue")
    def queue(user: str = ""):
        return {"jobs": get_queue_json(user or None)}

    @app.get("/status/{job_id}")
    def status(job_id: str):
        return get_job_status_json(job_id)

    @app.delete("/cancel/{job_id}")
    def cancel(job_id: str):
        result = cancel_job(job_id)
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["error"])
        return result

    @app.get("/history")
    def history(limit: int = 100):
        return {"jobs": get_history(limit)}

    @app.get("/stats")
    def stats():
        return get_stats()

    @app.get("/logs/{job_id}")
    def logs(job_id: str):
        import glob as _glob
        matches = _glob.glob(f"/tmp/slurm_*_{job_id}.out")
        if not matches:
            return {"job_id": job_id, "log": f"(no log file found for job {job_id})"}
        log_path = matches[0]
        try:
            content = Path(log_path).read_text(errors="replace")
            return {"job_id": job_id, "file": log_path, "log": content}
        except Exception as e:
            return {"job_id": job_id, "log": f"Error reading log: {e}"}

    @app.get("/cluster")
    def cluster():
        return {"output": get_cluster_info()}

    @app.get("/gpu-alloc")
    def gpu_alloc():
        return get_gpu_alloc()

    @app.get("/gpu-status")
    def gpu_status():
        return get_gpu_status()

    @app.get("/venvs")
    def venvs():
        return {"venvs": get_available_venvs()}

    class CreateVenvRequest(BaseModel):
        name: str
        python_version: str = ""

    @app.post("/venvs/create")
    def create_venv(req: CreateVenvRequest):
        import re
        if not re.match(r'^[a-zA-Z0-9_-]+$', req.name):
            raise HTTPException(status_code=400, detail="Invalid venv name: use only letters, numbers, _ or -")
        venv_path = VENVS_BASE / req.name
        if venv_path.exists():
            raise HTTPException(status_code=400, detail=f"Venv '{req.name}' already exists at {venv_path}")
        python = req.python_version or "python3"
        result = subprocess.run(
            [python, "-m", "venv", str(venv_path)],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            raise HTTPException(status_code=500, detail=result.stderr)
        return {"success": True, "name": req.name, "path": str(venv_path)}

    @app.get("/scripts")
    def scripts():
        return {"scripts": list_scripts()}

    @app.get("/", response_class=HTMLResponse)
    def root():
        return HTMLResponse(content=DASHBOARD_HTML)

    @app.get("/api")
    def api_docs():
        return {
            "service": "Slurm API",
            "endpoints": {
                "POST /submit": {
                    "desc": "提交 job",
                    "body": {
                        "command": "要執行的指令 (必填), e.g. 'python3 -u train.py --lr 0.001'",
                        "username": "使用者名稱 (必填), e.g. 'alice' → repo 放在 /storage/SSD2/slurmjob/alice/",
                        "gpu": "GPU 數量 (預設 1)",
                        "job_name": "job 名稱 (預設 job)",
                        "nodelist": "指定節點 (選填)",
                        "branch": "git branch (預設 main)",
                        "repo_dir": "repo 路徑 (選填, 必須在 /storage/SSD2/slurmjob/<username>/ 底下)",
                        "repo_url": "git remote URL (選填)",
                    }
                },
                "GET /queue": "查看 queue，?user=xxx 過濾使用者",
                "GET /status/{job_id}": "查看 job 狀態",
                "DELETE /cancel/{job_id}": "取消 job",
                "GET /cluster": "查看叢集資源",
                "GET /scripts": "列出可用 scripts",
            }
        }

    print(f"Slurm HTTP API running at http://0.0.0.0:{port}")
    uvicorn.run(app, host="0.0.0.0", port=port)


# ─── Entry Point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--http", action="store_true", help="Run as HTTP server")
    parser.add_argument("--port", type=int, default=8765, help="HTTP port (default: 8765)")
    args = parser.parse_args()

    if args.http:
        run_http_server(port=args.port)
    else:
        run_mcp_server()
