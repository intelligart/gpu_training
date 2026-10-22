import hashlib
from pathlib import Path
import subprocess
import tarfile
import tempfile
import os
import unittest

from tests.test_onboarding_protocol import run_probe


class OnboardingPackagingTests(unittest.TestCase):
    def test_clean_artifact_imports_protocol_and_reproducibility(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            digests = []
            for name in ("first", "second"):
                output = base / name
                subprocess.run(
                    ["bash", str(root / "scripts/build-platform-v1-artifact.sh")],
                    cwd=root, env=dict(os.environ, ARTIFACT_OUTPUT_DIR=str(output)),
                    check=True, capture_output=True, text=True,
                )
                artifact, = output.glob("gpu-platform-v*.tar.gz")
                digests.append(hashlib.sha256(artifact.read_bytes()).hexdigest())
                with tarfile.open(artifact) as archive:
                    names = archive.getnames()
                    self.assertTrue(any(path.endswith("/onboarding.py") for path in names))
                    destination = (output / "clean").resolve()
                    # Python 3.10.12 predates tarfile's extraction filters.
                    for member in archive.getmembers():
                        target = (destination / member.name).resolve()
                        self.assertTrue(target.is_relative_to(destination))
                        self.assertTrue(member.isfile() or member.isdir())
                    archive.extractall(destination)
                release, = (output / "clean").iterdir()
                self.assertIn("BACKEND_CALLS=0", run_probe(release))
            self.assertEqual(digests[0], digests[1])