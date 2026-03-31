from __future__ import annotations

import argparse
from pathlib import Path

from job_search_lib import (
    JOBS_DIR,
    classify_role_family,
    ensure_job_layout,
    ensure_job_index_entry,
    load_jobs_index,
    load_taxonomy,
    read_yaml,
    refresh_dashboard_data,
    save_jobs_index,
    slugify,
    utc_now_iso,
    write_yaml,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create a canonical job folder from manual input.")
    parser.add_argument("--company", required=True, help="Company name.")
    parser.add_argument("--title", required=True, help="Job title.")
    parser.add_argument("--description", help="Inline job description.")
    parser.add_argument("--raw-file", help="Path to a text or markdown file containing the job description.")
    parser.add_argument("--source-url", default="", help="Source URL.")
    parser.add_argument("--source", default="manual", help="Source type.")
    parser.add_argument("--location", default="", help="Job location.")
    parser.add_argument("--remote-policy", default="", help="Remote policy.")
    parser.add_argument("--employment-type", default="full_time", help="Employment type.")
    parser.add_argument("--company-stage", default="", help="Company stage such as seed, series_a, scale_up.")
    parser.add_argument("--role-family", default="", help="Override normalized role family.")
    return parser.parse_args()


def load_description(args: argparse.Namespace) -> str:
    if args.raw_file:
        return Path(args.raw_file).read_text(encoding="utf-8")
    if args.description:
        return args.description
    return ""


def main() -> None:
    args = parse_args()
    description = load_description(args)
    taxonomy = load_taxonomy()
    role_family = args.role_family or classify_role_family(args.title, description, taxonomy)

    job_id = f"{slugify(args.company)}-{slugify(args.title)}"
    job_dir = JOBS_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    paths = ensure_job_layout(job_dir)

    offer_template = read_yaml(Path("templates/job_offer.yaml"), {})
    offer = dict(offer_template)
    offer.update(
        {
            "id": job_id,
            "company_name": args.company,
            "job_title": args.title,
            "normalized_role_family": role_family,
            "source": args.source,
            "source_url": args.source_url,
            "source_date": utc_now_iso(),
            "location": args.location,
            "remote_policy": args.remote_policy,
            "employment_type": args.employment_type,
            "company_stage": args.company_stage,
            "application_url": args.source_url,
            "job_description_raw": description,
            "job_description_clean": description.strip(),
            "status": "discovered",
            "status_history": [
                {
                    "timestamp": utc_now_iso(),
                    "from": "",
                    "to": "discovered",
                    "note": "Offer ingested manually.",
                }
            ],
        }
    )

    write_yaml(job_dir / "offer.yaml", offer)
    paths["raw"].write_text(description or f"# {args.company} - {args.title}\n", encoding="utf-8")
    paths["research"].write_text("# Research\n\n", encoding="utf-8")
    paths["fit_report"].write_text("# Fit Report\n\nRun score_job.py to populate this file.\n", encoding="utf-8")
    paths["decision"].write_text("# Decision Log\n\n", encoding="utf-8")

    index_data = load_jobs_index()
    ensure_job_index_entry(index_data, offer, job_dir)
    save_jobs_index(index_data)
    refresh_dashboard_data()

    print(f"Created job folder: {job_dir}")
    print(f"Normalized role family: {role_family}")


if __name__ == "__main__":
    main()
