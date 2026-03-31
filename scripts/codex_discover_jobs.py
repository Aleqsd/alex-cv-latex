from __future__ import annotations

import argparse
import shlex
import subprocess
from pathlib import Path

from job_search_lib import load_profile, load_taxonomy


PROMPT_TEMPLATE = """You are working in this repository as a job-search discovery agent.

Goal:
- Find current public job offers relevant to the candidate profile.
- Focus on coding-heavy roles in the preferred families.
- Ingest only offers that are likely worth review.

Candidate targets:
- Preferred role families: {preferred_role_families}
- Preferred company stages: {preferred_company_stages}
- Preferred work modes: {preferred_work_modes}

Repository tasks:
1. Search the web for relevant public job offers.
2. Ignore clearly off-target roles such as design, sales, recruiting, marketing, advocacy-only, or generic talent pools.
3. For each promising offer, ingest it into the repository using:
   - `python scripts/ingest_job_url.py --url "<job_url>"`
4. Score each ingested offer using:
   - `python scripts/score_job.py --job-id <job_id>`
5. Refresh dashboard data at the end.

Rules:
- Only ingest roles that are genuinely relevant to the target profile.
- Only ingest jobs that explicitly state full remote work. Skip hybrid, onsite, in-office, or ambiguous work-mode listings.
- Skip offers where remote work is limited to the United States.
- Prefer English-language roles with clear public descriptions.
- Do not invent metadata that is not visible on the offer page.
- If a page is blocked or too sparse, skip it.
- Be selective: quality over quantity.

Suggested search themes:
{search_themes}
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Launch Codex in web-search mode to discover relevant jobs.")
    parser.add_argument("--model", default="", help="Optional Codex model override.")
    parser.add_argument("--print-only", action="store_true", help="Print the generated command without running Codex.")
    return parser.parse_args()


def build_prompt() -> str:
    profile = load_profile()
    taxonomy = load_taxonomy()
    preferences = profile.get("preferences", {})
    role_families = preferences.get("preferred_role_families", [])
    search_themes = []
    for family in role_families:
        keywords = taxonomy.get("role_families", {}).get(family, {}).get("keywords", [])
        if keywords:
            search_themes.append(f"- {family}: {', '.join(keywords[:6])}")

    return PROMPT_TEMPLATE.format(
        preferred_role_families=", ".join(role_families),
        preferred_company_stages=", ".join(preferences.get("preferred_company_stages", [])),
        preferred_work_modes=", ".join(preferences.get("preferred_work_modes", [])),
        search_themes="\n".join(search_themes) or "- software engineer, backend engineer, founding engineer, platform engineer",
    )


def main() -> None:
    args = parse_args()
    prompt = build_prompt()
    command = [
        "codex",
        "exec",
        "--cd",
        str(Path(__file__).resolve().parent.parent),
        "--sandbox",
        "workspace-write",
        "--ask-for-approval",
        "never",
        "--search",
    ]
    if args.model:
        command.extend(["--model", args.model])
    command.append(prompt)

    rendered = " ".join(shlex.quote(part) for part in command)
    print(rendered)
    if not args.print_only:
        subprocess.run(command, check=True)


if __name__ == "__main__":
    main()
