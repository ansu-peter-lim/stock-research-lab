from __future__ import annotations

import argparse

from .core import JobStore, render_monitor, run_job


def main() -> None:
    parser = argparse.ArgumentParser(description="Run or monitor Stock Research Lab Codex jobs")
    parser.add_argument("job", nargs="?", help="path to a TOML job file, or 'monitor'")
    parser.add_argument("--accept", action="store_true", help="accept a completed review job")
    args = parser.parse_args()
    if args.job == "monitor":
        print(render_monitor())
        return
    if not args.job:
        parser.error("a TOML job path or 'monitor' is required")
    if args.accept:
        store = JobStore()
        job = store.load(args.job)
        job.transition("accepted")
        store.save(job, args.job)
    else:
        job = run_job(args.job)
    print(f"{job.job_id}: {job.status} thread_id={job.thread_id or '-'}")


if __name__ == "__main__":
    main()
