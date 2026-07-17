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
import argparse
import tempfile
import shlex
from pathlib import Path
from typing import Optional

SLURM_CONF = "/etc/slurm/slurm.conf"
SBATCH = "/usr/bin/sbatch"
SQUEUE = "/usr/bin/squeue"
SCANCEL = "/usr/bin/scancel"
SINFO = "/usr/bin/sinfo"
JOBS_DIR = Path("/home/hank/Code/slurm-jobs")
GENERATED_SCRIPTS_DIR = Path("/tmp/slurm-generated")

ENV = {**os.environ, "SLURM_CONF": SLURM_CONF}

# Per-node venv activation (維護在這裡，不用每個 script 各自寫)
VENV_ACTIVATE = """
case "$SLURMD_NODENAME" in
    ia-ai-server-5) source /storage/SSD2/hank/ComfyUI/venv/bin/activate ;;
    ia-ai-server-4|AI-Server-6) source /storage/SSD2/hank/gpu_training/venv/bin/activate ;;
esac
"""

DEFAULT_REPO_DIR = "/storage/SSD2/hank/gpu_training"


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
) -> Path:
    """動態產生 sbatch script，回傳路徑"""
    GENERATED_SCRIPTS_DIR.mkdir(parents=True, exist_ok=True)

    nodelist_line = f"#SBATCH --nodelist={nodelist}" if nodelist else ""
    work_dir = repo_dir or DEFAULT_REPO_DIR

    if repo_url:
        git_sync = f"""
if [ ! -d "{work_dir}/.git" ]; then
    git clone {repo_url} {work_dir}
fi
cd {work_dir}
git fetch origin
git checkout {branch}
git pull origin {branch}
"""
    else:
        git_sync = f"""
cd {work_dir}
git pull origin {branch}
"""

    script = f"""#!/bin/bash
#SBATCH --job-name={job_name}
#SBATCH --gres=gpu:{gpu}
#SBATCH --cpus-per-task=4
#SBATCH --output=/tmp/slurm_{job_name}_%j.out
#SBATCH --time=02:00:00
{nodelist_line}
{VENV_ACTIVATE}
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
) -> dict:
    """提交 sbatch job。可指定現有 script_path 或直接給 command 動態產生"""
    if command:
        name = job_name or "job"
        path = generate_script(command, gpu=gpu, job_name=name, nodelist=nodelist, branch=branch, repo_dir=repo_dir, repo_url=repo_url)
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
                "nodes": parts[5] if len(parts) > 5 else "",
            })
    return jobs


def get_queue(user: Optional[str] = None) -> str:
    """查看 job queue"""
    cmd = [SQUEUE, "-o", "%.8i %15j %10u %10T %10M %N"]
    if user:
        cmd += ["-u", user]
    stdout, stderr, rc = run_cmd(cmd)
    return stdout if rc == 0 else f"Error: {stderr}"


def get_queue_json(user: Optional[str] = None) -> list[dict]:
    """查看 job queue，回傳結構化 JSON"""
    cmd = [SQUEUE, "-o", "%.8i %15j %10u %10T %10M %N"]
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
    from mcp.server.fastmcp import FastMCP

    mcp = FastMCP("Slurm Manager")

    @mcp.tool()
    def slurm_submit(
        command: str,
        gpu: int = 1,
        job_name: str = "job",
        nodelist: str = "",
        branch: str = "main",
        repo_dir: str = "",
        repo_url: str = "",
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
        """
        result = submit_job(
            command=command,
            gpu=gpu,
            job_name=job_name or "job",
            nodelist=nodelist or None,
            branch=branch,
            repo_dir=repo_dir,
            repo_url=repo_url,
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
      <div class="section-title">Job Queue</div>
      <div class="queue-wrap">
        <table>
          <thead><tr><th>Job ID</th><th>Name</th><th>User</th><th>State</th><th>Time</th><th>Node</th><th></th></tr></thead>
          <tbody id="queue-body"><tr><td colspan="7" class="empty-state">Loading...</td></tr></tbody>
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
        </div>
        <button class="btn-submit" id="btn-submit" onclick="submitJob()">Submit Job</button>
      </div>
    </div>
  </main>

  <div class="toast" id="toast"></div>

  <script>
    function parseCluster(raw) {
      const lines = raw.trim().split('\\n').filter(l => l && !l.startsWith('NODELIST'));
      return lines.map(line => {
        const parts = line.trim().split(/\\s+/);
        return { name: parts[0], gres: parts[1] || '', cpus: parts[2] || '', state: parts[3] || '' };
      });
    }

    function nodeCardHTML(node) {
      const state = node.state.toLowerCase();
      const stateClass = state.includes('idle') ? 'state-idle' :
                         state.includes('alloc') ? 'state-alloc' :
                         state.includes('mix') ? 'state-mix' : 'state-down';
      const cardClass = state.includes('idle') ? 'idle' : 'busy';

      // parse GPU count from gres like "gpu:2" or "gpu:a6000:2"
      const gpuMatch = node.gres.match(/gpu:(\d+)$/i) || node.gres.match(/gpu:[^:]+:(\d+)/i);
      const gpuCount = gpuMatch ? gpuMatch[1] : node.gres.replace('gpu:', '') || '?';
      const gpuModel = 'GPU';

      // parse CPU allocated/total from "A/I/O/T"
      const cpuParts = node.cpus.split('/');
      const cpuAlloc = parseInt(cpuParts[0]) || 0;
      const cpuTotal = parseInt(cpuParts[3]) || 1;
      const cpuPct = Math.round(cpuAlloc / cpuTotal * 100);

      return `
        <div class="node-card ${cardClass}">
          <div class="node-name">${node.name}</div>
          <div class="node-meta">GPU: ${gpuModel} × ${gpuCount} &nbsp;|&nbsp; CPU: ${cpuAlloc}/${cpuTotal}</div>
          <div class="gpu-bar-wrap"><div class="gpu-bar ${cpuPct > 80 ? 'full' : ''}" style="width:${cpuPct}%"></div></div>
          <span class="node-state ${stateClass}">${node.state}</span>
        </div>`;
    }

    function queueRowHTML(job) {
      const badgeClass = job.state === 'RUNNING' ? 'badge-running' :
                         job.state === 'PENDING' ? 'badge-pending' : 'badge-other';
      return `<tr>
        <td style="color:#94a3b8">${job.job_id}</td>
        <td style="color:#e2e8f0;font-weight:600">${job.name}</td>
        <td style="color:#94a3b8">${job.user}</td>
        <td><span class="badge ${badgeClass}">${job.state}</span></td>
        <td style="color:#64748b">${job.time}</td>
        <td style="color:#64748b">${job.nodes || '—'}</td>
        <td><button onclick="cancelJob('${job.job_id}')" style="background:none;border:1px solid #3b3460;color:#94a3b8;border-radius:4px;padding:2px 8px;cursor:pointer;font-size:11px">cancel</button></td>
      </tr>`;
    }

    async function refresh() {
      try {
        const [clusterRes, queueRes] = await Promise.all([
          fetch('/cluster'), fetch('/queue')
        ]);
        const clusterData = await clusterRes.json();
        const queueData = await queueRes.json();

        const nodes = parseCluster(clusterData.output || '');
        document.getElementById('cluster-grid').innerHTML =
          nodes.length ? nodes.map(nodeCardHTML).join('') : '<div style="color:#475569;padding:16px">No nodes found</div>';

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
      if (!command) { showToast('Command is required', 'error'); return; }
      const btn = document.getElementById('btn-submit');
      btn.disabled = true; btn.textContent = 'Submitting...';
      try {
        const res = await fetch('/submit', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            command,
            job_name: document.getElementById('f-jobname').value || 'job',
            gpu: parseInt(document.getElementById('f-gpu').value),
            branch: document.getElementById('f-branch').value || 'main',
            nodelist: document.getElementById('f-nodelist').value,
            repo_dir: document.getElementById('f-repodir').value,
            repo_url: document.getElementById('f-repourl').value,
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

    refresh();
    setInterval(refresh, 5000);
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
        gpu: int = 1
        job_name: str = "job"
        nodelist: str = ""
        branch: str = "main"
        repo_dir: str = ""           # e.g. "/storage/SSD2/alice/my_project"
        repo_url: str = ""           # e.g. "git@github.com:org/repo.git"
        script_path: str = ""        # legacy: 直接指定現有 script

    @app.post("/submit")
    def submit(req: SubmitRequest):
        result = submit_job(
            command=req.command or None,
            script_path=req.script_path or None,
            gpu=req.gpu,
            job_name=req.job_name or None,
            nodelist=req.nodelist or None,
            branch=req.branch,
            repo_dir=req.repo_dir,
            repo_url=req.repo_url,
        )
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["error"])
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

    @app.get("/cluster")
    def cluster():
        return {"output": get_cluster_info()}

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
                        "gpu": "GPU 數量 (預設 1)",
                        "job_name": "job 名稱 (預設 job)",
                        "nodelist": "指定節點 (選填)",
                        "branch": "git branch (預設 main)",
                        "repo_dir": "repo 路徑 (選填, 預設 /storage/SSD2/hank/gpu_training)",
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
