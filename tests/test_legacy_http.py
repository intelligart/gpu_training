"""Regression tests: no real submissions, no CUDA or model execution."""

import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
import slurm_server


class LegacyHttpTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(slurm_server.create_http_app())
        self.original = {
            "command": "python3 -u test_case1_single_gpu.py", "gpu": 1,
            "job_name": "test-1", "repo_dir": "/storage/SSD2/hank/gpu_training",
        }

    def post_mocked(self, payload, headers=None):
        with patch.object(slurm_server, "submit_job", return_value={
            "success": True, "submission_id": "legacy-1", "job_id": "123",
        }) as submit, patch.object(slurm_server, "record_submission") as record:
            response = self.client.post("/submit", json=payload, headers=headers)
            return response, submit, record

    def test_original_request_without_username_or_venv(self):
        response, submit, record = self.post_mocked(self.original)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(submit.call_args.kwargs["username"], "hank")
        self.assertEqual(submit.call_args.kwargs["venv"], "")
        self.assertEqual(response.json()["venv_policy"], "node-default")
        payload = json.loads(record.call_args.kwargs["request_payload"])
        self.assertEqual(payload["node_default_venvs"], slurm_server.get_legacy_node_venvs())

    def test_original_alice_git_request(self):
        payload = {**self.original, "username": "alice", "repo_dir": "/storage/SSD2/slurmjob/alice/gpu_training",
                   "repo_url": "git@github.com:intelligart/gpu_training.git"}
        response, submit, _ = self.post_mocked(payload)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(submit.call_args.kwargs["username"], "alice")

    def test_hank_demo_branch_preserved(self):
        payload = {**self.original, "username": "hank", "command": "python3 -u hank_demo.py",
                   "repo_url": "git@github.com:intelligart/gpu_training.git", "branch": "hank/demo", "venv": "ltx2"}
        response, submit, _ = self.post_mocked(payload)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(submit.call_args.kwargs["branch"], "hank/demo")
        self.assertEqual(submit.call_args.kwargs["command"], "python3 -u hank_demo.py")
        self.assertEqual(response.json()["venv_policy"], "explicit")

    def test_mcp_still_requires_username_and_venv(self):
        for removed in ("username", "venv"):
            payload = {"command": "python3 -u hank_demo.py", "username": "hank", "venv": "ltx2"}
            payload.pop(removed)
            response, submit, record = self.post_mocked(payload, {"X-Submission-Source": "mcp"})
            self.assertEqual(response.status_code, 400)
            submit.assert_not_called()
            record.assert_not_called()

    def test_arbitrary_repo_dir_still_rejected(self):
        response, submit, _ = self.post_mocked({**self.original, "repo_dir": "/etc"})
        self.assertEqual(response.status_code, 400)
        submit.assert_not_called()

    def test_invalid_default_configuration_rejected_before_submit(self):
        for mapping in ('not json', '{}', '{"bad node": "/tmp/venv"}', '{"node": "relative"}'):
            with patch.dict(os.environ, GPU_PLATFORM_NODE_VENVS=mapping):
                response, submit, _ = self.post_mocked(self.original)
                self.assertEqual(response.status_code, 400)
                submit.assert_not_called()

    def test_unconfigured_target_fails_before_submit(self):
        response, submit, _ = self.post_mocked({**self.original, "nodelist": "ia-ai-server-5090"})
        self.assertEqual(response.status_code, 400)
        submit.assert_not_called()


class JobEnvironmentTests(unittest.TestCase):
    def run_environment(self, venv, node, mapping):
        with patch.dict(os.environ, GPU_PLATFORM_NODE_VENVS=json.dumps(mapping)):
            script = "set -e\n" + slurm_server.render_job_environment(venv) + "\nprintf 'USER_COMMAND_REACHED\\n'\n"
        return subprocess.run(["bash", "-c", script], env={**os.environ, "SLURMD_NODENAME": node},
                              capture_output=True, text=True, timeout=10)

    def create_fixture(self, root):
        directory = root / "venv with spaces" / "bin"
        directory.mkdir(parents=True)
        (directory / "activate").write_text("export VIRTUAL_ENV=/wrong/old/location\n")
        for name in ("python", "python3"):
            # Shell stub only: these tests never execute a model/interpreter.
            executable = directory / name
            executable.write_text("#!/bin/sh\nexit 0\n")
            executable.chmod(0o755)
        return directory.parent

    def test_valid_worker_mapping_selected_and_logged(self):
        with tempfile.TemporaryDirectory() as temporary:
            venv = self.create_fixture(Path(temporary))
            result = self.run_environment("", "fixture-node", {"fixture-node": str(venv)})
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn(f"venv={venv}", result.stdout)
            self.assertIn("USER_COMMAND_REACHED", result.stdout)

    def test_explicit_venv_overrides_default_map(self):
        with tempfile.TemporaryDirectory() as temporary:
            venv = self.create_fixture(Path(temporary))
            result = self.run_environment(str(venv), "fixture-node", {"fixture-node": "/does/not/exist"})
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn(f"venv={venv}", result.stdout)

    def test_missing_node_or_broken_interpreter_never_runs_command(self):
        with tempfile.TemporaryDirectory() as temporary:
            venv = self.create_fixture(Path(temporary))
            (venv / "bin" / "python").unlink()
            (venv / "bin" / "python").symlink_to("/nonexistent/python3.10")
            for node in ("fixture-node", "unknown-node"):
                result = self.run_environment("", node, {"fixture-node": str(venv)})
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn("USER_COMMAND_REACHED", result.stdout)
                self.assertIn("ERROR:", result.stderr)

    def test_nonstarting_interpreter_or_failed_activation_stops_command(self):
        with tempfile.TemporaryDirectory() as temporary:
            venv = self.create_fixture(Path(temporary))
            (venv / "bin" / "python").write_text("#!/bin/sh\nexit 127\n")
            result = self.run_environment(str(venv), "fixture-node", {})
            self.assertNotEqual(result.returncode, 0)
            self.assertNotIn("USER_COMMAND_REACHED", result.stdout)
            self.assertIn("interpreter cannot start", result.stderr)
            (venv / "bin" / "python").write_text("#!/bin/sh\nexit 0\n")
            (venv / "bin" / "activate").write_text("false\n")
            result = self.run_environment(str(venv), "fixture-node", {})
            self.assertNotEqual(result.returncode, 0)
            self.assertNotIn("USER_COMMAND_REACHED", result.stdout)