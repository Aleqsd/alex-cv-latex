from __future__ import annotations

import argparse
import json
import re
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from html import unescape
from pathlib import Path
from typing import Any

import requests
from bs4 import BeautifulSoup

from job_search_lib import (
    DATA_DIR,
    JOBS_DIR,
    classify_role_family,
    compute_fit,
    ensure_job_index_entry,
    ensure_job_layout,
    infer_remote_policy,
    is_explicit_remote_offer,
    is_remote_eligible_for_constraints,
    is_us_only_remote_offer,
    load_jobs_index,
    load_profile,
    load_taxonomy,
    read_yaml,
    refresh_dashboard_data,
    role_family_name,
    save_jobs_index,
    slugify,
    utc_now_iso,
    write_yaml,
)


USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Discover jobs from configured boards and ingest them into the repository.")
    parser.add_argument("--config", default=str(DATA_DIR / "job_sources.yaml"), help="Path to a job sources YAML config.")
    parser.add_argument("--source-id", help="Optional single source id from data/job_sources.yaml.")
    parser.add_argument("--min-score", type=int, default=80, help="Minimum final score to consider a discovered offer relevant.")
    parser.add_argument("--limit", type=int, default=0, help="Optional cap on the number of jobs processed.")
    return parser.parse_args()


def load_job_sources(config_path: str) -> dict[str, Any]:
    return read_yaml(Path(config_path), {"version": 1, "sources": []})


def html_to_text(value: str) -> str:
    text = re.sub(r"<[^>]+>", " ", value or "")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def extract_page_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "svg", "img"]):
        tag.decompose()
    parts: list[str] = []
    for node in soup.find_all(["h1", "h2", "h3", "p", "li"]):
        text = node.get_text(" ", strip=True)
        if text:
            parts.append(text)
    text = "\n".join(parts)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def fetch_text_snapshot(url: str) -> str:
    response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=30)
    response.raise_for_status()
    return extract_page_text(response.text)


def extract_ashby_app_data(html: str) -> dict[str, Any]:
    match = re.search(r"window\.__appData = (\{.*?\});\s*fetch\(", html, re.DOTALL)
    if not match:
        return {}
    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError:
        return {}


def extract_embedded_json_value(html: str, key: str) -> Any:
    needle = f'"{key}":'
    start = html.find(needle)
    if start == -1:
        return None
    index = start + len(needle)
    while index < len(html) and html[index] in " \r\n\t":
        index += 1
    if index >= len(html) or html[index] not in "[{":
        return None

    opening = html[index]
    closing = "]" if opening == "[" else "}"
    depth = 0
    in_string = False
    escaped = False
    end = index

    while end < len(html):
        char = html[end]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
        else:
            if char == '"':
                in_string = True
            elif char == opening:
                depth += 1
            elif char == closing:
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(html[index : end + 1])
                    except json.JSONDecodeError:
                        return None
        end += 1
    return None


def detect_remote_policy(location: str, title: str, description: str) -> str:
    return infer_remote_policy(location, title, description)


def posting_sort_key(posting: dict[str, Any]) -> tuple[int, str]:
    raw = str(posting.get("posted_at", "") or "").strip()
    if not raw:
        return (0, "")
    try:
        normalized = raw.replace("Z", "+00:00")
        return (1, normalized)
    except Exception:
        pass
    try:
        parsed = parsedate_to_datetime(raw)
        return (1, parsed.isoformat())
    except Exception:
        return (1, raw)


def fetch_greenhouse(source: dict[str, Any]) -> list[dict[str, Any]]:
    token = source["board_token"]
    response = requests.get(
        f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true",
        headers={"User-Agent": USER_AGENT},
        timeout=30,
    )
    response.raise_for_status()
    payload = response.json()
    jobs = []
    for item in payload.get("jobs", []):
        jobs.append(
            {
                "external_job_id": str(item.get("id", "")),
                "title": item.get("title", "").strip(),
                "url": item.get("absolute_url", ""),
                "location": (item.get("location") or {}).get("name", ""),
                "description": html_to_text(item.get("content", "")),
                "posted_at": item.get("updated_at", ""),
                "provider": "greenhouse",
            }
        )
    return jobs


def fetch_lever(source: dict[str, Any]) -> list[dict[str, Any]]:
    token = source["board_token"]
    response = requests.get(
        f"https://api.lever.co/v0/postings/{token}?mode=json",
        headers={"User-Agent": USER_AGENT},
        timeout=30,
    )
    response.raise_for_status()
    payload = response.json()
    jobs = []
    for item in payload:
        categories = item.get("categories") or {}
        jobs.append(
            {
                "external_job_id": str(item.get("id", "")),
                "title": item.get("text", "").strip(),
                "url": item.get("hostedUrl", "") or item.get("applyUrl", ""),
                "location": categories.get("location", "") or item.get("categories", {}).get("location", ""),
                "description": html_to_text(item.get("descriptionPlain", "") or item.get("description", "")),
                "posted_at": item.get("createdAt", ""),
                "provider": "lever",
            }
        )
    return jobs


def fetch_workable(source: dict[str, Any]) -> list[dict[str, Any]]:
    token = source["board_token"]
    response = requests.get(
        f"https://{token}.workable.com/spi/v3/jobs",
        headers={"User-Agent": USER_AGENT},
        timeout=30,
    )
    response.raise_for_status()
    payload = response.json()
    jobs = []
    for item in payload.get("results", []):
        description_parts = [
            html_to_text(item.get("description", "")),
            html_to_text(item.get("requirements", "")),
            html_to_text(item.get("benefits", "")),
        ]
        jobs.append(
            {
                "external_job_id": str(item.get("shortcode", "") or item.get("id", "")),
                "title": item.get("title", "").strip(),
                "url": item.get("url", ""),
                "location": item.get("location", {}).get("location_str", "") if isinstance(item.get("location"), dict) else "",
                "description": "\n".join(part for part in description_parts if part),
                "posted_at": item.get("published", "") or item.get("created_at", ""),
                "provider": "workable",
            }
        )
    return jobs


def fetch_ashby(source: dict[str, Any]) -> list[dict[str, Any]]:
    token = source["board_token"].strip("/")
    board_url = source.get("base_url") or f"https://jobs.ashbyhq.com/{token}"
    response = requests.get(board_url, headers={"User-Agent": USER_AGENT}, timeout=30)
    response.raise_for_status()
    app_data = extract_ashby_app_data(response.text)
    organization = app_data.get("organization") or {}
    postings = organization.get("jobPostings") or extract_embedded_json_value(response.text, "jobPostings") or []
    detail_fetch_limit = int(source.get("detail_fetch_limit", 0) or 0)
    fetched_details = 0

    jobs = []
    for item in postings:
        if item.get("isListed") is False:
            continue
        posting_id = str(item.get("id") or "")
        external_job_id = posting_id or str(item.get("jobId") or "")
        job_url = f"{board_url.rstrip('/')}/{posting_id}" if posting_id else board_url
        location_bits = [item.get("locationName", "")]
        for secondary in item.get("secondaryLocations", []) or []:
            secondary_name = secondary.get("locationName", "")
            if secondary_name:
                location_bits.append(secondary_name)
        location = " | ".join(part for part in location_bits if part)

        description = "\n".join(
            part
            for part in [
                item.get("title", ""),
                item.get("teamName", ""),
                item.get("departmentName", ""),
                location,
                item.get("compensationTierSummary", ""),
            ]
            if part
        )
        if fetched_details < detail_fetch_limit:
            try:
                detail_text = fetch_text_snapshot(job_url)
                if detail_text:
                    description = detail_text
                fetched_details += 1
            except requests.RequestException:
                pass

        jobs.append(
            {
                "external_job_id": external_job_id,
                "title": item.get("title", "").strip(),
                "url": job_url,
                "location": location,
                "description": description,
                "posted_at": item.get("publishedDate", "") or item.get("updatedAt", ""),
                "provider": "ashby",
            }
        )
    return jobs


def fetch_teamtailor(source: dict[str, Any]) -> list[dict[str, Any]]:
    base_url = source.get("base_url", "").strip()
    token = str(source.get("board_token", "")).strip().strip("/")
    if not base_url:
        if token.startswith("http://") or token.startswith("https://"):
            base_url = token
        elif "." in token:
            base_url = f"https://{token}"
        else:
            base_url = f"https://{token}.teamtailor.com"
    rss_url = source.get("rss_url") or f"{base_url.rstrip('/')}/jobs.rss"

    response = requests.get(rss_url, headers={"User-Agent": USER_AGENT}, timeout=30)
    response.raise_for_status()
    root = ET.fromstring(response.text)

    jobs = []
    channel = root.find("channel")
    if channel is None:
        return jobs

    for item in channel.findall("item"):
        title = (item.findtext("title") or "").strip()
        url = (item.findtext("link") or "").strip()
        description_raw = item.findtext("description") or ""
        description = html_to_text(unescape(description_raw))
        external_job_id = ""
        if url:
            external_job_id = url.rstrip("/").split("/")[-1]
        jobs.append(
            {
                "external_job_id": external_job_id,
                "title": title,
                "url": url,
                "location": source.get("location_hint", ""),
                "description": description,
                "posted_at": item.findtext("pubDate") or "",
                "provider": "teamtailor",
            }
        )
    return jobs


FETCHERS = {
    "greenhouse": fetch_greenhouse,
    "lever": fetch_lever,
    "workable": fetch_workable,
    "ashby": fetch_ashby,
    "teamtailor": fetch_teamtailor,
}


def should_keep_job(title: str, description: str, role_family: str, profile: dict[str, Any]) -> bool:
    preferred = set(profile.get("preferences", {}).get("preferred_role_families", []))
    title_lower = title.lower()
    haystack = f"{title} {description}".lower()

    negative_title_terms = [
        "designer",
        "design",
        "brand",
        "content",
        "manager",
        "marketing",
        "sales",
        "advocacy",
        "advocate",
        "evangelist",
        "director",
        "head of",
        "intern",
        "internship",
        "analyst",
        "account executive",
        "customer success",
        "finance",
        "legal",
        "recruiter",
        "recruiting",
        "talent",
        "hr",
        "human resources",
        "people ops",
        "office manager",
        "general application",
        "don't see what you're looking for",
        "dont see what youre looking for",
    ]
    if any(term in title_lower for term in negative_title_terms):
        return False

    positive_title_terms = [
        "engineer",
        "developer",
        "software",
        "backend",
        "full-stack",
        "fullstack",
        "full stack",
        "platform",
        "devops",
        "infrastructure",
        "site reliability",
        "sre",
        "founding",
    ]
    positive_stack_terms = ["python", "go", "typescript", "aws", "gcp", "docker", "kubernetes", "api", "apis"]

    title_hit = any(term in title_lower for term in positive_title_terms)
    stack_hits = sum(1 for term in positive_stack_terms if term in haystack)

    if role_family in preferred and (title_hit or stack_hits >= 2):
        return True

    return title_hit and stack_hits >= 2


def source_allows_job(source: dict[str, Any], profile: dict[str, Any], title: str, description: str, location: str) -> bool:
    title_lower = title.lower()
    haystack = f"{title} {description}".lower()
    allow_titles = [item.lower() for item in source.get("allow_title_terms", [])]
    deny_titles = [item.lower() for item in source.get("deny_title_terms", [])]
    require_keywords = [item.lower() for item in source.get("require_keywords", [])]
    constraints = profile.get("constraints", {}).get("location_constraints", {})

    if allow_titles and not any(term in title_lower for term in allow_titles):
        return False
    if deny_titles and any(term in title_lower for term in deny_titles):
        return False
    if require_keywords and not any(term in haystack for term in require_keywords):
        return False
    if not is_explicit_remote_offer(location, title, description):
        return False
    if constraints.get("exclude_remote_us_only", False) and is_us_only_remote_offer(location, title, description):
        return False
    if not is_remote_eligible_for_constraints(constraints, location, title, description):
        return False
    return True


def load_offer_template() -> dict[str, Any]:
    return read_yaml(Path("templates/job_offer.yaml"), {})


def find_existing_discovered_job_id(
    company: str,
    title_slug: str,
    location: str,
    provider: str,
    index_data: dict[str, Any],
) -> str | None:
    for entry in index_data.get("jobs", []):
        if entry.get("company_name") != company:
            continue
        candidate_dir = JOBS_DIR / entry.get("id", "")
        offer = read_yaml(candidate_dir / "offer.yaml", {})
        if not offer:
            continue
        if offer.get("source_provider") != provider:
            continue
        if slugify(offer.get("job_title", "")) != title_slug:
            continue
        if (offer.get("location", "") or "").strip() != location.strip():
            continue
        return entry.get("id")
    return None


def upsert_discovered_offer(
    source: dict[str, Any],
    job: dict[str, Any],
    profile: dict[str, Any],
    taxonomy: dict[str, Any],
    index_data: dict[str, Any],
) -> dict[str, Any] | None:
    company = source["company_name"]
    title = job["title"]
    description = job["description"]
    role_family = classify_role_family(title, description, taxonomy)
    if not source_allows_job(source, profile, title, description, job.get("location", "")):
        return None
    if not should_keep_job(title, description, role_family, profile):
        return None

    company_slug = slugify(company)
    title_slug = slugify(title)
    external_id = slugify(job["external_job_id"])[:16] if job["external_job_id"] else ""
    existing_job_id = find_existing_discovered_job_id(company, title_slug, job.get("location", ""), job["provider"], index_data)
    job_id = existing_job_id or "-".join(part for part in [company_slug, title_slug, external_id] if part)
    job_dir = JOBS_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    paths = ensure_job_layout(job_dir)

    existing = read_yaml(job_dir / "offer.yaml", {})
    offer_template = load_offer_template()
    offer = dict(offer_template)
    offer.update(existing)
    offer.update(
        {
            "id": job_id,
            "company_name": company,
            "job_title": title,
            "normalized_role_family": role_family,
            "source": "auto_discovery",
            "source_provider": job["provider"],
            "discovery_source": source["id"],
            "external_job_id": job["external_job_id"],
            "source_url": job["url"],
            "application_url": job["url"],
            "source_date": existing.get("source_date", utc_now_iso()),
            "posted_at": job.get("posted_at", ""),
            "last_seen_at": utc_now_iso(),
            "location": job.get("location", "") or source.get("location_hint", ""),
            "remote_policy": detect_remote_policy(job.get("location", ""), title, description),
            "employment_type": existing.get("employment_type", "full_time"),
            "company_stage": source.get("company_stage", existing.get("company_stage", "")),
            "job_description_raw": description,
            "job_description_clean": description.strip(),
        }
    )

    if not existing:
        offer["status"] = "discovered"
        offer["status_history"] = [
            {
                "timestamp": utc_now_iso(),
                "from": "",
                "to": "discovered",
                "note": f"Offer discovered automatically from source {source['id']}.",
            }
        ]

    if not paths["raw"].exists():
        paths["raw"].write_text(description or f"# {company} - {title}\n", encoding="utf-8")
    if not paths["research"].exists():
        paths["research"].write_text("# Research\n\n", encoding="utf-8")
    if not paths["decision"].exists():
        paths["decision"].write_text("# Decision Log\n\n", encoding="utf-8")
    if not paths["fit_report"].exists():
        paths["fit_report"].write_text("# Fit Report\n\nRun score_job.py to populate this file.\n", encoding="utf-8")

    fit = compute_fit(offer, profile, taxonomy)
    offer.update(fit)
    offer["fit_summary"] = (
        f"{company} scores {fit['fit_score_final']} with recommendation "
        f"{fit['fit_recommendation']} for role family {role_family_name(role_family)}."
    )
    offer["updated_at"] = utc_now_iso()
    write_yaml(job_dir / "offer.yaml", offer)
    ensure_job_index_entry(index_data, offer, job_dir)
    return offer


def main() -> None:
    args = parse_args()
    profile = load_profile()
    taxonomy = load_taxonomy()
    index_data = load_jobs_index()
    sources_data = load_job_sources(args.config)

    enabled_sources = [source for source in sources_data.get("sources", []) if source.get("enabled")]
    if args.source_id:
        enabled_sources = [source for source in enabled_sources if source.get("id") == args.source_id]
    if not enabled_sources:
        raise SystemExit("No enabled discovery sources matched. Update data/job_sources.yaml first.")

    discovered: list[dict[str, Any]] = []
    processed = 0
    for source in enabled_sources:
        provider = source.get("provider")
        fetcher = FETCHERS.get(provider)
        if not fetcher:
            print(f"Skipping source {source['id']}: unsupported provider {provider}")
            continue

        postings = sorted(fetcher(source), key=posting_sort_key, reverse=True)
        for posting in postings:
            if args.limit and processed >= args.limit:
                break
            processed += 1
            offer = upsert_discovered_offer(source, posting, profile, taxonomy, index_data)
            if offer and offer.get("fit_score_final", 0) >= args.min_score:
                discovered.append(offer)
        if args.limit and processed >= args.limit:
            break

    save_jobs_index(index_data)
    refresh_dashboard_data()

    print(json.dumps(
        {
            "processed": processed,
            "relevant": len(discovered),
            "sources": [source["id"] for source in enabled_sources],
        },
        indent=2,
    ))


if __name__ == "__main__":
    main()
