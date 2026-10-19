import inspect
import json
import sys
import types
import unittest
from unittest.mock import patch

import httpx


class _FakeMCPServer:
    def __init__(self, *args, **kwargs):
        pass

    def tool(self):
        return lambda function: function


mcp_module = types.ModuleType("mcp")
mcp_server_package = types.ModuleType("mcp.server")
mcpserver_module = types.ModuleType("mcp.server.mcpserver")
mcpserver_module.MCPServer = _FakeMCPServer
sys.modules.setdefault("mcp", mcp_module)
sys.modules.setdefault("mcp.server", mcp_server_package)
sys.modules.setdefault("mcp.server.mcpserver", mcpserver_module)

import mcp_server


class SubmitJobContractTests(unittest.TestCase):
    @patch("mcp_server._api")
    def test_gpu_status_handles_live_mb_metrics_and_process_text(self, api_mock):
        api_mock.return_value = {"node": {"state": "idle", "gpus": [
            {"index": 0, "name": "A6000", "mem_used_mb": 38511, "mem_total_mb": 49140,
             "util_pct": 100, "processes": "other/python (37638MB), hank/python (824MB)"},
            {"index": 1, "name": "A6000", "mem_used_mb": 0, "mem_total_mb": 49140,
             "util_pct": 0, "processes": ""}
        ]}}
        result = mcp_server.gpu_status()
        api_mock.assert_called_once_with("GET", "/gpu-status")
        self.assertIn("38511/49140 MB  util=100%", result)
        self.assertIn("other/python (37638MB), hank/python (824MB)", result)
        self.assertIn("0/49140 MB  util=0%", result)
        self.assertNotIn("?/? GB", result)

    @patch("mcp_server._api")
    def test_gpu_status_does_not_mix_partial_mb_metrics_with_legacy_gb(self, api_mock):
        api_mock.return_value = {"node": [{"mem_used_mb": 512, "mem_total_gb": 48}]}
        self.assertIn("512/? MB", mcp_server.gpu_status())

    @patch("mcp_server._api")
    def test_gpu_status_rejects_invalid_process_telemetry(self, api_mock):
        for processes in (None, 42, ["invalid"]):
            with self.subTest(processes=processes):
                api_mock.return_value = {"node": [{"processes": processes}]}
                with self.assertRaisesRegex(ValueError, "Invalid GPU process telemetry"):
                    mcp_server.gpu_status()

    @patch("mcp_server._api")
    def test_gpu_status_handles_nested_backend_devices_and_processes(self, api_mock):
        api_mock.return_value = {"node": {"state": "idle", "gpus": [
            {"index": 0, "name": "A6000", "mem_used_gb": 38, "mem_total_gb": 48,
             "utilization": 100, "processes": [{"user": "other", "name": "trainer", "used_memory_mb": 38000}]}
        ]}}
        result = mcp_server.gpu_status()
        self.assertIn("State: idle", result)
        self.assertIn("GPU 0: A6000", result)
        self.assertIn("other: trainer", result)
        self.assertIn("util=100%", result)

    @patch("mcp_server._api")
    def test_gpu_status_preserves_legacy_errors_and_missing_telemetry(self, api_mock):
        api_mock.return_value = {"old": [{"index": 1, "name": "legacy"}],
                                 "offline": {"error": "unreachable"}, "missing": {"state": "idle", "gpus": []}}
        result = mcp_server.gpu_status()
        self.assertIn("GPU 1: legacy", result)
        self.assertIn("Error: unreachable", result)
        self.assertIn("do not infer availability", result)

    def test_submit_job_schema_requires_venv(self):
        signature = inspect.signature(mcp_server.submit_job)

        self.assertIs(signature.parameters["venv"].default, inspect.Parameter.empty)

    @patch("mcp_server._api")
    def test_missing_username_is_rejected_without_backend_call(self, api_mock):
        result = mcp_server._submit_job_request("python train.py", " ", venv="ltx2")

        self.assertIn("username and venv are required", result)
        api_mock.assert_not_called()

    @patch("mcp_server._api")
    def test_missing_venv_is_rejected_without_backend_call(self, api_mock):
        result = mcp_server._submit_job_request("python train.py", "alice", venv=" ")

        self.assertIn("username and venv are required", result)
        api_mock.assert_not_called()

    @patch("mcp_server._api")
    def test_success_requires_and_returns_submission_and_job_ids(self, api_mock):
        api_mock.return_value = {
            "success": True,
            "submission_id": "submission-1",
            "job_id": "123",
            "status": "submitted",
        }

        result = json.loads(
            mcp_server._submit_job_request("python train.py", " alice ", venv=" ltx2 ")
        )

        self.assertEqual(result["submission_id"], "submission-1")
        self.assertEqual(result["job_id"], "123")
        self.assertEqual(result["status"], "submitted")
        api_mock.assert_called_once_with(
            "POST",
            "/submit",
            json={
                "command": "python train.py",
                "username": "alice",
                "gpu": 1,
                "job_name": "job",
                "nodelist": "",
                "repo_url": "",
                "branch": "main",
                "venv": "ltx2",
                "mem": "",
            },
            headers={"X-Submission-Source": "mcp"},
        )

    @patch("mcp_server._api")
    def test_incomplete_backend_success_is_rejected(self, api_mock):
        api_mock.return_value = {"success": True, "job_id": "123"}

        result = mcp_server._submit_job_request("python train.py", "alice", venv="ltx2")

        self.assertIn("incomplete success response", result)

    @patch("mcp_server._api")
    def test_backend_http_failure_is_reported_without_success(self, api_mock):
        request = httpx.Request("POST", "http://internal/submit")
        response = httpx.Response(503, request=request, text="unavailable")
        api_mock.side_effect = httpx.HTTPStatusError(
            "service unavailable", request=request, response=response
        )

        result = mcp_server._submit_job_request("python train.py", "alice", venv="ltx2")

        self.assertEqual(result, "Error: unavailable")

    @patch("mcp_server._api")
    def test_job_history_includes_submission_and_short_commit(self, api_mock):
        api_mock.return_value = {
            "jobs": [
                {
                    "job_id": "123",
                    "submission_id": "0123456789abcdef0123456789abcdef",
                    "source_commit": "abcdef0123456789abcdef0123456789abcdef01",
                    "job_name": "experiment",
                    "username": "alice",
                    "status": "COMPLETED",
                    "nodelist": "ia-ai-server-4",
                },
                {
                    "job_id": "122",
                    "job_name": "legacy-job",
                    "username": "alice",
                    "status": "COMPLETED",
                    "nodelist": "ia-ai-server-5",
                },
            ]
        }

        result = mcp_server.job_history()

        self.assertIn("Submission", result)
        self.assertIn("Commit", result)
        self.assertIn("0123456789abcdef0123456789abcdef", result)
        self.assertIn("abcdef012345", result)
        self.assertNotIn("abcdef0123456789abcdef0123456789abcdef01", result)
        self.assertIn("legacy", result)


if __name__ == "__main__":
    unittest.main()