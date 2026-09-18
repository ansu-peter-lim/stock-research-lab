import json
import tempfile
import unittest
from pathlib import Path

from orchestrator.core import Job, JobStore, run_job


class FakeResult:
    final_response = "done"


class FakeThread:
    id = "thread-test-123"

    def __init__(self, calls):
        self.calls = calls

    def run(self, prompt, effort, sandbox):
        self.calls.append((prompt, effort, sandbox))
        return FakeResult()


class FakeCodex:
    def __init__(self, calls):
        self.calls = calls

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def thread_start(self, cwd, sandbox):
        self.calls.append(("thread_start", cwd, sandbox))
        return FakeThread(self.calls)

    def thread_resume(self, thread_id, cwd, sandbox):
        self.calls.append(("thread_resume", thread_id, cwd, sandbox))
        return FakeThread(self.calls)


def write_job(folder, **overrides):
    values = {
        "job_id": "TEST-001",
        "objective": "test",
        "reasoning_tier": "medium",
        "prompt": "do test",
    }
    values.update(overrides)
    path = Path(folder) / "test.toml"
    lines = []
    for key, value in values.items():
        lines.append(f'{key} = {json.dumps(value)}')
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


class OrchestratorTests(unittest.TestCase):
    def test_reasoning_tier_mapping(self):
        self.assertEqual(Job("a", "b", "low", "p").reasoning_tier, "low")
        self.assertEqual(Job("a", "b", "medium", "p").reasoning_tier, "medium")
        self.assertEqual(Job("a", "b", "high", "p").reasoning_tier, "high")

    def test_xhigh_rejected(self):
        with self.assertRaises(ValueError):
            Job("a", "b", "xhigh", "p")

    def test_default_read_only_and_explicit_workspace_write(self):
        self.assertEqual(Job("a", "b", "low", "p").sandbox, "read-only")
        self.assertEqual(Job("a", "b", "low", "p", sandbox="workspace-write").sandbox, "workspace-write")

    def test_state_transitions(self):
        job = Job("a", "b", "low", "p")
        for status in ("running", "review", "accepted"):
            job.transition(status)
        self.assertEqual(job.status, "accepted")
        with self.assertRaises(ValueError):
            job.transition("running")

    def test_thread_id_persistence_and_result(self):
        with tempfile.TemporaryDirectory() as tmp:
            calls = []
            path = write_job(tmp)
            job = run_job(path, codex_factory=lambda: FakeCodex(calls))
            self.assertEqual(job.status, "review")
            self.assertEqual(job.thread_id, "thread-test-123")
            self.assertTrue(Path(tmp, "results", "TEST-001", "response.md").exists())
            state = Path(tmp, "test.state.json")
            self.assertEqual(json.loads(state.read_text())["thread_id"], "thread-test-123")
            self.assertEqual(calls[1][1], "medium")
            self.assertEqual(calls[0][2].value, "read-only")

    def test_existing_thread_id_is_resumed(self):
        with tempfile.TemporaryDirectory() as tmp:
            calls = []
            path = write_job(tmp, thread_id="thread-existing")
            job = run_job(path, codex_factory=lambda: FakeCodex(calls))
            self.assertEqual(calls[0][0:2], ("thread_resume", "thread-existing"))
            self.assertEqual(job.thread_id, "thread-test-123")


if __name__ == "__main__":
    unittest.main()
