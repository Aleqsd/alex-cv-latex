from __future__ import annotations

import json
import re
from urllib.parse import urlparse
from typing import Any

from ingest_job_url import (
    classify_question_kind,
    detect_application_platform,
    extract_application_questions,
    fetch_html,
)


PLAYWRIGHT_AVAILABLE = False
try:
    from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
    from playwright.sync_api import sync_playwright

    PLAYWRIGHT_AVAILABLE = True
except ImportError:  # pragma: no cover - optional runtime dependency
    PlaywrightTimeoutError = Exception  # type: ignore[assignment]
    sync_playwright = None  # type: ignore[assignment]


ACTION_PATTERNS = [
    r"apply",
    r"apply now",
    r"apply for this job",
    r"submit application",
    r"start application",
    r"continue application",
    r"i[' ]?m interested",
    r"join us",
]

COOKIE_PATTERNS = [
    r"accept",
    r"accept all",
    r"allow all",
    r"got it",
    r"agree",
]

PLACEHOLDER_PATTERNS = [
    r"^start typing\b",
    r"^pick date\b",
    r"^select date\b",
    r"^choose date\b",
    r"^mm/?dd/?yyyy$",
    r"^search\b",
]

DEMOGRAPHIC_OPTION_PATTERNS = [
    r"^male$",
    r"^female$",
    r"^decline to self-identify$",
    r"^hispanic or latino$",
    r"^white\b",
    r"^black or african american\b",
    r"^native hawaiian or other pacific islander\b",
    r"^asian\b",
    r"^american indian or alaska native\b",
    r"^two or more races\b",
    r"^i identify as one or more of the classifications of protected veteran listed above$",
    r"^i am not a protected veteran$",
    r"^i decline to self-identify for protected veteran status$",
    r"^yes, i have a disability, or have had one in the past$",
    r"^no, i don't have a disability and have not had one in the past$",
    r"^i do not want to answer$",
]

FRAME_EXTRACTION_SCRIPT = """
() => {
  const ignored = new Set(["hidden", "submit", "button", "image", "reset", "password", "search"]);
  const normalize = (value) => (value || "").replace(/\\s+/g, " ").trim().replace(/^[ :*\\-]+|[ :*\\-]+$/g, "");
  const getTextFromIds = (ids) => (ids || "")
    .split(/\\s+/)
    .map((id) => document.getElementById(id))
    .filter(Boolean)
    .map((node) => normalize(node.textContent))
    .filter(Boolean)
    .join(" ");
  const headingFromContainer = (container, field) => {
    let current = container;
    while (current) {
      const labelIds = current.getAttribute && current.getAttribute("aria-labelledby");
      if (labelIds) {
        const labeled = getTextFromIds(labelIds);
        if (labeled) return labeled;
      }
      const heading = current.querySelector && current.querySelector("legend, [role='heading'], h1, h2, h3, h4, strong, [data-testid*='question'], [class*='question']");
      if (heading && (!field || !heading.contains(field))) {
        const text = normalize(heading.textContent);
        if (text) return text;
      }
      const previous = current.previousElementSibling;
      if (previous) {
        const text = normalize(previous.textContent);
        if (text) return text;
      }
      current = current.parentElement;
    }
    return "";
  };
  const questions = [];
  const seen = new Set();
  let fields = Array.from(document.querySelectorAll("form input, form textarea, form select"));
  if (!fields.length) {
    fields = Array.from(document.querySelectorAll("input, textarea, select"));
  }
  for (const field of fields) {
    const tag = field.tagName.toLowerCase();
    const fieldType = (field.getAttribute("type") || tag).toLowerCase();
    if (ignored.has(fieldType)) continue;
    const rects = field.getClientRects();
    if (!rects.length && !field.closest("form")) continue;

    let prompt = "";
    if (fieldType === "checkbox" || fieldType === "radio") {
      const fieldset = field.closest("fieldset");
      if (fieldset) {
        const legend = fieldset.querySelector("legend");
        if (legend) prompt = normalize(legend.textContent);
      }
      if (!prompt) {
        const grouped = field.closest("[role='group'], [role='radiogroup'], [data-testid*='question'], [data-testid*='field'], [class*='question'], [class*='field']");
        prompt = headingFromContainer(grouped || field.parentElement, field);
      }
    }
    const fieldId = field.getAttribute("id") || "";
    if (!prompt) {
      const labelled = getTextFromIds(field.getAttribute("aria-labelledby"));
      if (labelled) prompt = labelled;
    }
    if (!prompt && fieldId && typeof CSS !== "undefined" && CSS.escape) {
      const label = document.querySelector(`label[for="${CSS.escape(fieldId)}"]`);
      if (label) prompt = normalize(label.textContent);
    }
    if (!prompt) {
      const parentLabel = field.closest("label");
      if (parentLabel) {
        const groupedName = field.getAttribute("name");
        const groupCount = groupedName
          ? document.querySelectorAll(`input[name="${groupedName.replace(/"/g, '\\"')}"], textarea[name="${groupedName.replace(/"/g, '\\"')}"], select[name="${groupedName.replace(/"/g, '\\"')}"]`).length
          : 1;
        if (fieldType !== "radio" || groupCount <= 1) {
          prompt = normalize(parentLabel.textContent);
        }
      }
    }
    if (!prompt) {
      prompt = normalize(
        field.getAttribute("aria-label") ||
        field.getAttribute("placeholder") ||
        field.getAttribute("name") ||
        ""
      );
    }
    if (!prompt) continue;

    const dedupe = prompt.toLowerCase();
    if (seen.has(dedupe)) continue;
    seen.add(dedupe);
    questions.push({
      prompt,
      fieldType,
      name: field.getAttribute("name") || "",
      required: field.required || field.getAttribute("aria-required") === "true",
      source: "browser",
    });
  }

  const actionLabels = Array.from(document.querySelectorAll("button, a, input[type='submit'], input[type='button']"))
    .map((node) => {
      if (node.tagName.toLowerCase() === "input") {
        return normalize(node.getAttribute("value") || "");
      }
      return normalize(node.textContent || node.getAttribute("aria-label") || "");
    })
    .filter(Boolean)
    .slice(0, 40);

  return {
    questions,
    formCount: document.querySelectorAll("form").length,
    actionLabels,
  };
}
"""


def _extract_embedded_json_value(html: str, key: str) -> Any:
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


def _repair_ashby_url(url: str, expected_title: str) -> str:
    parsed = urlparse(url)
    path_parts = [part for part in parsed.path.split("/") if part]
    if not path_parts:
        return url
    board_slug = path_parts[0]
    board_url = f"{parsed.scheme}://{parsed.netloc}/{board_slug}"
    board_html = fetch_html(board_url)
    postings = _extract_embedded_json_value(board_html, "jobPostings") or []
    normalized_title = expected_title.strip().lower()
    for item in postings:
        if str(item.get("title", "")).strip().lower() == normalized_title:
            posting_id = str(item.get("id", "")).strip()
            if posting_id:
                return f"{board_url}/{posting_id}"
    return url


def _normalize_browser_questions(raw_questions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    def clean_prompt(value: str) -> str:
        value = re.sub(r"\s+", " ", value or "").strip(" :*-")
        value = re.sub(r"\*+\s*required\b", "", value, flags=re.IGNORECASE)
        value = re.sub(r"\brequired\.\s*", "", value, flags=re.IGNORECASE)
        value = re.sub(r"\s+yes\s+no$", "", value, flags=re.IGNORECASE)
        lowered = value.lower()
        if "resume/cv" in lowered and "accepted file types" in lowered:
            return "Resume/CV"
        if "results found" in lowered and "accepted file types" in lowered:
            return ""
        value = re.sub(r"\s{2,}", " ", value).strip(" .")
        return value

    normalized: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in raw_questions:
        prompt = clean_prompt(str(item.get("prompt", "")))
        if not prompt:
            continue
        dedupe = prompt.lower()
        if dedupe in seen:
            continue
        if dedupe in {"yes", "no", "true", "false"}:
            continue
        if any(re.search(pattern, dedupe, re.IGNORECASE) for pattern in PLACEHOLDER_PATTERNS):
            continue
        if any(re.search(pattern, dedupe, re.IGNORECASE) for pattern in DEMOGRAPHIC_OPTION_PATTERNS):
            continue
        seen.add(dedupe)
        field_type = str(item.get("fieldType", "")).lower()
        name = str(item.get("name", ""))
        normalized.append(
            {
                "prompt": prompt,
                "kind": classify_question_kind(field_type, prompt, name),
                "required": bool(item.get("required")),
                "source": item.get("source", "browser"),
            }
        )
    return normalized


def _review_application_questions(questions: list[dict[str, Any]]) -> dict[str, Any]:
    suspicious_prompts: list[str] = []
    reasons: list[str] = []
    generic_prompts = {
        "country",
        "name",
        "email",
        "resume",
        "phone number",
    }
    for question in questions:
        prompt = str(question.get("prompt", "")).strip()
        lowered = prompt.lower()
        if any(re.search(pattern, lowered, re.IGNORECASE) for pattern in PLACEHOLDER_PATTERNS):
            suspicious_prompts.append(prompt)
        elif prompt in {"Start typing...", "Pick date..."}:
            suspicious_prompts.append(prompt)
        elif question.get("kind") == "boolean" and len(prompt.split()) <= 2 and lowered not in generic_prompts:
            suspicious_prompts.append(prompt)

    if suspicious_prompts:
        reasons.append("Some detected prompts still look like option labels or placeholders.")
    if len(questions) >= 20 and sum(1 for item in questions if item.get("kind") == "boolean") >= 10:
        reasons.append("Long compliance or demographic sections may still need a quick manual review.")

    return {
        "review_required": bool(reasons),
        "review_reasons": reasons,
        "suspicious_prompts": suspicious_prompts[:8],
    }


def _extract_frame_payload(frame: Any) -> dict[str, Any]:
    payload = frame.evaluate(FRAME_EXTRACTION_SCRIPT)
    questions = _normalize_browser_questions(payload.get("questions", []))
    return {
        "questions": questions,
        "form_count": int(payload.get("formCount", 0) or 0),
        "action_labels": payload.get("actionLabels", []) or [],
    }


def _collect_page_payload(page: Any) -> dict[str, Any]:
    best_questions: list[dict[str, Any]] = []
    form_count = 0
    action_labels: list[str] = []
    frame_count = 0

    for frame in page.frames:
        try:
            payload = _extract_frame_payload(frame)
        except Exception:
            continue
        frame_count += 1
        form_count += payload["form_count"]
        action_labels.extend(payload["action_labels"])
        if len(payload["questions"]) > len(best_questions):
            best_questions = payload["questions"]

    return {
        "questions": best_questions,
        "form_count": form_count,
        "frame_count": frame_count,
        "action_labels": list(dict.fromkeys(action_labels)),
    }


def _dismiss_cookie_banners(page: Any) -> None:
    locator = page.locator("button, a")
    count = min(locator.count(), 25)
    for index in range(count):
        node = locator.nth(index)
        try:
            text = (node.inner_text(timeout=500) or "").strip().lower()
        except Exception:
            continue
        if not text:
            continue
        if any(re.search(pattern, text, re.IGNORECASE) for pattern in COOKIE_PATTERNS):
            try:
                node.click(timeout=1000)
                page.wait_for_timeout(500)
                return
            except Exception:
                continue


def _click_apply_action(page: Any) -> str:
    locator = page.locator("button, a, input[type='submit'], input[type='button']")
    count = min(locator.count(), 50)
    for index in range(count):
        node = locator.nth(index)
        try:
            tag_name = node.evaluate("(el) => el.tagName.toLowerCase()")
        except Exception:
            continue
        try:
            if tag_name == "input":
                label = (node.get_attribute("value") or "").strip()
            else:
                label = (node.inner_text(timeout=500) or node.get_attribute("aria-label") or "").strip()
        except Exception:
            continue
        if not label:
            continue
        if not any(re.search(pattern, label, re.IGNORECASE) for pattern in ACTION_PATTERNS):
            continue
        try:
            with page.context.expect_page(timeout=1500) as popup_info:
                node.click(timeout=1500)
            next_page = popup_info.value
            next_page.wait_for_load_state("domcontentloaded", timeout=5000)
            page = next_page
        except Exception:
            try:
                node.click(timeout=1500)
            except Exception:
                continue
            try:
                page.wait_for_load_state("domcontentloaded", timeout=5000)
            except PlaywrightTimeoutError:
                page.wait_for_timeout(1000)
        return label
    return ""


def inspect_application_page(
    url: str,
    expected_title: str = "",
    browser_mode: str = "auto",
    timeout_ms: int = 15000,
) -> dict[str, Any]:
    html = fetch_html(url)
    platform = detect_application_platform(url, html)
    if platform == "ashby" and expected_title:
        repaired_url = _repair_ashby_url(url, expected_title)
        if repaired_url != url:
            url = repaired_url
            html = fetch_html(url)
            platform = detect_application_platform(url, html)
    static_questions = extract_application_questions(html)
    result = {
        "source_page_url": url,
        "application_url": url,
        "html": html,
        "platform": platform,
        "questions": static_questions,
        "page_signals": {
            "has_application_form": bool(static_questions),
            "question_count": len(static_questions),
            "platform": platform,
            "inspection_mode": "static",
            "browser_available": PLAYWRIGHT_AVAILABLE,
        },
    }
    result["page_signals"].update(_review_application_questions(static_questions))

    should_use_browser = browser_mode == "always" or (
        browser_mode == "auto" and (not static_questions or platform in {"ashby", "teamtailor", "greenhouse", "lever", "workable"})
    )
    if not should_use_browser or not PLAYWRIGHT_AVAILABLE:
        if should_use_browser and not PLAYWRIGHT_AVAILABLE:
            result["page_signals"]["browser_error"] = "playwright_not_installed"
        return result

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
            page.wait_for_timeout(1200)
            _dismiss_cookie_banners(page)
            initial_payload = _collect_page_payload(page)
            clicked_label = ""
            best_payload = initial_payload
            source_page_url = page.url
            best_url = page.url
            best_html = page.content()

            if len(initial_payload["questions"]) <= len(static_questions):
                clicked_label = _click_apply_action(page)
                if clicked_label:
                    page.wait_for_timeout(1500)
                    clicked_payload = _collect_page_payload(page)
                    if len(clicked_payload["questions"]) >= len(best_payload["questions"]):
                        best_payload = clicked_payload
                        best_url = page.url
                        best_html = page.content()

            browser_questions = best_payload["questions"]
            if len(browser_questions) >= len(result["questions"]):
                result["questions"] = browser_questions
                result["html"] = best_html
                result["application_url"] = best_url

            result["source_page_url"] = source_page_url
            result["platform"] = detect_application_platform(result["application_url"], result["html"])
            result["page_signals"] = {
                "has_application_form": bool(result["questions"]),
                "question_count": len(result["questions"]),
                "platform": result["platform"],
                "inspection_mode": "browser",
                "browser_available": True,
                "frame_count": best_payload["frame_count"],
                "form_count": best_payload["form_count"],
                "clicked_apply_action": clicked_label,
                "action_labels": best_payload["action_labels"][:12],
                "source_page_url": source_page_url,
                "final_url": result["application_url"],
            }
            result["page_signals"].update(_review_application_questions(result["questions"]))
        finally:
            context.close()
            browser.close()

    return result
