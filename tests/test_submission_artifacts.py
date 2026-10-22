import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

import slurm_server


class SubmissionArtifactTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        root = Path(self.temp_dir.name)
        self.scripts_patch = patch.object(
            slurm_server, "GENERATED_SCRIPTS_DIR", root / "scripts"
        )
        self.logs_patch = patch.object(slurm_server, "NAS_LOGS_DIR", root / "logs")
        self.scripts_patch.start()
        self.logs_patch.start()
        self.addCleanup(self.scripts_patch.stop)
        self.addCleanup(self.logs_patch.stop)

    @patch(
        "slurm_server.prepare_submission_source",
        return_value={
            "source_identity": "/tmp/repo",
            "source_commit": "abc123",
            "run_path": "/tmp/repo",
        },
    )
    @patch("slurm_server.run_cmd", return_value=("Submitted batch job 123", "", 0))
    def test_same_user_and_job_name_get_unique_complete_artifacts(
        self, run_mock, prepare_mock
    ):
        def submit(index):
            return slurm_server.submit_job(
                command=f"python train.py --run {index}",
                username="alice",
                venv="ltx2",
                job_name="experiment",
                repo_dir="/tmp/repo",
            )

        with ThreadPoolExecutor(max_workers=8) as executor:
            results = list(executor.map(submit, range(16)))

        submission_ids = {result["submission_id"] for result in results}
        script_paths = {result["script_path"] for result in results}
        log_paths = {result["log_path"] for result in results}
        self.assertEqual(len(submission_ids), 16)
        self.assertEqual(len(script_paths), 16)
        self.assertEqual(len(log_paths), 16)
        self.assertEqual(run_mock.call_count, 16)
        self.assertEqual(prepare_mock.call_count, 16)

        for index, result in enumerate(results):
            script_path = Path(result["script_path"])
            content = script_path.read_text()
            self.assertIn("#SBATCH --job-name=experiment", content)
            self.assertIn(f"python train.py --run {index}", content)
            self.assertIn(result["submission_id"], result["script_path"])
            self.assertIn(result["submission_id"], result["log_path"])
            self.assertFalse(any(script_path.parent.glob("*.tmp")))


if __name__ == "__main__":
    unittest.main()