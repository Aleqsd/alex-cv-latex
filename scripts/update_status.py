from __future__ import annotations

import argparse

from job_search_lib import JOBS_DIR, append_status_transition, ensure_job_index_entry, load_jobs_index, read_yaml, refresh_dashboard_data, save_jobs_index, write_yaml


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Update the canonical status of a job offer.")
    parser.add_argument("--job-id", required=True, help="Job id.")
    parser.add_argument("--status", required=True, help="New status.")
    parser.add_argument("--note", default="", help="Optional status change note.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    job_dir = JOBS_DIR / args.job_id
    offer_path = job_dir / "offer.yaml"
    offer = read_yaml(offer_path, {})
    if not offer:
        raise SystemExit(f"Offer not found for {args.job_id}.")

    previous = offer.get("status", "")
    append_status_transition(offer, args.status, args.note)
    write_yaml(offer_path, offer)

    index_data = load_jobs_index()
    ensure_job_index_entry(index_data, offer, job_dir)
    save_jobs_index(index_data)
    refresh_dashboard_data()
    print(f"Updated {args.job_id}: {previous} -> {args.status}")


if __name__ == "__main__":
    main()
