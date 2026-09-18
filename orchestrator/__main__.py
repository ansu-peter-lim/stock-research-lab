from __future__ import annotations

import argparse

from .core import JobStore, run_job


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a Stock Research Lab Codex job")
    parser.add_argument("job", help="path to a TOML job file")
    parser.add_argument("--accept", action="store_true", help="accept a completed review job")
    args = parser.parse_args()
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
