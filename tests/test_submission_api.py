import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

import slurm_server


class SubmissionApiBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(slurm_server.create_http_app())
        self.payload = {
            "command": "python train.py",
            "username": "alice",
            "venv": "ltx2",
            "job_name": "experiment",
            "gpu": 1,
        }

    @patch("slurm_server.record_submission")
    @patch("slurm_server.submit_job")
    def test_headerless_manual_submission_is_accepted_and_audited(self, submit_mock, record_mock):
        submit_mock.return_value = {"success": True, "submission_id": "manual-1", "job_id": "123"}
        response = self.client.post("/submit", json=self.payload)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["submission_source"], "manual-http")
        self.assertEqual(response.json()["venv_policy"], "explicit")
        submit_mock.assert_called_once()
        self.assertEqual(record_mock.call_args.kwargs["submission_source"], "manual-http")

    @patch("slurm_server.record_submission")
    @patch("slurm_server.submit_job")
    def test_unknown_source_is_rejected(self, submit_mock, record_mock):
        response = self.client.post("/submit", json=self.payload, headers={"X-Submission-Source": "untrusted"})
        self.assertEqual(response.status_code, 403)
        submit_mock.assert_not_called()
        record_mock.assert_not_called()

    @patch("slurm_server.record_submission")
    @patch("slurm_server.submit_job")
    def test_mcp_source_records_audit_metadata(self, submit_mock, record_mock):
        submit_mock.return_value = {
            "success": True,
            "submission_id": "submission-1",
            "job_id": "123",
        }

        response = self.client.post(
            "/submit",
            json=self.payload,
            headers={"X-Submission-Source": "mcp"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["submission_source"], "mcp")
        self.assertEqual(response.json()["status"], "submitted")
        submit_mock.assert_called_once()
        record_mock.assert_called_once()
        self.assertEqual(record_mock.call_args.kwargs["submission_source"], "mcp")
        self.assertEqual(record_mock.call_args.kwargs["submission_id"], "submission-1")

    @patch("slurm_server.record_submission")
    @patch("slurm_server.submit_job")
    def test_legacy_script_path_is_rejected(self, submit_mock, record_mock):
        payload = {**self.payload, "script_path": "/tmp/untrusted.sh"}

        response = self.client.post(
            "/submit",
            json=payload,
            headers={"X-Submission-Source": "mcp"},
        )

        self.assertEqual(response.status_code, 422)
        submit_mock.assert_not_called()
        record_mock.assert_not_called()

    @patch("slurm_server.record_submission")
    @patch("slurm_server.submit_job")
    def test_missing_venv_is_rejected(self, submit_mock, record_mock):
        payload = {**self.payload, "venv": " "}

        response = self.client.post(
            "/submit",
            json=payload,
            headers={"X-Submission-Source": "internal-ui"},
        )

        self.assertEqual(response.status_code, 400)
        submit_mock.assert_not_called()
        record_mock.assert_not_called()

    def test_health_endpoint_is_read_only(self):
        with patch("slurm_server.get_cluster_info") as cluster_mock:
            response = self.client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "status": "ok",
                "service": "slurm-api",
                "version": slurm_server.SERVICE_VERSION,
            },
        )
        cluster_mock.assert_not_called()

    def test_legacy_embedded_mcp_is_disabled(self):
        with self.assertRaisesRegex(RuntimeError, "Embedded MCP is disabled"):
            slurm_server.run_mcp_server()

    @patch("slurm_server.write_recovery_record", return_value="/recovery/submission-1.json")
    @patch("slurm_server.record_submission", side_effect=sqlite3.OperationalError("disk full"))
    @patch("slurm_server.submit_job")
    def test_metadata_failure_reports_real_job_id_and_recovery_record(
        self, submit_mock, record_mock, recovery_mock
    ):
        submit_mock.return_value = {
            "success": True,
            "submission_id": "submission-1",
            "job_id": "123",
            "script_path": "/scripts/submission-1/job.sh",
            "log_path": "/logs/submission-1/slurm_123.out",
            "run_path": "/runs/submission-1",
        }

        response = self.client.post(
            "/submit",
            json=self.payload,
            headers={"X-Submission-Source": "mcp"},
        )

        self.assertEqual(response.status_code, 500)
        detail = response.json()["detail"]
        self.assertEqual(detail["status"], "metadata_finalize_failed")
        self.assertEqual(detail["job_id"], "123")
        self.assertEqual(detail["submission_id"], "submission-1")
        record_mock.assert_called_once()
        recovery_mock.assert_called_once()

    @patch("slurm_server.get_submission_by_job_id")
    def test_log_lookup_uses_exact_metadata_path(self, lookup_mock):
        with tempfile.TemporaryDirectory() as temp_dir:
            expected_log = Path(temp_dir) / "expected.out"
            decoy_log = Path(temp_dir) / "decoy_123.out"
            expected_log.write_text("expected log")
            decoy_log.write_text("wrong log")
            lookup_mock.return_value = {
                "job_id": "123",
                "log_path": str(expected_log),
            }

            response = self.client.get("/logs/123")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["file"], str(expected_log))
        self.assertEqual(response.json()["log"], "expected log")
        lookup_mock.assert_called_once_with("123")


if __name__ == "__main__":
    unittest.main()