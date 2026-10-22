import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import slurm_server


class CleanupTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name)
        self.db_path = self.root / "history.db"
        self.db_patch = patch.object(slurm_server, "DB_PATH", self.db_path)
        self.runs_patch = patch.object(slurm_server, "RUNS_BASE", self.root / "runs")
        self.scripts_patch = patch.object(
            slurm_server, "GENERATED_SCRIPTS_DIR", self.root / "scripts"
        )
        self.logs_patch = patch.object(slurm_server, "NAS_LOGS_DIR", self.root / "logs")
        for patcher in (
            self.db_patch,
            self.runs_patch,
            self.scripts_patch,
            self.logs_patch,
        ):
            patcher.start()
            self.addCleanup(patcher.stop)
        slurm_server.init_db()

    def _record_old_submission(self, submission_id, job_id):
        run_path = slurm_server.RUNS_BASE / "alice" / submission_id
        script_path = slurm_server.GENERATED_SCRIPTS_DIR / submission_id / "job.sh"
        log_path = slurm_server.NAS_LOGS_DIR / "alice" / submission_id / f"slurm_{job_id}.out"
        run_path.mkdir(parents=True)
        script_path.parent.mkdir(parents=True)
        log_path.parent.mkdir(parents=True)
        (run_path / "source.txt").write_text(submission_id)
        script_path.write_text("#!/bin/bash\n")
        log_path.write_text(submission_id)
        slurm_server.record_submission(
            submission_id=submission_id,
            job_id=job_id,
            username="alice",
            job_name="experiment",
            command="python train.py",
            gpu=1,
            run_path=str(run_path),
            script_path=str(script_path),
            log_path=str(log_path),
            status="submitted",
        )
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "UPDATE jobs SET submit_time = '2020-01-01 00:00:00' WHERE submission_id = ?",
            (submission_id,),
        )
        conn.commit()
        conn.close()
        return run_path, script_path, log_path

    @patch("slurm_server.get_active_job_ids", return_value={"101"})
    def test_cleanup_preserves_active_artifacts_and_removes_inactive(self, active_mock):
        active_paths = self._record_old_submission("active-submission", "101")
        inactive_paths = self._record_old_submission("inactive-submission", "102")

        dry_run = slurm_server.cleanup_old_jobs(days=30, dry_run=True)

        self.assertEqual(
            {item["submission_id"] for item in dry_run["skipped_active"]},
            {"active-submission"},
        )
        self.assertTrue(all(path.exists() for path in active_paths + inactive_paths))

        result = slurm_server.cleanup_old_jobs(days=30, dry_run=False)

        self.assertEqual(
            {item["submission_id"] for item in result["deleted"]},
            {"inactive-submission"},
        )
        self.assertIsNotNone(slurm_server.get_submission("active-submission"))
        self.assertIsNone(slurm_server.get_submission("inactive-submission"))
        self.assertTrue(all(path.exists() for path in active_paths))
        self.assertTrue(all(not path.exists() for path in inactive_paths))
        self.assertEqual(active_mock.call_count, 2)

    @patch("slurm_server.run_cmd", return_value=("", "controller unavailable", 1))
    def test_cleanup_fails_closed_when_slurm_status_is_unavailable(self, run_mock):
        self._record_old_submission("preserved-submission", "201")

        with self.assertRaises(slurm_server.SlurmStatusError):
            slurm_server.cleanup_old_jobs(days=30, dry_run=False)

        self.assertIsNotNone(slurm_server.get_submission("preserved-submission"))
        run_mock.assert_called_once()


if __name__ == "__main__":
    unittest.main()