from __future__ import annotations

import argparse

from job_search_lib import (
    JOBS_DIR,
    append_status_transition,
    ensure_job_index_entry,
    is_explicit_remote_offer,
    is_remote_eligible_for_constraints,
    is_us_only_remote_offer,
    load_jobs_index,
    load_profile,
    read_yaml,
    refresh_dashboard_data,
    save_jobs_index,
    write_yaml,
)


TERMINAL_STATUSES = {"applied", "follow_up_due", "recruiter_contact", "interviewing", "rejected", "archived"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Archive offers blocked by the current location constraints.")
    parser.add_argument("--dry-run", action="store_true", help="Print matching job ids without modifying files.")
    return parser.parse_args()


def offer_matches_location_block(offer: dict, constraints: dict) -> tuple[bool, str]:
    remote_parts = (
        str(offer.get("remote_policy", "")),
        str(offer.get("location", "")),
        str(offer.get("job_title", "")),
        str(offer.get("job_description_clean", "")),
    )
    explicit_remote = is_explicit_remote_offer(*remote_parts)
    if constraints.get("remote_only_default", False) and constraints.get("require_explicit_remote", False) and not explicit_remote:
        return True, "Blocked by location constraint: offer does not explicitly state full remote work."
    if constraints.get("exclude_remote_us_only", False) and is_us_only_remote_offer(*remote_parts):
        return True, "Blocked by location constraint: remote work is limited to the United States."
    if explicit_remote and not is_remote_eligible_for_constraints(constraints, *remote_parts):
        return True, "Blocked by location constraint: remote work is restricted outside the current search geography."
    return False, ""


def main() -> None:
    args = parse_args()
    profile = load_profile()
    constraints = profile.get("constraints", {}).get("location_constraints", {})
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
        blocked, note = offer_matches_location_block(offer, constraints)
        if not blocked:
            continue
        archived.append(job_id)
        if args.dry_run:
            continue
        append_status_transition(offer, "archived", note)
        write_yaml(offer_path, offer)
        ensure_job_index_entry(index_data, offer, JOBS_DIR / job_id)

    if not args.dry_run:
        save_jobs_index(index_data)
        refresh_dashboard_data()

    action = "Matched" if args.dry_run else "Archived"
    print(f"{action} {len(archived)} blocked offer(s).")
    for job_id in archived:
        print(job_id)


if __name__ == "__main__":
    main()
