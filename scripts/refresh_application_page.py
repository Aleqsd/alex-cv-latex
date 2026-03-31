from __future__ import annotations

import argparse

from application_inspector import inspect_application_page
from job_search_lib import JOBS_DIR, ensure_job_layout, read_yaml, refresh_dashboard_data, utc_now_iso, write_yaml


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Refresh application-page metadata for an existing job offer.")
    parser.add_argument("--job-id", required=True, help="Canonical job id.")
    parser.add_argument(
        "--browser",
        choices=["auto", "always", "off"],
        default="auto",
        help="Whether to inspect the page with a real browser when static HTML is insufficient.",
    )
    return parser.parse_args()
def main() -> None:
    args = parse_args()
    job_dir = JOBS_DIR / args.job_id
    offer = read_yaml(job_dir / "offer.yaml", {})
    if not offer:
        raise SystemExit(f"Offer not found for {args.job_id}.")

    application_url = offer.get("application_url") or offer.get("source_url")
    if not application_url:
        raise SystemExit("This offer does not have an application URL to inspect.")

    inspection = inspect_application_page(
        application_url,
        expected_title=offer.get("job_title", ""),
        browser_mode=args.browser,
    )
    previous_questions = offer.get("application_questions", [])
    html = inspection["html"]
    questions = inspection["questions"]
    platform = inspection["platform"]
    paths = ensure_job_layout(job_dir)

    preservation_threshold = max(3, int(len(previous_questions) * 0.6)) if previous_questions else 0
    if previous_questions and len(questions) < preservation_threshold:
        questions = previous_questions
        inspection["page_signals"] = dict(inspection["page_signals"])
        inspection["page_signals"]["preserved_previous_questions"] = True
        inspection["page_signals"]["preservation_reason"] = "inspection_regressed"
    paths["source_html"].write_text(html, encoding="utf-8")

    offer["source_url"] = inspection.get("source_page_url", offer.get("source_url", application_url))
    offer["application_url"] = inspection["application_url"]
    offer["application_platform"] = platform
    offer["application_questions"] = questions
    offer["page_signals"] = dict(inspection["page_signals"])
    offer["page_signals"]["refreshed_at"] = utc_now_iso()
    offer["updated_at"] = utc_now_iso()
    write_yaml(job_dir / "offer.yaml", offer)
    refresh_dashboard_data()
    print(f"Refreshed application page for {args.job_id}")
    print(f"Detected questions: {len(questions)}")


if __name__ == "__main__":
    main()
