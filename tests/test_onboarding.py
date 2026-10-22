import inspect
import unittest
from unittest.mock import patch

from onboarding import GUIDE_VERSION, get_guide
from tests.test_mcp_submission import mcp_server


class OnboardingTests(unittest.TestCase):
    def test_checklist_and_honest_limits(self):
        guide = get_guide()
        for expected in (
            GUIDE_VERSION, "username", "program", "dataset", "不需要", "venv",
            "resources", "output", "worker preflight", "shared-hank",
            "尚未啟用 sandbox", "沒有強制", "使用規範", "Bubblewrap",
            "<MCP_ENDPOINT>", "不需要安裝 MCP server",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, guide)
        self.assertNotIn("192.168.", guide)

    def test_three_surfaces_are_identical_and_have_no_side_effects(self):
        with patch("builtins.open", side_effect=AssertionError("filesystem accessed")):
            self._assert_no_side_effects()

    def _assert_no_side_effects(self):
        with patch.object(mcp_server, "_api", side_effect=AssertionError("backend called")) as api:
            with patch.object(mcp_server, "submit_job") as submit:
                with patch.object(mcp_server, "cancel_job") as cancel:
                    for surface in (
                        mcp_server.get_onboarding_guide,
                        mcp_server.onboarding_resource,
                        mcp_server.onboarding_prompt,
                    ):
                        self.assertEqual(surface(), get_guide())
                    api.assert_not_called()
                    submit.assert_not_called()
                    cancel.assert_not_called()

    def test_safe_workflow_templates(self):
        guide = get_guide()
        for expected in (
            "缺資料先問清楚", "不得猜測", "cluster_info", "list_venvs",
            "本次明確確認", "client 指引", "gpu=1", "gpu=2", "torchrun",
            "submission_id", "job_id", "status", "source_commit",
            "list_jobs", "job_history", "get_logs", "exact log",
            "取消第一步", "取消第二步", "cancel_job", "terminal state",
            "停止並回報", "不得降級", "raw API fallback", "手動 workload",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, guide)

    def test_existing_submission_signature_is_unchanged(self):
        self.assertEqual(
            tuple(inspect.signature(mcp_server.submit_job).parameters),
            ("command", "username", "venv", "gpu", "job_name", "nodelist", "repo_url", "branch", "mem"),
        )