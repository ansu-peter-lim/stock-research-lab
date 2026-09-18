import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from orchestrator.core import MODEL_TIERS, Job, JobStore, create_job_file, render_monitor, run_job
from orchestrator.__main__ import main


class FakeResult:
    final_response = "done"


class UsageResult:
    final_response = "done"
    model = "codex-test"
    usage = {"total_tokens": 17}


class FakeThread:
    id = "thread-test-123"

    def __init__(self, calls):
        self.calls = calls

    def run(self, prompt, effort, sandbox, model=None):
        self.calls.append((prompt, effort, sandbox, model))
        return FakeResult()


class UsageThread(FakeThread):
    def run(self, prompt, effort, sandbox, model=None):
        self.calls.append((prompt, effort, sandbox, model))
        return UsageResult()


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


class UsageCodex(FakeCodex):
    def thread_start(self, cwd, sandbox):
        self.calls.append(("thread_start", cwd, sandbox))
        return UsageThread(self.calls)

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
    def test_new_job_file_is_small_and_pending(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = create_job_file("JOB-0004", tmp)
            self.assertEqual(path.name, "JOB-0004.toml")
            self.assertIn('status = "pending"', path.read_text(encoding="utf-8"))
            with self.assertRaises(FileExistsError):
                create_job_file("JOB-0004", tmp)

    def test_reasoning_tier_mapping(self):
        self.assertEqual(Job("a", "b", "low", "p").reasoning_tier, "low")
        self.assertEqual(Job("a", "b", "medium", "p").reasoning_tier, "medium")
        self.assertEqual(Job("a", "b", "high", "p").reasoning_tier, "high")

    def test_model_tier_mapping_and_standard_default(self):
        self.assertEqual(Job("a", "b", "medium", "p").model_tier, "standard")
        self.assertEqual(set(MODEL_TIERS), {"economy", "standard", "advanced", "critical"})
        for tier, model in MODEL_TIERS.items():
            self.assertEqual(Job("a", "b", "medium", "p", model_tier=tier).model_tier, tier)
            self.assertTrue(model.startswith("gpt-"))

    def test_unknown_model_tier_rejected(self):
        with self.assertRaises(ValueError):
            Job("a", "b", "medium", "p", model_tier="unknown")

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
            self.assertEqual(calls[1][3], MODEL_TIERS["standard"])
            self.assertEqual(job.model, MODEL_TIERS["standard"])

    def test_legacy_job_without_model_tier_resolves_to_standard(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = write_job(tmp)
            self.assertEqual(JobStore(tmp).load(path).model_tier, "standard")

    def test_requested_and_resolved_model_persist(self):
        with tempfile.TemporaryDirectory() as tmp:
            calls = []
            path = write_job(tmp, model_tier="advanced")
            job = run_job(path, codex_factory=lambda: FakeCodex(calls))
            state = json.loads(Path(tmp, "test.state.json").read_text())
            self.assertEqual(state["model_tier"], "advanced")
            self.assertEqual(state["model"], MODEL_TIERS["advanced"])
            self.assertEqual(state["reasoning_tier"], "medium")
            self.assertEqual(calls[1][3], MODEL_TIERS["advanced"])

    def test_existing_thread_id_is_resumed(self):
        with tempfile.TemporaryDirectory() as tmp:
            calls = []
            path = write_job(tmp, thread_id="thread-existing")
            job = run_job(path, codex_factory=lambda: FakeCodex(calls))
            self.assertEqual(calls[0][0:2], ("thread_resume", "thread-existing"))
            self.assertEqual(job.thread_id, "thread-test-123")

    def test_accept_uses_review_state_without_rewriting_toml(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = write_job(tmp, status="pending")
            original_toml = path.read_text(encoding="utf-8")
            runtime = Job(
                "TEST-001", "test", "medium", "do test", status="review",
                thread_id="thread-runtime", started_at="2026-09-18T01:00:00+00:00",
                result_location="jobs/results/TEST-001/response.md",
                current_turn_tokens=17, cumulative_tokens=17,
                progress={"completed": 1, "current": "review", "pending": 0},
                activity=[{"timestamp": "2026-09-18T01:01:00+00:00", "message": "ready"}],
            )
            store = JobStore(tmp)
            store.save(runtime, path)

            with patch.object(sys, "argv", ["orchestrator", str(path), "--accept"]):
                main()

            state = json.loads(Path(tmp, "test.state.json").read_text(encoding="utf-8"))
            self.assertEqual(state["status"], "accepted")
            self.assertEqual(state["thread_id"], "thread-runtime")
            self.assertEqual(state["cumulative_tokens"], 17)
            self.assertEqual(state["progress"]["current"], "review")
            self.assertEqual(path.read_text(encoding="utf-8"), original_toml)

    def test_monitor_rendering_includes_job_progress_activity_and_usage(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = write_job(tmp)
            calls = []
            job = run_job(path, codex_factory=lambda: UsageCodex(calls))
            # Reopen the snapshot through the public persistence mechanism to
            # model a runner reporting progress while the job is active.
            state_path = Path(tmp, "test.state.json")
            state = json.loads(state_path.read_text())
            state["status"] = "running"
            state_path.write_text(json.dumps(state), encoding="utf-8")
            store = JobStore(tmp)
            store.record_progress(path, completed=2, current="inspect", pending=1)
            store.record_activity(path, "inspect", timestamp="2026-09-18T00:00:00+00:00")
            rendered = render_monitor(tmp)
            self.assertIn("Stock Research Lab Monitor", rendered)
            self.assertIn("ID: TEST-001", rendered)
            self.assertIn("Model Tier: standard", rendered)
            self.assertIn("Model: codex-test", rendered)
            self.assertIn("Reasoning: medium", rendered)
            self.assertIn("completed: 2", rendered)
            self.assertIn("current turn tokens: 17", rendered)
            self.assertIn("current job cumulative tokens: 17", rendered)
            self.assertIn("inspect", rendered)

    def test_monitor_no_active_job(self):
        with tempfile.TemporaryDirectory() as tmp:
            rendered = render_monitor(tmp)
            self.assertIn("No active job", rendered)
            self.assertIn("current turn tokens: N/A", rendered)

    def test_monitor_aggregates_only_recorded_usage_for_today(self):
        with tempfile.TemporaryDirectory() as tmp:
            for name, job_id, tokens, recorded in (
                ("a", "A", 12, "2026-09-18T01:00:00+00:00"),
                ("b", "B", 8, "2026-09-17T01:00:00+00:00"),
            ):
                state = {
                    "job_id": job_id, "status": "review", "cumulative_tokens": tokens,
                    "usage_recorded_at": recorded, "activity": [],
                }
                Path(tmp, f"{name}.state.json").write_text(json.dumps(state), encoding="utf-8")
            rendered = render_monitor(tmp)
            self.assertIn("today's cumulative tokens: 12", rendered)

    def test_unavailable_token_data_is_not_fabricated(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = write_job(tmp)
            run_job(path, codex_factory=lambda: FakeCodex([]))
            rendered = render_monitor(tmp)
            self.assertIn("today's cumulative tokens: N/A", rendered)
            self.assertIn("current turn tokens: N/A", rendered)


if __name__ == "__main__":
    unittest.main()
