from __future__ import annotations

import argparse
import shutil

from job_search_lib import JOBS_DIR, load_jobs_index, read_yaml, refresh_dashboard_data, save_jobs_index


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Delete all tracked jobs for one company from the repository.")
    parser.add_argument("--company", required=True, help="Exact company name to purge.")
    parser.add_argument("--dry-run", action="store_true", help="List matching jobs without deleting them.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    index_data = load_jobs_index()
    company = args.company.strip().lower()

    kept_jobs = []
    removed_ids: list[str] = []

    for entry in index_data.get("jobs", []):
        job_id = entry.get("id", "")
        job_dir = JOBS_DIR / job_id
        offer = read_yaml(job_dir / "offer.yaml", {})
        company_name = str(offer.get("company_name") or entry.get("company_name") or "").strip().lower()
        if company_name != company:
            kept_jobs.append(entry)
            continue
        removed_ids.append(job_id)
        if not args.dry_run:
            shutil.rmtree(job_dir, ignore_errors=True)

    if not args.dry_run:
        index_data["jobs"] = kept_jobs
        save_jobs_index(index_data)
        refresh_dashboard_data()

    action = "Would purge" if args.dry_run else "Purged"
    print(f"{action} {len(removed_ids)} job(s) for {args.company}.")
    for job_id in removed_ids:
        print(job_id)


if __name__ == "__main__":
    main()
