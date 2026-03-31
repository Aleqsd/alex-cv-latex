from __future__ import annotations

import argparse

from job_search_lib import (
    JOBS_DIR,
    append_status_transition,
    ensure_job_index_entry,
    load_jobs_index,
    read_yaml,
    refresh_dashboard_data,
    save_jobs_index,
    write_yaml,
)


TERMINAL_STATUSES = {"applied", "follow_up_due", "recruiter_contact", "interviewing", "rejected", "archived"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Archive offers currently scored as skip.")
    parser.add_argument("--dry-run", action="store_true", help="Print matching job ids without modifying files.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    index_data = load_jobs_index()

    archived: list[str] = []
    for entry in index_data.get("jobs", []):
        job_id = entry.get("id", "")
        if not job_id:
            continue
        offer_path = JOBS_DIR / job_id / "offer.yaml"
        offer = read_yaml(offer_path, {})
        if not offer:
            continue
        if str(offer.get("status", "")) in TERMINAL_STATUSES:
            continue
        if str(offer.get("fit_recommendation", "")) != "skip":
            continue

        archived.append(job_id)
        if args.dry_run:
            continue

        append_status_transition(offer, "archived", "Archived automatically because the current fit recommendation is skip.")
        write_yaml(offer_path, offer)
        ensure_job_index_entry(index_data, offer, JOBS_DIR / job_id)

    if not args.dry_run:
        save_jobs_index(index_data)
        refresh_dashboard_data()

    action = "Matched" if args.dry_run else "Archived"
    print(f"{action} {len(archived)} skip offer(s).")
    for job_id in archived:
        print(job_id)


if __name__ == "__main__":
    main()
