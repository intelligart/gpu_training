"""Real SDK walkthrough in a separate process, away from legacy fake SDKs."""

import os
from pathlib import Path
import subprocess
import sys
import unittest


PROTOCOL_PROBE = r'''
import anyio
from importlib.metadata import version
from unittest.mock import patch
from mcp import ClientSession
from mcp.shared.memory import create_client_server_memory_streams
import mcp_server
from onboarding import GUIDE_URI, PROMPT_NAME, get_guide

assert version("mcp") == "2.2.0", "Use deploy/platform-v1/requirements-service.lock"

async def walkthrough():
    with patch.object(mcp_server, "_api", side_effect=AssertionError("backend forbidden")) as api:
        async with create_client_server_memory_streams() as (client_streams, server_streams):
            async with anyio.create_task_group() as tasks:
                # Pinned MCP 2.2.0 exposes the low-level stream server here;
                # use in-memory transport instead of a live HTTP endpoint.
                tasks.start_soon(
                    mcp_server.mcp._lowlevel_server.run,
                    *server_streams,
                    mcp_server.mcp._lowlevel_server.create_initialization_options(),
                )
                async with ClientSession(*client_streams) as client:
                    initialized = await client.initialize()
                    assert "get_onboarding_guide" in initialized.instructions
                    tools = await client.list_tools()
                    guide_tool = next(tool for tool in tools.tools if tool.name == "get_onboarding_guide")
                    assert not guide_tool.input_schema.get("required")
                    submission = next(tool for tool in tools.tools if tool.name == "submit_job")
                    assert set(submission.input_schema["required"]) == {"command", "username", "venv"}
                    tool_result = await client.call_tool("get_onboarding_guide", {})
                    assert not tool_result.is_error
                    assert tool_result.content[0].text == get_guide()
                    print("TOOLS_ONLY_WALKTHROUGH=PASS")
                    resources = await client.list_resources()
                    assert GUIDE_URI in [str(resource.uri) for resource in resources.resources]
                    resource = await client.read_resource(GUIDE_URI)
                    assert resource.contents[0].text == get_guide()
                    prompts = await client.list_prompts()
                    assert PROMPT_NAME in [prompt.name for prompt in prompts.prompts]
                    prompt = await client.get_prompt(PROMPT_NAME)
                    assert prompt.messages[0].content.text == get_guide()
                    print("RESOURCE_PROMPT_WALKTHROUGH=PASS")
                    api.assert_not_called()
                tasks.cancel_scope.cancel()

anyio.run(walkthrough)
print("BACKEND_CALLS=0; SUBMISSION_SCHEMA=UNCHANGED")
'''


def run_probe(directory: Path) -> str:
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONNOUSERSITE="1")
    env.pop("PYTHONPATH", None)
    env.pop("PYTHONHOME", None)
    result = subprocess.run(
        [sys.executable, "-c", PROTOCOL_PROBE], cwd=directory, env=env,
        capture_output=True, text=True, timeout=45,
    )
    if result.returncode:
        raise AssertionError(result.stdout + result.stderr)
    return result.stdout


class OnboardingProtocolTests(unittest.TestCase):
    def test_real_sdk_read_only_client_walkthroughs(self):
        output = run_probe(Path(__file__).resolve().parents[1])
        self.assertIn("TOOLS_ONLY_WALKTHROUGH=PASS", output)
        self.assertIn("RESOURCE_PROMPT_WALKTHROUGH=PASS", output)
        self.assertIn("BACKEND_CALLS=0", output)