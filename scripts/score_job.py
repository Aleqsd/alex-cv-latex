from __future__ import annotations

import argparse
from pathlib import Path

from job_search_lib import (
    JOBS_DIR,
    compute_fit,
    ensure_job_layout,
    ensure_job_index_entry,
    load_jobs_index,
    load_profile,
    load_taxonomy,
    read_yaml,
    refresh_dashboard_data,
    role_family_name,
    save_jobs_index,
    utc_now_iso,
    write_yaml,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Score one or all job offers against the candidate profile.")
    parser.add_argument("--job-id", help="Specific job id to score.")
    parser.add_argument("--all", action="store_true", help="Score every indexed job.")
    return parser.parse_args()


def render_fit_report(offer: dict, fit: dict) -> str:
    strengths = "\n".join(f"- {item}" for item in fit["strengths"]) or "- None yet"
    risks = "\n".join(f"- {item}" for item in fit["risks"]) or "- None yet"
    subscores = "\n".join(f"- {key}: {value}" for key, value in fit["subscores"].items())
    evidence = "\n".join(f"- {key}: {value}" for key, value in fit["evidence_quality"].items())
    return (
        f"# Fit Report\n\n"
        f"## Summary\n\n"
        f"- Company: {offer.get('company_name', '')}\n"
        f"- Role: {offer.get('job_title', '')}\n"
        f"- Recommendation: {fit['fit_recommendation']}\n"
        f"- Confidence: {fit['confidence']}\n\n"
        f"## Scores\n\n"
        f"- ATS: {fit['fit_score_ats']}\n"
        f"- Human: {fit['fit_score_human']}\n"
        f"- Strategic: {fit['fit_score_strategic']}\n"
        f"- Final: {fit['fit_score_final']}\n\n"
        f"## Subscores\n\n{subscores}\n\n"
        f"## Strengths\n\n{strengths}\n\n"
        f"## Risks\n\n{risks}\n\n"
        f"## Evidence Quality\n\n{evidence}\n"
    )


def score_offer(job_dir: Path, profile: dict, taxonomy: dict, index_data: dict) -> None:
    offer_path = job_dir / "offer.yaml"
    offer = read_yaml(offer_path, {})
    if not offer:
        return
    paths = ensure_job_layout(job_dir)

    fit = compute_fit(offer, profile, taxonomy)
    offer.update(fit)
    role_family_label = role_family_name(fit["normalized_role_family"])
    offer["fit_summary"] = (
        f"{offer['company_name']} scores {fit['fit_score_final']} with recommendation "
        f"{fit['fit_recommendation']} for role family {role_family_label}."
    )
    offer["updated_at"] = utc_now_iso()
    write_yaml(offer_path, offer)
    paths["fit_report"].write_text(render_fit_report(offer, fit), encoding="utf-8")
    ensure_job_index_entry(index_data, offer, job_dir)


def main() -> None:
    args = parse_args()
    if not args.job_id and not args.all:
        raise SystemExit("Use --job-id <id> or --all.")

    profile = load_profile()
    taxonomy = load_taxonomy()
    index_data = load_jobs_index()
    targets = [JOBS_DIR / entry["id"] for entry in index_data.get("jobs", [])] if args.all else [JOBS_DIR / args.job_id]

    for job_dir in targets:
        score_offer(job_dir, profile, taxonomy, index_data)

    save_jobs_index(index_data)
    refresh_dashboard_data()
    print(f"Scored {len(targets)} job(s).")


if __name__ == "__main__":
    main()
