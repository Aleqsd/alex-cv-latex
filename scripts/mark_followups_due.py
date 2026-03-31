from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone

from job_search_lib import (
    JOBS_DIR,
    append_status_transition,
    ensure_job_index_entry,
    follow_up_due_timestamp,
    load_jobs_index,
    read_yaml,
    refresh_dashboard_data,
    save_jobs_index,
    write_yaml,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Mark applied jobs as follow_up_due when their follow-up window is reached.")
    parser.add_argument("--days", type=int, default=7, help="Number of days after apply/contact before follow-up is due.")
    parser.add_argument("--dry-run", action="store_true", help="Report what would change without writing files.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    index_data = load_jobs_index()
    due_jobs: list[dict[str, str]] = []

    for entry in index_data.get("jobs", []):
        job_dir = JOBS_DIR / entry.get("id", "")
        offer = read_yaml(job_dir / "offer.yaml", {})
        if not offer:
            continue
        if str(offer.get("status", "")) not in {"applied", "recruiter_contact"}:
            continue
        due_at = follow_up_due_timestamp(offer, delay_days=args.days)
        if not due_at:
            continue
        if due_at <= datetime.now(timezone.utc):
            due_jobs.append({"id": offer["id"], "due_at": due_at.isoformat()})
            if args.dry_run:
                continue
            append_status_transition(offer, "follow_up_due", f"Automatic follow-up threshold reached after {args.days} days.")
            write_yaml(job_dir / "offer.yaml", offer)
            ensure_job_index_entry(index_data, offer, job_dir)

    if not args.dry_run:
        save_jobs_index(index_data)
        refresh_dashboard_data()

    print(json.dumps({"followUpsDue": due_jobs, "count": len(due_jobs), "dryRun": args.dry_run}, indent=2))


if __name__ == "__main__":
    main()
