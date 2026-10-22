import subprocess
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

import slurm_server


class SourcePreparationTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name)
        self.remote = self.root / "remote.git"
        self.work = self.root / "work"
        self._git("init", "--bare", str(self.remote))
        self._git("init", str(self.work))
        self._git("-C", str(self.work), "config", "user.name", "Test User")
        self._git("-C", str(self.work), "config", "user.email", "test@example.com")
        self._git("-C", str(self.work), "checkout", "-b", "main")
        self._write_and_push("v1")

        self.cache_patch = patch.object(
            slurm_server, "SOURCE_CACHE_BASE", self.root / "cache"
        )
        self.runs_patch = patch.object(slurm_server, "RUNS_BASE", self.root / "runs")
        self.cache_patch.start()
        self.runs_patch.start()
        self.addCleanup(self.cache_patch.stop)
        self.addCleanup(self.runs_patch.stop)

    def _git(self, *args):
        return subprocess.run(
            ["git", *args],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()

    def _write_and_push(self, value):
        (self.work / "version.txt").write_text(value)
        self._git("-C", str(self.work), "add", "version.txt")
        self._git("-C", str(self.work), "commit", "-m", value)
        self._git(
            "-C",
            str(self.work),
            "push",
            str(self.remote),
            "main:main",
        )

    def _prepare(self, submission_id):
        return slurm_server.prepare_submission_source(
            submission_id=submission_id,
            username="alice",
            branch="main",
            repo_url=str(self.remote),
        )

    def test_branch_update_does_not_change_existing_run(self):
        first = self._prepare("submission-1")
        self._write_and_push("v2")

        second = self._prepare("submission-2")

        self.assertNotEqual(first["source_commit"], second["source_commit"])
        self.assertEqual(Path(first["run_path"], "version.txt").read_text(), "v1")
        self.assertEqual(Path(second["run_path"], "version.txt").read_text(), "v2")
        self.assertFalse(Path(first["run_path"], ".git", "config").read_text().find("origin") >= 0)

    def test_concurrent_preparation_uses_distinct_run_directories(self):
        submission_ids = [f"concurrent-{index}" for index in range(8)]

        with ThreadPoolExecutor(max_workers=8) as executor:
            results = list(executor.map(self._prepare, submission_ids))

        run_paths = {result["run_path"] for result in results}
        commits = {result["source_commit"] for result in results}
        self.assertEqual(len(run_paths), 8)
        self.assertEqual(len(commits), 1)
        for result in results:
            self.assertEqual(Path(result["run_path"], "version.txt").read_text(), "v1")


if __name__ == "__main__":
    unittest.main()