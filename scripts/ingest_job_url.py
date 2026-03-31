from __future__ import annotations

import argparse
import re
import subprocess
import tempfile
from pathlib import Path
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

from job_search_lib import JOBS_DIR, ensure_job_layout, read_yaml, refresh_dashboard_data, slugify, write_yaml


IGNORED_INPUT_TYPES = {"hidden", "submit", "button", "image", "reset", "password", "search"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch a job offer URL and ingest it into the repository.")
    parser.add_argument("--url", required=True, help="Job offer URL.")
    parser.add_argument("--company", help="Optional company name override.")
    parser.add_argument("--title", help="Optional job title override.")
    parser.add_argument("--location", default="", help="Optional location override.")
    parser.add_argument("--remote-policy", default="", help="Optional remote policy override.")
    parser.add_argument("--employment-type", default="full_time", help="Employment type.")
    parser.add_argument("--company-stage", default="", help="Company stage.")
    return parser.parse_args()


def fetch_html(url: str) -> str:
    response = requests.get(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
            )
        },
        timeout=20,
    )
    response.raise_for_status()
    return response.text


def detect_application_platform(url: str, html: str) -> str:
    haystack = f"{url}\n{html}".lower()
    candidates = {
        "greenhouse": ["greenhouse.io", "boards.greenhouse.io", "grnh.se"],
        "lever": ["lever.co"],
        "ashby": ["ashbyhq.com"],
        "workable": ["workable.com"],
        "smartrecruiters": ["smartrecruiters.com"],
        "teamtailor": ["teamtailor.com"],
        "welcome_to_the_jungle": ["welcometothejungle.com"],
    }
    for platform, needles in candidates.items():
        if any(needle in haystack for needle in needles):
            return platform
    return "custom"


def classify_question_kind(field_type: str, prompt: str, name: str) -> str:
    lowered = f"{prompt} {name}".lower()
    if any(token in lowered for token in ("resume", "cv", "upload", "attach", "attachment")):
        return "resume_upload"
    if any(token in lowered for token in ("privacy policy", "consent", "authorize", "authorized to work", "certify")):
        return "boolean"
    if "language" in lowered and any(token in lowered for token in ("speak", "fluent", "fluently")):
        return "select"
    if any(token in lowered for token in ("gender", "race", "ethnicity", "veteran", "disability")):
        return "select"
    if any(token in lowered for token in ("cover letter", "motivation", "why", "additional information")):
        return "long_text"
    if any(token in lowered for token in ("linkedin", "github", "portfolio", "website")):
        return "link"
    if any(token in lowered for token in ("name", "email", "phone", "location")):
        return "contact"
    if field_type in {"textarea"}:
        return "long_text"
    if field_type in {"checkbox", "radio"}:
        return "boolean"
    if field_type in {"select-one", "select"}:
        return "select"
    return "text"


def normalize_prompt(text: str) -> str:
    text = re.sub(r"\s+", " ", text or "").strip(" :*-")
    return text


def extract_application_questions(html: str) -> list[dict[str, object]]:
    soup = BeautifulSoup(html, "html.parser")
    questions: list[dict[str, object]] = []
    seen: set[str] = set()

    for form in soup.find_all("form")[:5]:
        label_map: dict[str, str] = {}
        for label in form.find_all("label"):
            label_text = normalize_prompt(label.get_text(" ", strip=True))
            html_for = label.get("for")
            if label_text and html_for:
                label_map[html_for] = label_text

        for field in form.find_all(["input", "textarea", "select"]):
            tag_name = field.name.lower()
            field_type = field.get("type", tag_name).lower()
            if field_type in IGNORED_INPUT_TYPES:
                continue

            field_id = field.get("id", "")
            name = field.get("name", "")
            prompt = label_map.get(field_id, "")
            if not prompt:
                prompt = normalize_prompt(field.get("aria-label", "") or field.get("placeholder", ""))
            if not prompt and field.find_parent("label"):
                prompt = normalize_prompt(field.find_parent("label").get_text(" ", strip=True))
            if not prompt and name:
                prompt = normalize_prompt(name.replace("_", " ").replace("-", " "))

            if not prompt:
                continue

            dedupe_key = prompt.lower()
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)

            questions.append(
                {
                    "prompt": prompt,
                    "kind": classify_question_kind(field_type, prompt, name),
                    "required": bool(field.has_attr("required") or field.get("aria-required") == "true"),
                    "source": "form",
                }
            )

    return questions


def extract_metadata(html: str, url: str) -> tuple[str, str, str]:
    soup = BeautifulSoup(html, "html.parser")
    page_title = soup.title.get_text(" ", strip=True) if soup.title else ""
    h1 = soup.find("h1")
    title_guess = h1.get_text(" ", strip=True) if h1 else page_title

    og_site = soup.find("meta", attrs={"property": "og:site_name"})
    company_guess = og_site.get("content", "").strip() if og_site else ""
    if not company_guess:
        domain = urlparse(url).netloc
        company_guess = domain.replace("www.", "").split(".")[0].replace("-", " ").title()

    text_parts = []
    for tag in soup(["script", "style", "noscript", "svg", "img"]):
        tag.decompose()
    for node in soup.find_all(["h1", "h2", "h3", "p", "li"]):
        text = node.get_text(" ", strip=True)
        if text:
            text_parts.append(text)
    cleaned = "\n".join(text_parts)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    return company_guess, title_guess, cleaned.strip()


def main() -> None:
    args = parse_args()
    html = fetch_html(args.url)
    company_guess, title_guess, cleaned = extract_metadata(html, args.url)
    company = args.company or company_guess
    title = args.title or title_guess
    job_id = f"{slugify(company)}-{slugify(title)}"

    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as handle:
        handle.write(cleaned)
        temp_path = Path(handle.name)

    try:
        subprocess.run(
            [
                "python",
                "scripts/ingest_job.py",
                "--company",
                company,
                "--title",
                title,
                "--raw-file",
                str(temp_path),
                "--source-url",
                args.url,
                "--source",
                "url",
                "--location",
                args.location,
                "--remote-policy",
                args.remote_policy,
                "--employment-type",
                args.employment_type,
                "--company-stage",
                args.company_stage,
            ],
            check=True,
        )
    finally:
        temp_path.unlink(missing_ok=True)

    job_dir = JOBS_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    paths = ensure_job_layout(job_dir)
    paths["source_html"].write_text(html, encoding="utf-8")

    offer = read_yaml(job_dir / "offer.yaml", {})
    questions = extract_application_questions(html)
    platform = detect_application_platform(args.url, html)
    offer["application_url"] = args.url
    offer["application_platform"] = platform
    offer["application_questions"] = questions
    offer["page_signals"] = {
        "has_application_form": bool(questions),
        "question_count": len(questions),
        "platform": platform,
    }
    write_yaml(job_dir / "offer.yaml", offer)
    refresh_dashboard_data()


if __name__ == "__main__":
    main()
