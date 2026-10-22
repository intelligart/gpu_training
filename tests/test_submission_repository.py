import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import slurm_server


class SubmissionRepositoryTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.db_path = Path(self.temp_dir.name) / "history.db"
        self.db_patch = patch.object(slurm_server, "DB_PATH", self.db_path)
        self.db_patch.start()
        self.addCleanup(self.db_patch.stop)

    def _create_legacy_database(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            """
            CREATE TABLE jobs (
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
            """
        )
        conn.execute(
            """
            INSERT INTO jobs (
                job_id, username, job_name, command, gpu, nodelist,
                repo_dir, repo_url, branch, submit_time
            ) VALUES ('41', 'legacy-user', 'legacy-job', 'python old.py', 1, '', '', '', 'main', '2025-01-01 00:00:00')
            """
        )
        conn.commit()
        conn.close()

    def test_additive_migration_preserves_legacy_rows(self):
        self._create_legacy_database()

        slurm_server.init_db()

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM jobs WHERE job_id = '41'").fetchone()
        columns = {item[1] for item in conn.execute("PRAGMA table_info(jobs)")}
        conn.close()

        self.assertIsNotNone(row)
        self.assertEqual(row["username"], "legacy-user")
        self.assertIsNone(row["submission_id"])
        self.assertEqual(row["status"], "legacy")
        self.assertTrue(set(slurm_server.SUBMISSION_COLUMNS).issubset(columns))

    def test_submission_metadata_round_trips_and_id_is_unique(self):
        slurm_server.init_db()
        values = {
            "submission_id": "submission-1",
            "job_id": "123",
            "username": "alice",
            "job_name": "experiment",
            "command": "python train.py",
            "gpu": 1,
            "source_identity": "git@example/repo.git@main",
            "source_commit": "abc123",
            "run_path": "/runs/submission-1",
            "script_path": "/scripts/submission-1/job.sh",
            "log_path": "/logs/submission-1/123.out",
            "request_payload": '{"gpu": 1}',
            "status": "submitted",
            "submission_source": "mcp",
        }

        slurm_server.record_submission(**values)

        row = slurm_server.get_submission("submission-1")
        self.assertEqual(row["job_id"], "123")
        self.assertEqual(row["source_commit"], "abc123")
        self.assertEqual(row["log_path"], "/logs/submission-1/123.out")
        with self.assertRaises(sqlite3.IntegrityError):
            slurm_server.record_submission(**values)


if __name__ == "__main__":
    unittest.main()