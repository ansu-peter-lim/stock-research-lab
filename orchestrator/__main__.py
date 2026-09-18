from __future__ import annotations

import argparse

from .core import JobStore, create_job_file, render_monitor, run_job


def main() -> None:
    parser = argparse.ArgumentParser(description="Run or monitor Stock Research Lab Codex jobs")
    parser.add_argument("command", nargs="?", help="path to a TOML job, 'monitor', or 'new'")
    parser.add_argument("value", nargs="?", help="job id when command is 'new'")
    parser.add_argument("--accept", action="store_true", help="accept a completed review job")
    args = parser.parse_args()
    if args.command == "monitor":
        print(render_monitor())
        return
    if args.command == "new":
        if not args.value:
            parser.error("new requires a job id such as JOB-0004")
        print(create_job_file(args.value))
        return
    if not args.command:
        parser.error("a TOML job path or 'monitor' is required")
    if args.accept:
        store = JobStore()
        job = store.load(args.command)
        job.transition("accepted")
        store.save(job, args.command)
    else:
        job = run_job(args.command)
    print(f"{job.job_id}: {job.status} thread_id={job.thread_id or '-'}")


if __name__ == "__main__":
    main()
