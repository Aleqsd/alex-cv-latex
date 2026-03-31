from __future__ import annotations

import filecmp
import json
import re
import tempfile
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import yaml


REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"
PROFILE_DIR = REPO_ROOT / "profile"
JOBS_DIR = REPO_ROOT / "jobs"
DASHBOARD_OVERVIEW = REPO_ROOT / "dashboard" / "data" / "overview.json"
DASHBOARD_STORE = REPO_ROOT / "dashboard" / "data" / "store.json"
JOB_SOURCES_CONFIG = DATA_DIR / "job_sources.yaml"
JOB_SOURCE_DIRNAME = "source"
JOB_ARTIFACTS_DIRNAME = "artifacts"
JOB_NOTES_DIRNAME = "notes"
EXPLICIT_REMOTE_PATTERNS = (
    "full remote",
    "fully remote",
    "100% remote",
    "remote -",
    "remote,",
    "remote ",
    "work from anywhere",
    "distributed team",
)
US_ONLY_REMOTE_PATTERNS = (
    "remote - us",
    "remote - u.s.",
    "remote - usa",
    "remote, us",
    "remote, u.s.",
    "remote, usa",
    "remote us",
    "us remote",
    "u.s. remote",
    "usa remote",
    "remote - united states",
    "remote, united states",
    "united states remote",
    "remote within the united states",
    "remote in the united states",
    "remote anywhere in the us",
    "remote anywhere in the united states",
    "us-only remote",
    "remote (us",
    "remote (u.s.",
    "remote (usa",
)
REMOTE_ALLOWED_MARKERS = (
    "france",
    "paris",
    "europe",
    "european union",
    "european economic area",
    "emea",
    "worldwide",
    "global",
    "anywhere",
    "work from anywhere",
    "distributed",
)
REMOTE_RESTRICTED_MARKERS = (
    "united states",
    "usa",
    "u.s.",
    "us remote",
    "remote us",
    "americas",
    "north america",
    "south america",
    "latin america",
    "latam",
    "apac",
    "asia pacific",
    "new york",
    "nyc",
    "san francisco",
    "seattle",
    "india",
    "poland",
    "belgium",
    "brussels",
    "germany",
    "munich",
    "berlin",
    "ireland",
    "dublin",
    "united kingdom",
    "uk",
    "london",
    "spain",
    "portugal",
    "italy",
    "netherlands",
    "amsterdam",
    "canada",
    "toronto",
    "vancouver",
    "mexico",
    "brazil",
    "argentina",
    "colombia",
    "chile",
    "australia",
    "sydney",
    "melbourne",
    "singapore",
    "japan",
    "tokyo",
    "korea",
    "hong kong",
    "uae",
    "dubai",
)
REMOTE_REGION_PATTERNS = {
    "France": ("france", "paris"),
    "Europe": ("europe", "european union", "european economic area", "eea", "eu remote"),
    "EMEA": ("emea",),
    "Americas": ("americas", "north america", "south america", "latin america", "latam"),
    "APAC": ("apac", "asia pacific"),
    "United States": (
        "united states",
        "usa",
        "u.s.",
        "us only",
        "us-only",
        "remote us",
        "us remote",
    ),
    "United Kingdom": ("united kingdom", "uk", "london"),
    "Ireland": ("ireland", "dublin"),
    "Germany": ("germany", "munich", "berlin"),
    "Belgium": ("belgium", "brussels"),
    "Poland": ("poland",),
    "India": ("india",),
    "Spain": ("spain",),
    "Portugal": ("portugal",),
    "Italy": ("italy",),
    "Netherlands": ("netherlands", "amsterdam"),
    "Canada": ("canada", "toronto", "vancouver"),
    "Australia": ("australia", "sydney", "melbourne"),
    "Singapore": ("singapore",),
    "Japan": ("japan", "tokyo"),
    "Worldwide": ("worldwide", "global", "anywhere", "work from anywhere"),
}
NON_REMOTE_PATTERNS = (
    "hybrid",
    "on-site",
    "onsite",
    "in office",
    "office-based",
    "office based",
)


def read_yaml(path: Path, default: Any | None = None) -> Any:
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as handle:
        loaded = yaml.safe_load(handle)
    if loaded is None:
        return default
    return loaded


def write_yaml(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        yaml.safe_dump(payload, handle, sort_keys=False, allow_unicode=False)
        temp_path = Path(handle.name)
    temp_path.replace(path)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")
        temp_path = Path(handle.name)
    temp_path.replace(path)


def infer_remote_policy(*parts: str) -> str:
    text = " ".join(str(part or "") for part in parts).strip().lower()
    if not text:
        return ""
    if any(pattern in text for pattern in NON_REMOTE_PATTERNS):
        if "hybrid" in text:
            return "hybrid"
        return "onsite"
    if any(pattern in text for pattern in EXPLICIT_REMOTE_PATTERNS):
        if any(pattern in text for pattern in US_ONLY_REMOTE_PATTERNS):
            return "remote_us_only"
        return "remote"
    return ""


def remote_scope_text(*parts: str) -> str:
    primary_parts = [str(part or "").strip().lower() for part in parts[:2] if str(part or "").strip()]
    if primary_parts:
        return " ".join(primary_parts)
    return " ".join(str(part or "").strip().lower() for part in parts if str(part or "").strip())


def is_explicit_remote_offer(*parts: str) -> bool:
    return infer_remote_policy(*parts) in {"remote", "remote_us_only"}


def is_us_only_remote_offer(*parts: str) -> bool:
    return infer_remote_policy(*parts) == "remote_us_only"


def is_remote_eligible_for_constraints(constraints: dict[str, Any], *parts: str) -> bool:
    if not is_explicit_remote_offer(*parts):
        return False
    if constraints.get("exclude_remote_us_only", False) and is_us_only_remote_offer(*parts):
        return False

    scope_text = remote_scope_text(*parts)
    text = " ".join(str(part or "") for part in parts).strip().lower()
    if not text:
        return False

    base_country = str(constraints.get("base_country", "")).strip().lower()
    if base_country and (base_country in scope_text or base_country in text):
        return True

    if any(marker in scope_text for marker in REMOTE_RESTRICTED_MARKERS):
        return False

    if any(marker in scope_text for marker in REMOTE_ALLOWED_MARKERS):
        return True

    if any(marker in text for marker in REMOTE_ALLOWED_MARKERS):
        return True

    if any(marker in text for marker in REMOTE_RESTRICTED_MARKERS):
        return False

    return True


def remote_regions_from_text(*parts: str) -> list[str]:
    text = remote_scope_text(*parts) or " ".join(str(part or "") for part in parts).strip().lower()
    regions: list[str] = []
    if not text:
        return regions
    for label, patterns in REMOTE_REGION_PATTERNS.items():
        if any(pattern in text for pattern in patterns):
            regions.append(label)
    return regions


def normalize_remote_profile(constraints: dict[str, Any], *parts: str) -> dict[str, Any]:
    text = " ".join(str(part or "") for part in parts).strip().lower()
    policy = infer_remote_policy(*parts) or "unspecified"
    explicit = is_explicit_remote_offer(*parts)
    eligible = is_remote_eligible_for_constraints(constraints, *parts)
    regions = remote_regions_from_text(*parts)
    base_country = str(constraints.get("base_country", "")).strip().title()

    if policy == "hybrid":
        label = "Hybrid"
        scope = "hybrid"
    elif policy == "onsite":
        label = "On-site"
        scope = "onsite"
    elif not explicit:
        label = "Remote not explicit"
        scope = "unspecified"
    elif "Worldwide" in regions:
        label = "Remote (Global)"
        scope = "global"
    elif base_country and base_country in regions and len(regions) == 1:
        label = f"Remote ({base_country})"
        scope = "base_country"
    elif base_country and base_country in regions:
        label = f"Remote ({base_country} + region limits)"
        scope = "multi_region_including_base"
    elif "Europe" in regions or "EMEA" in regions:
        label = "Remote (Europe / EMEA)"
        scope = "regional"
    elif regions:
        label = "Remote (" + ", ".join(regions[:2]) + (", ..." if len(regions) > 2 else "") + ")"
        scope = "country_limited"
    elif explicit:
        label = "Remote (Explicit)"
        scope = "explicit_unknown_scope"
    else:
        label = "Remote not explicit"
        scope = "unspecified"

    reason = ""
    if explicit and not eligible:
        if is_us_only_remote_offer(*parts):
            reason = "Remote restricted to the United States."
        else:
            reason = "Remote scope appears incompatible with the current search geography."

    return {
        "policy": policy,
        "scope": scope,
        "regions": regions,
        "label": label,
        "eligible": eligible,
        "explicit": explicit,
        "reason": reason,
        "raw": text,
    }


def job_source_dir(job_dir: Path) -> Path:
    return job_dir / JOB_SOURCE_DIRNAME


def job_artifacts_dir(job_dir: Path) -> Path:
    return job_dir / JOB_ARTIFACTS_DIRNAME


def job_notes_dir(job_dir: Path) -> Path:
    return job_dir / JOB_NOTES_DIRNAME


def ensure_job_layout(job_dir: Path) -> dict[str, Path]:
    source_dir = job_source_dir(job_dir)
    artifacts_dir = job_artifacts_dir(job_dir)
    notes_dir = job_notes_dir(job_dir)
    source_dir.mkdir(parents=True, exist_ok=True)
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    notes_dir.mkdir(parents=True, exist_ok=True)

    legacy_moves = {
        "raw.md": source_dir / "raw.md",
        "source.html": source_dir / "source.html",
        "fit_report.md": artifacts_dir / "fit_report.md",
        "research.md": notes_dir / "research.md",
        "decision.md": notes_dir / "decision.md",
    }
    for legacy_name, target_path in legacy_moves.items():
        legacy_path = job_dir / legacy_name
        if legacy_path.exists() and not target_path.exists():
            legacy_path.replace(target_path)
        elif legacy_path.exists() and target_path.exists():
            try:
                if filecmp.cmp(legacy_path, target_path, shallow=False):
                    legacy_path.unlink()
            except OSError:
                pass

    return {
        "source_dir": source_dir,
        "artifacts_dir": artifacts_dir,
        "notes_dir": notes_dir,
        "raw": source_dir / "raw.md",
        "source_html": source_dir / "source.html",
        "fit_report": artifacts_dir / "fit_report.md",
        "research": notes_dir / "research.md",
        "decision": notes_dir / "decision.md",
    }


def slugify(value: str) -> str:
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-")


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def parse_iso_datetime(value: str) -> datetime | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None


def latest_status_timestamp(offer: dict[str, Any], statuses: set[str] | None = None) -> datetime | None:
    timestamps: list[datetime] = []
    for item in offer.get("status_history", []) or []:
        target = str(item.get("to", "")).strip()
        if statuses and target not in statuses:
            continue
        parsed = parse_iso_datetime(str(item.get("timestamp", "")))
        if parsed:
            timestamps.append(parsed)
    if timestamps:
        return max(timestamps)
    return parse_iso_datetime(str(offer.get("updated_at") or offer.get("source_date") or ""))


def age_in_days(value: datetime | None) -> int | None:
    if value is None:
        return None
    delta = datetime.now(timezone.utc) - value.astimezone(timezone.utc)
    return max(0, delta.days)


def follow_up_due_timestamp(offer: dict[str, Any], delay_days: int = 7) -> datetime | None:
    if str(offer.get("status", "")) not in {"applied", "recruiter_contact", "follow_up_due"}:
        return None
    anchor = latest_status_timestamp(offer, {"applied", "recruiter_contact"})
    if anchor is None:
        return None
    return anchor + timedelta(days=delay_days)


def append_status_transition(offer: dict[str, Any], new_status: str, note: str = "") -> None:
    previous = offer.get("status", "")
    if previous == new_status and not note:
        return
    offer["status"] = new_status
    offer.setdefault("status_history", []).append(
        {
            "timestamp": utc_now_iso(),
            "from": previous,
            "to": new_status,
            "note": note,
        }
    )


def load_profile() -> dict[str, Any]:
    return {
        "basics": read_yaml(PROFILE_DIR / "basics.yaml", {}),
        "skills": read_yaml(PROFILE_DIR / "skills.yaml", {}),
        "achievements": read_yaml(PROFILE_DIR / "achievements.yaml", {}),
        "preferences": read_yaml(PROFILE_DIR / "preferences.yaml", {}),
        "constraints": read_yaml(PROFILE_DIR / "constraints.yaml", {}),
        "experience": read_yaml(PROFILE_DIR / "experience.yaml", {}),
        "education": read_yaml(PROFILE_DIR / "education.yaml", {}),
    }


def load_jobs_index() -> dict[str, Any]:
    return read_yaml(DATA_DIR / "jobs_index.yaml", {"version": 1, "jobs": []})


def prune_jobs_index(index_data: dict[str, Any]) -> dict[str, Any]:
    jobs = index_data.get("jobs", [])
    index_data["jobs"] = [
        entry
        for entry in jobs
        if (REPO_ROOT / entry.get("path", "") / "offer.yaml").exists()
    ]
    return index_data


def save_jobs_index(index_data: dict[str, Any]) -> None:
    prune_jobs_index(index_data)
    write_yaml(DATA_DIR / "jobs_index.yaml", index_data)


def load_taxonomy() -> dict[str, Any]:
    return read_yaml(DATA_DIR / "taxonomy.yaml", {"role_families": {}, "status_groups": {}})


def load_job_sources_config() -> dict[str, Any]:
    return read_yaml(JOB_SOURCES_CONFIG, {"version": 1, "sources": []})


def flatten_profile_terms(profile: dict[str, Any]) -> set[str]:
    skills = profile.get("skills", {})
    terms: set[str] = set()
    for key in ("languages", "frameworks", "cloud_platform", "ai_tooling", "practices"):
        for item in skills.get(key, []) or []:
            terms.add(str(item).lower())
    return terms


def classify_role_family(title: str, description: str, taxonomy: dict[str, Any]) -> str:
    haystack = f"{title} {description}".lower()
    scores: dict[str, int] = {}
    for role_family, config in taxonomy.get("role_families", {}).items():
        keywords = config.get("keywords", [])
        score = sum(2 if keyword in title.lower() else 1 for keyword in keywords if keyword in haystack)
        scores[role_family] = score
    best = max(scores.items(), key=lambda item: item[1], default=("software_engineer", 0))
    return best[0] if best[1] > 0 else "software_engineer"


def collect_profile_themes(profile: dict[str, Any]) -> Counter[str]:
    counter: Counter[str] = Counter()
    for experience in profile.get("experience", {}).get("experiences", []):
        for bullet in experience.get("bullets", []):
            for theme in bullet.get("supported_themes", []):
                counter[str(theme)] += 1
    return counter


def infer_seniority(title: str, description: str) -> str:
    haystack = f"{title} {description}".lower()
    if "staff" in haystack or "principal" in haystack:
        return "staff"
    if "senior" in haystack or "sr." in haystack or "lead" in haystack:
        return "senior"
    if "junior" in haystack or "entry" in haystack:
        return "junior"
    return "mid"


def extract_keywords(description: str, profile_terms: set[str]) -> tuple[list[str], list[str]]:
    lowered = description.lower()
    required = sorted(term for term in profile_terms if term in lowered)
    preferred = sorted(term for term in profile_terms if f"nice to have {term}" in lowered or f"preferred {term}" in lowered)
    return required, preferred


def compute_fit(offer: dict[str, Any], profile: dict[str, Any], taxonomy: dict[str, Any]) -> dict[str, Any]:
    profile_terms = flatten_profile_terms(profile)
    profile_themes = collect_profile_themes(profile)
    title = offer.get("job_title", "")
    title_lower = str(title).lower()
    description = offer.get("job_description_clean") or offer.get("job_description_raw") or ""
    role_family = offer.get("normalized_role_family") or classify_role_family(title, description, taxonomy)

    required_keywords = offer.get("keywords_required") or []
    if not required_keywords:
        required_keywords, preferred_keywords = extract_keywords(description, profile_terms)
    else:
        preferred_keywords = offer.get("keywords_preferred") or []

    matched_required = [term for term in required_keywords if term.lower() in profile_terms]
    matched_preferred = [term for term in preferred_keywords if term.lower() in profile_terms]
    required_ratio = 1.0 if not required_keywords else len(matched_required) / max(len(required_keywords), 1)
    preferred_ratio = 1.0 if not preferred_keywords else len(matched_preferred) / max(len(preferred_keywords), 1)

    preferred_roles = profile.get("preferences", {}).get("preferred_role_families", [])
    role_rank = preferred_roles.index(role_family) if role_family in preferred_roles else None
    if role_rank == 0:
        role_family_match = 22
    elif role_rank == 1:
        role_family_match = 20
    elif role_rank == 2:
        role_family_match = 17
    else:
        role_family_match = 8
    core_skills_match = round(20 * (0.8 * required_ratio + 0.2 * preferred_ratio))

    role_theme_map = {
        "software_engineer": ["backend_services", "full_stack", "product_delivery", "developer_tooling"],
        "backend_engineer": ["backend_services", "product_delivery", "integrations"],
        "founding_engineer": ["founding", "startup", "0_to_1", "recruiting", "cross_functional_execution"],
        "platform_devops_engineer": ["ci_cd", "developer_tooling", "release_engineering", "test_automation", "qa_enablement"],
    }
    target_themes = role_theme_map.get(role_family, [])
    themed_hits = sum(1 for theme in target_themes if profile_themes.get(theme))
    experience_relevance = min(20, 8 + themed_hits * 3)

    offer_seniority = offer.get("seniority_estimate") or infer_seniority(title, description)
    if offer_seniority == "staff":
        seniority_alignment = 2
    elif offer_seniority == "senior":
        seniority_alignment = 9
    elif offer_seniority == "junior":
        seniority_alignment = 4
    else:
        seniority_alignment = 8

    domain_keywords = ("gaming", "developer", "cloud", "platform", "software")
    domain_relevance = 5 if any(keyword in description.lower() for keyword in domain_keywords) else 3

    achievements = profile.get("achievements", {}).get("achievements", [])
    achievement_relevance = min(
        10,
        3
        + sum(
            1
            for achievement in achievements
            if any(theme in target_themes for theme in achievement.get("themes", []))
        ),
    )

    constraints = profile.get("constraints", {}).get("location_constraints", {})
    location = str(offer.get("location", ""))
    remote_policy = str(offer.get("remote_policy", ""))
    remote_profile = normalize_remote_profile(
        constraints,
        remote_policy,
        location,
        offer.get("job_title", ""),
        offer.get("job_description_clean", ""),
    )
    explicit_remote = remote_profile["explicit"]
    us_only_remote = constraints.get("exclude_remote_us_only", False) and is_us_only_remote_offer(
        remote_policy,
        location,
        offer.get("job_title", ""),
        offer.get("job_description_clean", ""),
    )
    eligible_remote = remote_profile["eligible"]
    if eligible_remote and remote_profile["scope"] in {"base_country", "multi_region_including_base", "regional", "global"}:
        logistics_fit = 10
    elif eligible_remote and remote_profile["scope"] == "country_limited":
        logistics_fit = 8
    elif eligible_remote and remote_profile["scope"] == "explicit_unknown_scope":
        logistics_fit = 4
    else:
        logistics_fit = 0

    strategic_fit = 6 if role_rank == 0 else 5 if role_rank in {1, 2} else 1

    ats_score = min(100, role_family_match * 2 + core_skills_match * 2 + logistics_fit + 10)
    human_score = min(
        100,
        experience_relevance * 3
        + achievement_relevance * 2
        + seniority_alignment * 2
        + role_family_match,
    )
    strategic_score = min(100, strategic_fit * 12 + logistics_fit * 2 + domain_relevance * 4)
    final_score = round(0.45 * ats_score + 0.40 * human_score + 0.15 * strategic_score)
    unsupported = [term for term in required_keywords if term.lower() not in profile_terms]

    title_penalty = 0
    off_target_markers = {
        "frontend": 18,
        "front-end": 18,
        "mobile": 18,
        "android": 18,
        "ios": 18,
        "data scientist": 16,
        "research scientist": 16,
        "engineering manager": 22,
        "manager": 18,
        "team leader": 18,
        "head of": 22,
        "director": 22,
    }
    matched_off_target = [marker for marker in off_target_markers if marker in title_lower]
    for marker in matched_off_target:
        title_penalty += off_target_markers[marker]

    if offer_seniority == "staff":
        final_score -= 12
        human_score = max(0, human_score - 10)
        strategic_score = max(0, strategic_score - 8)

    if remote_profile["scope"] == "explicit_unknown_scope":
        final_score -= 10
        ats_score = max(0, ats_score - 8)
        strategic_score = max(0, strategic_score - 12)

    if len(matched_required) < 2 and required_keywords:
        final_score -= 8
        ats_score = max(0, ats_score - 8)

    if len(unsupported) >= 4:
        final_score -= 6
        human_score = max(0, human_score - 6)

    if title_penalty:
        final_score -= title_penalty
        ats_score = max(0, ats_score - min(20, title_penalty // 2))
        human_score = max(0, human_score - min(24, title_penalty))
        strategic_score = max(0, strategic_score - min(20, title_penalty))

    ats_score = max(0, min(100, round(ats_score)))
    human_score = max(0, min(100, round(human_score)))
    strategic_score = max(0, min(100, round(strategic_score)))
    final_score = max(0, min(100, round(final_score)))

    strengths = []
    if matched_required:
        strengths.append(f"Direct keyword overlap with {', '.join(matched_required[:5])}.")
    if role_family in preferred_roles:
        strengths.append(f"Role family aligns with preferred target: {role_family_name(role_family)}.")
    if achievement_relevance >= 7:
        strengths.append("Strong quantified delivery evidence is available for this role family.")
    if remote_profile["eligible"] and remote_profile["label"]:
        strengths.append(f"Remote fit is acceptable under current constraints: {remote_profile['label']}.")

    risks = []
    if unsupported:
        risks.append(f"Missing or weak evidence for: {', '.join(unsupported[:5])}.")
    if matched_off_target:
        risks.append(f"Title points to an off-target area: {', '.join(matched_off_target[:3])}.")
    if offer_seniority == "staff":
        risks.append("Offer may require broader staff-level organizational influence.")
    if us_only_remote:
        risks.append("Offer is remote but restricted to the United States.")
    elif explicit_remote and not eligible_remote:
        risks.append(remote_profile["reason"] or "Offer is remote but geographically restricted outside the current search location.")
    elif logistics_fit < 10:
        risks.append("Offer does not explicitly state full remote work.")

    if constraints.get("remote_only_default", False) and constraints.get("require_explicit_remote", False) and not explicit_remote:
        recommendation = "skip"
        final_score = min(final_score, 35)
        ats_score = min(ats_score, 35)
        strategic_score = min(strategic_score, 20)
    elif not eligible_remote:
        recommendation = "skip"
        final_score = min(final_score, 35)
        ats_score = min(ats_score, 35)
        strategic_score = min(strategic_score, 20)
    elif title_penalty >= 18:
        recommendation = "skip"
    elif final_score >= 84 and ats_score >= 82 and human_score >= 78 and logistics_fit >= 8:
        recommendation = "apply"
    elif final_score >= 70 and ats_score >= 68 and human_score >= 64:
        recommendation = "maybe"
    else:
        recommendation = "skip"

    evidence_quality = {
        "direct": len(matched_required),
        "adjacent": len(matched_preferred),
        "weak": len(unsupported),
        "unsupported": max(0, len(required_keywords) - len(matched_required) - len(matched_preferred)),
    }

    subscores = {
        "role_family_match": role_family_match,
        "core_skills_match": core_skills_match,
        "experience_relevance": experience_relevance,
        "seniority_alignment": seniority_alignment,
        "domain_relevance": domain_relevance,
        "achievement_relevance": achievement_relevance,
        "logistics_fit": logistics_fit,
        "strategic_fit": strategic_fit,
    }

    return {
        "normalized_role_family": role_family,
        "keywords_required": required_keywords,
        "keywords_preferred": preferred_keywords,
        "fit_score_ats": round(ats_score),
        "fit_score_human": round(human_score),
        "fit_score_strategic": round(strategic_score),
        "fit_score_final": final_score,
        "fit_recommendation": recommendation,
        "strengths": strengths[:3],
        "risks": risks[:3],
        "subscores": subscores,
        "confidence": "high" if len(required_keywords) >= 3 else "medium",
        "evidence_quality": evidence_quality,
        "seniority_estimate": offer_seniority,
        "remote_profile": remote_profile,
    }


def ensure_job_index_entry(index_data: dict[str, Any], offer: dict[str, Any], job_dir: Path) -> None:
    jobs = index_data.setdefault("jobs", [])
    relative_path = str(job_dir.relative_to(REPO_ROOT)).replace("\\", "/")
    entry = next((item for item in jobs if item.get("id") == offer["id"]), None)
    payload = {
        "id": offer["id"],
        "company_name": offer.get("company_name", ""),
        "job_title": offer.get("job_title", ""),
        "normalized_role_family": offer.get("normalized_role_family", ""),
        "status": offer.get("status", "discovered"),
        "fit_score_final": offer.get("fit_score_final", 0),
        "path": relative_path,
        "updated_at": utc_now_iso(),
    }
    if entry is None:
        jobs.append(payload)
    else:
        entry.update(payload)


def load_all_offers() -> list[dict[str, Any]]:
    offers: list[dict[str, Any]] = []
    index_data = load_jobs_index()
    for entry in index_data.get("jobs", []):
        job_dir = REPO_ROOT / entry.get("path", "")
        offer_path = job_dir / "offer.yaml"
        offer = read_yaml(offer_path, {})
        if offer:
            offers.append(offer)
    return offers


def role_family_display(role_family: str, profile: dict[str, Any]) -> str:
    basics = profile.get("basics", {})
    defaults = basics.get("headline_defaults", {})
    return defaults.get(role_family, role_family.replace("_", " ").title())


def role_family_name(role_family: str) -> str:
    labels = {
        "software_engineer": "Software Engineer",
        "backend_engineer": "Backend Engineer",
        "founding_engineer": "Founding Engineer",
        "platform_devops_engineer": "Platform / DevOps Engineer",
    }
    return labels.get(role_family, role_family.replace("_", " ").title())


def normalize_offer_title_for_dedupe(title: str) -> str:
    lowered = str(title or "").lower()
    lowered = lowered.replace("—", "-").replace("–", "-")
    lowered = re.sub(r"\(([^)]*(remote|hybrid|onsite|on-site|paris|london|seattle|tokyo|dublin|munich|singapore|sydney|nyc|new york|san francisco|emea|apac|europe|us|usa|uk|france|germany|india|japan)[^)]*)\)", "", lowered)
    lowered = re.sub(r"\s+-\s+(remote.*|paris|london|seattle|tokyo|dublin|munich|singapore|sydney|nyc|new york city|san francisco|seattle|emea|apac|europe|us|usa|uk|france|germany|india|japan)$", "", lowered)
    lowered = re.sub(r"[^a-z0-9]+", " ", lowered)
    lowered = re.sub(r"\s+", " ", lowered).strip()
    return lowered


def dedupe_group_key(offer: dict[str, Any]) -> str:
    company = slugify(str(offer.get("company_name", "")).strip())
    title = normalize_offer_title_for_dedupe(str(offer.get("job_title", "")).strip())
    return f"{company}:{slugify(title)}"


def asset_presence_score(job_dir: Path) -> int:
    paths = ensure_job_layout(job_dir)
    return sum(
        1
        for path in (
            paths["fit_report"],
            paths["research"],
            paths["decision"],
        )
        if path.exists()
    )


def compute_duplicate_relationships(offers: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for offer in offers:
        grouped.setdefault(dedupe_group_key(offer), []).append(offer)

    metadata: dict[str, dict[str, Any]] = {}
    for group_key, group in grouped.items():
        ranked = sorted(
            group,
            key=lambda offer: (
                int(offer.get("fit_score_final", 0) or 0),
                asset_presence_score(JOBS_DIR / offer.get("id", "")),
                str(offer.get("last_seen_at") or offer.get("updated_at") or offer.get("source_date") or ""),
            ),
            reverse=True,
        )
        canonical = ranked[0]
        canonical_id = canonical.get("id", "")
        group_ids = [item.get("id", "") for item in ranked if item.get("id")]
        for offer in ranked:
            offer_id = offer.get("id", "")
            metadata[offer_id] = {
                "groupKey": group_key,
                "canonicalId": canonical_id,
                "isDuplicate": offer_id != canonical_id,
                "groupIds": group_ids,
                "duplicateCount": max(0, len(group_ids) - 1),
            }
    return metadata


def artifact_preview(path: Path, limit: int = 700) -> str:
    if not path.exists():
        return ""
    try:
        text = path.read_text(encoding="utf-8", errors="ignore").strip()
    except OSError:
        return ""
    text = re.sub(r"\r\n?", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "\n..."


def source_metrics(config: dict[str, Any], offers: list[dict[str, Any]], duplicate_map: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    metrics: list[dict[str, Any]] = []
    offers_by_source: dict[str, list[dict[str, Any]]] = {}
    for offer in offers:
        source_id = str(offer.get("discovery_source", "")).strip()
        if source_id:
            offers_by_source.setdefault(source_id, []).append(offer)

    for source in config.get("sources", []):
        source_offers = offers_by_source.get(source.get("id", ""), [])
        canonical_offers = [offer for offer in source_offers if not duplicate_map.get(offer.get("id", ""), {}).get("isDuplicate")]
        apply_count = sum(1 for offer in canonical_offers if str(offer.get("fit_recommendation", "")) == "apply")
        maybe_count = sum(1 for offer in canonical_offers if str(offer.get("fit_recommendation", "")) == "maybe")
        active_count = sum(1 for offer in canonical_offers if str(offer.get("status", "")) != "archived")
        ready_count = sum(1 for offer in canonical_offers if effective_offer_status(offer) == "shortlisted")
        latest_seen = max(
            (str(offer.get("last_seen_at") or offer.get("updated_at") or "") for offer in source_offers if offer),
            default="",
        )
        avg_score = round(
            sum(int(offer.get("fit_score_final", 0) or 0) for offer in canonical_offers) / len(canonical_offers)
        ) if canonical_offers else 0
        canonical_count = len(canonical_offers)
        apply_ratio = (apply_count / canonical_count) if canonical_count else 0
        active_ratio = (active_count / canonical_count) if canonical_count else 0
        ready_ratio = (ready_count / canonical_count) if canonical_count else 0
        freshness_bonus = 8 if latest_seen and latest_seen[:10] >= (datetime.now(timezone.utc) - timedelta(days=14)).date().isoformat() else 0
        quality_score = min(
            100,
            round(
                avg_score * 0.45
                + apply_ratio * 28
                + active_ratio * 12
                + ready_ratio * 10
                + freshness_bonus
            ),
        )
        metrics.append(
            {
                "id": source.get("id", ""),
                "enabled": bool(source.get("enabled")),
                "company": source.get("company_name", ""),
                "provider": source.get("provider", ""),
                "notes": source.get("notes", ""),
                "boardToken": source.get("board_token", ""),
                "baseUrl": source.get("base_url", ""),
                "autoPrepareMinScore": int(source.get("auto_prepare_min_score", 0) or 0),
                "counts": {
                    "raw": len(source_offers),
                    "canonical": canonical_count,
                    "duplicates": max(0, len(source_offers) - canonical_count),
                    "apply": apply_count,
                    "maybe": maybe_count,
                    "active": active_count,
                    "ready": ready_count,
                },
                "averageScore": avg_score,
                "qualityScore": quality_score,
                "latestSeenAt": latest_seen,
            }
        )
    return sorted(metrics, key=lambda item: (item["enabled"], item["qualityScore"], item["averageScore"]), reverse=True)


def auto_shortlist_score(offer: dict[str, Any], source_quality_score: int = 0) -> int:
    review_penalty = 10 if offer.get("reviewNeeded") else 0
    remote_bonus = 8 if offer.get("remoteProfile", {}).get("eligible") else -20
    source_bonus = round(source_quality_score * 0.12)
    evidence = offer.get("evidenceQuality", {})
    direct_bonus = min(12, int(evidence.get("direct", 0)) * 3)
    unsupported_penalty = min(12, int(evidence.get("unsupported", 0)) * 2)
    return max(
        0,
        min(
            100,
            int(offer.get("scores", {}).get("final", 0))
            + source_bonus
            + direct_bonus
            + remote_bonus
            - review_penalty
            - unsupported_penalty,
        ),
    )


def should_auto_shortlist(offer: dict[str, Any], source_quality_score: int = 0) -> bool:
    if offer.get("isDuplicate"):
        return False
    if offer.get("status") not in {"discovered", "screened", "scored", "shortlisted"}:
        return False
    if offer.get("recommendation") != "apply":
        return False
    if not offer.get("remoteProfile", {}).get("eligible"):
        return False
    if offer.get("remoteProfile", {}).get("scope") == "explicit_unknown_scope":
        return False
    if int(offer.get("subscores", {}).get("seniority_alignment", 0)) <= 2:
        return False
    if int(offer.get("scores", {}).get("ats", 0)) < 84:
        return False
    if int(offer.get("scores", {}).get("human", 0)) < 80:
        return False
    if int(offer.get("scores", {}).get("final", 0)) < 88:
        return False
    return auto_shortlist_score(offer, source_quality_score) >= 90


def build_offer_command(script_name: str, *parts: str) -> str:
    return " ".join(["python", f"scripts/{script_name}", *parts]).strip()


def core_asset_state(asset_state: dict[str, bool] | None = None) -> bool:
    asset_state = asset_state or {}
    return bool(asset_state.get("fit_report"))


def effective_offer_status(offer: dict[str, Any], asset_state: dict[str, bool] | None = None) -> str:
    status = str(offer.get("status", "discovered"))
    if status in {"applied", "follow_up_due", "recruiter_contact", "interviewing", "rejected", "archived"}:
        return status
    return status


def next_action_for_offer(offer: dict[str, Any], asset_state: dict[str, bool] | None = None) -> dict[str, Any]:
    status = effective_offer_status(offer, asset_state)
    recommendation = str(offer.get("fit_recommendation", "unscored"))
    score = int(offer.get("fit_score_final", 0) or 0)
    job_id = offer.get("id", "")
    follow_up_due = follow_up_due_timestamp(offer)
    follow_up_overdue = bool(follow_up_due and follow_up_due <= datetime.now(timezone.utc))

    action = {
        "kind": "monitor",
        "label": "Monitor offer",
        "reason": "Tracked in the repository but not yet prioritized.",
        "command": build_offer_command("score_job.py", "--job-id", job_id) if job_id else "",
        "priority": max(10, score),
    }

    if status in {"discovered", "screened", "scored"}:
        if recommendation == "apply" and score >= 75:
            action = {
                "kind": "shortlist_offer",
                "label": "Shortlist offer",
                "reason": "High-fit discovered offer worth keeping in the active search queue.",
                "command": build_offer_command("update_status.py", "--job-id", job_id, "--status", "shortlisted", "--note", '"Shortlisted for manual review"'),
                "priority": 300 + score,
            }
        elif recommendation == "maybe":
            action = {
                "kind": "manual_review",
                "label": "Review offer",
                "reason": "Borderline fit. Quick human review can decide whether the offer belongs in the shortlist.",
                "command": build_offer_command("score_job.py", "--job-id", job_id),
                "priority": 180 + score,
            }
        else:
            action = {
                "kind": "archive_or_ignore",
                "label": "Skip or archive",
                "reason": "Current fit looks weak relative to the target profile.",
                "command": build_offer_command("update_status.py", "--job-id", job_id, "--status", "rejected"),
                "priority": 40 + score,
            }
    elif status == "shortlisted":
        action = {
            "kind": "review_offer",
            "label": "Inspect source offer",
            "reason": "This offer is shortlisted and should be reviewed on the live page before any application decision.",
            "command": build_offer_command("refresh_application_page.py", "--job-id", job_id, "--browser", "auto"),
            "priority": 360 + score,
        }
    elif status in {"applied", "recruiter_contact"}:
        if follow_up_overdue:
            action = {
                "kind": "send_follow_up",
                "label": "Send follow-up",
                "reason": "The application has been pending long enough to justify a recruiter follow-up.",
                "command": build_offer_command("update_status.py", "--job-id", job_id, "--status", "follow_up_due", "--note", '"Follow-up now due"'),
                "priority": 320 + score,
            }
        else:
            due_label = follow_up_due.date().isoformat() if follow_up_due else "the next few days"
            action = {
                "kind": "watch_for_reply",
                "label": "Track response",
                "reason": f"Application is out. If there is no reply, the next follow-up window starts around {due_label}.",
                "command": build_offer_command("update_status.py", "--job-id", job_id, "--status", "follow_up_due"),
                "priority": 160 + score,
            }
    elif status == "follow_up_due":
        action = {
            "kind": "send_follow_up",
            "label": "Send follow-up",
            "reason": "A recruiter follow-up is due for this active application.",
            "command": build_offer_command("update_status.py", "--job-id", job_id, "--status", "recruiter_contact", "--note", '"Follow-up sent"'),
            "priority": 320 + score,
        }
    elif status == "interviewing":
        action = {
            "kind": "interview_prep",
            "label": "Prepare interviews",
            "reason": "The process is active and needs interview preparation rather than more tailoring.",
            "command": "",
            "priority": 360 + score,
        }

    return action


def build_dashboard_payload() -> dict[str, Any]:
    profile = load_profile()
    offers = load_all_offers()
    duplicate_map = compute_duplicate_relationships(offers)
    source_config = load_job_sources_config()
    sources = source_metrics(source_config, offers, duplicate_map)
    canonical_offers = [offer for offer in offers if not duplicate_map.get(offer.get("id", ""), {}).get("isDuplicate")]
    active_statuses = {
        "discovered",
        "screened",
        "scored",
        "shortlisted",
        "applied",
        "follow_up_due",
        "recruiter_contact",
        "interviewing",
    }

    def average(key: str) -> int:
        return round(sum(offer.get(key, 0) for offer in canonical_offers) / len(canonical_offers)) if canonical_offers else 0

    top_offers = sorted(canonical_offers, key=lambda item: item.get("fit_score_final", 0), reverse=True)[:3]
    execution_queue = []
    for offer in canonical_offers:
        job_dir = JOBS_DIR / offer["id"]
        paths = ensure_job_layout(job_dir)
        asset_state = {
            "fit_report": paths["fit_report"].exists(),
        }
        effective_status = effective_offer_status(offer, asset_state)
        if effective_status not in active_statuses:
            continue
        execution_queue.append(
            {
                "id": offer.get("id", ""),
                "company": offer.get("company_name", "Unknown company"),
                "role": offer.get("job_title", "Untitled role"),
                "status": effective_status,
                "score": offer.get("fit_score_final", 0),
                "action": next_action_for_offer(offer, asset_state),
            }
        )
    execution_queue = sorted(execution_queue, key=lambda item: item["action"].get("priority", 0), reverse=True)[:6]
    latest_discovered = sorted(
        canonical_offers,
        key=lambda item: item.get("last_seen_at") or item.get("updated_at") or item.get("source_date") or "",
        reverse=True,
    )[:5]
    preferred_roles = profile.get("preferences", {}).get("preferred_role_families", [])
    default_role = preferred_roles[0] if preferred_roles else "software_engineer"
    focus_offer = top_offers[0] if top_offers else {}

    canonical_statuses = []
    for offer in canonical_offers:
        job_dir = JOBS_DIR / offer["id"]
        paths = ensure_job_layout(job_dir)
        asset_state = {
            "fit_report": paths["fit_report"].exists(),
        }
        canonical_statuses.append(effective_offer_status(offer, asset_state))

    pipeline_counts = {
        "Discovered": sum(1 for status in canonical_statuses if status == "discovered"),
        "Scored": sum(1 for status in canonical_statuses if status == "scored"),
        "Shortlisted": sum(1 for status in canonical_statuses if status == "shortlisted"),
        "Applied": sum(1 for status in canonical_statuses if status in {"applied", "follow_up_due", "recruiter_contact"}),
        "Interviewing": sum(1 for status in canonical_statuses if status == "interviewing"),
    }
    shortlisted_count = sum(1 for status in canonical_statuses if status == "shortlisted")

    assets = []
    for offer in top_offers:
        job_dir = JOBS_DIR / offer["id"]
        paths = ensure_job_layout(job_dir)
        asset_targets = [
            ("Fit report", paths["fit_report"]),
            ("Research note", paths["research"]),
            ("Decision log", paths["decision"]),
        ]
        for asset_name, asset_path in asset_targets:
            exists = asset_path.exists()
            assets.append(
                {
                    "name": f"{offer.get('company_name', 'Offer')} {asset_name}",
                    "detail": offer.get("job_title", ""),
                    "status": "done" if exists else "pending",
                    "label": "Ready" if exists else "Draft",
                }
            )

    if not assets:
        assets = [
            {
                "name": "No generated assets yet",
                "detail": "Ingest an offer and score it to unlock the review workflow.",
                "status": "pending",
                "label": "Empty",
            }
        ]

    decisions = []
    for offer in top_offers:
        role_family_label = role_family_name(offer.get("normalized_role_family", "software_engineer"))
        decisions.append(
            {
                "title": f"{offer.get('company_name', 'Offer')} - {offer.get('fit_recommendation', 'unscored').title()}",
                "meta": f"Final score {offer.get('fit_score_final', 0)} / role family {role_family_label}",
                "body": offer.get("fit_summary")
                or (
                    "Strongest signals: " + ", ".join(offer.get("strengths", [])[:2])
                    if offer.get("strengths")
                    else "Offer has not been fully scored yet."
                ),
            }
        )

    if not decisions:
        decisions = [
            {
                "title": "Repository ready for first real offer",
                "meta": "No scored offers yet",
                "body": "Ingesting the first offer should create the canonical folder, score report, and dashboard activity.",
            }
        ]

    return {
        "hero": {
            "role": focus_offer.get("job_title") or role_family_display(default_role, profile),
            "mode": (focus_offer.get("company_stage") or "Local-only").replace("_", " ").title(),
            "meta": (
                f"{len([offer for offer in canonical_offers if offer.get('status') in active_statuses])} active offers, "
                f"{shortlisted_count} shortlisted, {pipeline_counts['Applied']} in application follow-up."
            ),
            "progress": min(100, max(8, average("fit_score_final"))),
        },
        "scores": {
            "ats": average("fit_score_ats"),
            "human": average("fit_score_human"),
            "strategic": average("fit_score_strategic"),
            "final": average("fit_score_final"),
        },
        "pipeline": [
            {"name": "Discovered", "count": pipeline_counts["Discovered"], "note": "Raw leads needing normalization and first-pass scoring."},
            {"name": "Scored", "count": pipeline_counts["Scored"], "note": "Offers parsed and scored, waiting for keep/skip review."},
            {"name": "Shortlisted", "count": pipeline_counts["Shortlisted"], "note": "Promising offers kept in the active queue for closer inspection."},
            {"name": "Applied", "count": pipeline_counts["Applied"], "note": "Submitted applications waiting for recruiter movement."},
            {"name": "Interviewing", "count": pipeline_counts["Interviewing"], "note": "Processes with active next steps and prep needs."},
        ],
        "topMatches": [
            {
                "id": offer.get("id", ""),
                "company": offer.get("company_name", "Unknown company"),
                "role": offer.get("job_title", "Untitled role"),
                "score": offer.get("fit_score_final", 0),
                "tags": offer.get("keywords_required", [])[:4]
                or [offer.get("normalized_role_family", "unclassified").replace("_", " ").title()],
            }
            for offer in top_offers
        ]
        or [
            {
                "company": "No offers yet",
                "role": "Ingest a job to populate this dashboard",
                "score": 0,
                "tags": ["jobs/", "offer.yaml", "score_job.py"],
            }
        ],
        "assets": assets[:3],
        "decisions": decisions[:3],
        "discovery": [
            {
                "id": offer.get("id", ""),
                "company": offer.get("company_name", "Unknown company"),
                "role": offer.get("job_title", "Untitled role"),
                "status": offer.get("status", "discovered"),
                "provider": offer.get("source_provider", offer.get("source", "manual")),
                "score": offer.get("fit_score_final", 0),
            }
            for offer in latest_discovered
        ],
        "executionQueue": execution_queue,
        "topSources": [
            {
                "title": source["company"],
                "meta": f"{str(source['provider']).replace('_', ' ').title()} | quality {source['qualityScore']}",
                "body": f"{source['counts']['apply']} apply-grade canonical offer(s), average score {source['averageScore']}, {source['counts']['active']} active.",
            }
            for source in sources[:3]
        ],
        "milestones": [
            "Canonical profile data now lives under profile/ as YAML.",
            "Offer ingestion and scoring are available through repository scripts.",
            "Per-offer detail views now focus on fit, source data, and review actions.",
            "Discovery and shortlist review are the primary operational workflows.",
            "Decision logging should explain why each offer was applied to or skipped.",
        ],
        "readyCount": 0,
        "shortlistedCount": shortlisted_count,
        "duplicateCount": sum(1 for item in duplicate_map.values() if item.get("isDuplicate")),
    }


def build_dashboard_store() -> dict[str, Any]:
    profile = load_profile()
    offers = load_all_offers()
    duplicate_map = compute_duplicate_relationships(offers)
    source_config = load_job_sources_config()
    overview = build_dashboard_payload()
    constraints = profile.get("constraints", {}).get("location_constraints", {})
    sources = source_metrics(source_config, offers, duplicate_map)
    source_quality_by_id = {source["id"]: int(source.get("qualityScore", 0) or 0) for source in sources}

    serialized_offers = []
    for offer in sorted(offers, key=lambda item: item.get("fit_score_final", 0), reverse=True):
        job_dir = JOBS_DIR / offer["id"]
        paths = ensure_job_layout(job_dir)
        asset_paths = {
            "fit_report": paths["fit_report"],
            "raw": paths["raw"],
            "research": paths["research"],
            "decision": paths["decision"],
        }
        asset_state = {name: path.exists() for name, path in asset_paths.items()}
        effective_status = effective_offer_status(offer, asset_state)
        core_pack_ready = core_asset_state(asset_state)
        next_action = next_action_for_offer(offer, asset_state)
        latest_status_at = latest_status_timestamp(offer)
        follow_up_due_at = follow_up_due_timestamp(offer)
        dedupe = duplicate_map.get(offer.get("id", ""), {})
        remote_profile = offer.get("remote_profile") or normalize_remote_profile(
            constraints,
            offer.get("remote_policy", ""),
            offer.get("location", ""),
            offer.get("job_title", ""),
            offer.get("job_description_clean", ""),
        )
        serialized_offers.append(
            {
                "id": offer.get("id", ""),
                "company": offer.get("company_name", ""),
                "role": offer.get("job_title", ""),
                "roleFamily": offer.get("normalized_role_family", ""),
                "status": effective_status,
                "rawStatus": offer.get("status", ""),
                "location": offer.get("location", ""),
                "remotePolicy": offer.get("remote_policy", ""),
                "remoteProfile": remote_profile,
                "companyStage": offer.get("company_stage", ""),
                "source": offer.get("source", ""),
                "sourceProvider": offer.get("source_provider", ""),
                "discoverySource": offer.get("discovery_source", ""),
                "sourceQualityScore": source_quality_by_id.get(str(offer.get("discovery_source", "")), 0),
                "recommendation": offer.get("fit_recommendation", "unscored"),
                "sourceUrl": offer.get("source_url", ""),
                "applicationUrl": offer.get("application_url", ""),
                "applicationPlatform": offer.get("application_platform", ""),
                "applicationQuestions": offer.get("application_questions", []),
                "pageSignals": offer.get("page_signals", {}),
                "reviewNeeded": bool(offer.get("page_signals", {}).get("review_required")),
                "reviewReasons": offer.get("page_signals", {}).get("review_reasons", []),
                "packReady": False,
                "corePackReady": core_pack_ready,
                "nextAction": next_action,
                "dedupeGroup": dedupe.get("groupKey", ""),
                "canonicalOfferId": dedupe.get("canonicalId", offer.get("id", "")),
                "isDuplicate": bool(dedupe.get("isDuplicate")),
                "duplicateCount": int(dedupe.get("duplicateCount", 0) or 0),
                "duplicateOfferIds": dedupe.get("groupIds", []),
                "latestStatusAt": latest_status_at.isoformat() if latest_status_at else "",
                "statusAgeDays": age_in_days(latest_status_at),
                "followUpDueAt": follow_up_due_at.isoformat() if follow_up_due_at else "",
                "followUpOverdue": bool(follow_up_due_at and follow_up_due_at <= datetime.now(timezone.utc)),
                "scores": {
                    "ats": offer.get("fit_score_ats", 0),
                    "human": offer.get("fit_score_human", 0),
                    "strategic": offer.get("fit_score_strategic", 0),
                    "final": offer.get("fit_score_final", 0),
                },
                "keywordsRequired": offer.get("keywords_required", []),
                "keywordsPreferred": offer.get("keywords_preferred", []),
                "strengths": offer.get("strengths", []),
                "risks": offer.get("risks", []),
                "summary": offer.get("fit_summary", ""),
                "seniority": offer.get("seniority_estimate", ""),
                "evidenceQuality": offer.get("evidence_quality", {}),
                "subscores": offer.get("subscores", {}),
                "description": offer.get("job_description_clean", ""),
                "postedAt": offer.get("posted_at", ""),
                "lastSeenAt": offer.get("last_seen_at", ""),
                "paths": {
                    name: str(path.relative_to(REPO_ROOT)).replace("\\", "/")
                    for name, path in asset_paths.items()
                },
                "assets": {name: path.exists() for name, path in asset_paths.items()},
                "assetPreview": {
                    "fit_report": artifact_preview(paths["fit_report"]),
                    "research": artifact_preview(paths["research"]),
                    "decision": artifact_preview(paths["decision"]),
                    "raw": artifact_preview(paths["raw"]),
                },
                "updatedAt": offer.get("updated_at", offer.get("source_date", "")),
            }
        )

    canonical_serialized_offers = [item for item in serialized_offers if not item["isDuplicate"]]
    for item in serialized_offers:
        shortlist_score = auto_shortlist_score(item, item.get("sourceQualityScore", 0))
        item["autoShortlistScore"] = shortlist_score
        item["autoShortlist"] = should_auto_shortlist(item, item.get("sourceQualityScore", 0))
    shortlist_candidates = sorted(
        [
            item
            for item in canonical_serialized_offers
            if item["status"] in {"discovered", "screened", "scored", "shortlisted"}
            and (item["autoShortlist"] or (item["recommendation"] in {"apply", "maybe"} and item["scores"]["final"] >= 75))
        ],
        key=lambda item: (
            0 if item["autoShortlist"] else 1,
            0 if item["status"] == "shortlisted" else 1,
            -(item["autoShortlistScore"] or 0),
            -(item["scores"]["final"] or 0),
            item["company"],
            item["role"],
        ),
    )
    duplicate_groups = []
    seen_duplicate_groups: set[str] = set()
    for item in serialized_offers:
        group_key = item.get("dedupeGroup", "")
        if not group_key or group_key in seen_duplicate_groups:
            continue
        related = [offer for offer in serialized_offers if offer.get("dedupeGroup") == group_key]
        if len(related) <= 1:
            continue
        seen_duplicate_groups.add(group_key)
        canonical = next((offer for offer in related if offer["id"] == item.get("canonicalOfferId")), related[0])
        duplicate_groups.append(
            {
                "groupKey": group_key,
                "canonicalOfferId": canonical["id"],
                "company": canonical["company"],
                "role": canonical["role"],
                "roleFamily": canonical["roleFamily"],
                "canonical": canonical,
                "offers": sorted(
                    related,
                    key=lambda offer: (
                        0 if offer["id"] == canonical["id"] else 1,
                        -(offer["scores"]["final"] or 0),
                        offer["id"],
                    ),
                ),
                "duplicateCount": len(related) - 1,
            }
        )
    duplicate_groups.sort(key=lambda group: (-group["duplicateCount"], -(group["canonical"]["scores"]["final"] or 0), group["role"]))
    role_family_breakdown = Counter(item["roleFamily"] for item in canonical_serialized_offers if item["roleFamily"])
    status_breakdown = Counter(item["status"] for item in canonical_serialized_offers if item["status"])
    provider_breakdown = Counter(item["sourceProvider"] or item["source"] for item in canonical_serialized_offers if item["sourceProvider"] or item["source"])
    source_breakdown = Counter(item["discoverySource"] for item in canonical_serialized_offers if item["discoverySource"])
    focus_queue = sorted(
        [
            offer
            for offer in canonical_serialized_offers
            if offer["status"] in {
                "discovered",
                "screened",
                "scored",
                "shortlisted",
                "applied",
                "follow_up_due",
                "recruiter_contact",
                "interviewing",
            }
        ],
        key=lambda offer: (
            0 if offer["autoShortlist"] else 1,
            -(offer["nextAction"].get("priority", 0)),
            0 if offer["status"] == "shortlisted" else 1,
            -(offer["autoShortlistScore"] or 0),
            -(offer["scores"]["final"] or 0),
            offer["company"],
            offer["role"],
        ),
    )

    return {
        "generatedAt": utc_now_iso(),
        "overview": overview,
        "profile": {
            "fullName": profile.get("basics", {}).get("full_name", ""),
            "email": profile.get("basics", {}).get("email", ""),
            "location": profile.get("basics", {}).get("location", ""),
            "remotePreference": profile.get("basics", {}).get("remote_preference", ""),
            "links": profile.get("basics", {}).get("links", {}),
            "headlines": profile.get("basics", {}).get("headline_defaults", {}),
            "preferredRoleFamilies": profile.get("preferences", {}).get("preferred_role_families", []),
            "preferredCompanyStages": profile.get("preferences", {}).get("preferred_company_stages", []),
            "preferredWorkModes": profile.get("preferences", {}).get("preferred_work_modes", []),
            "strategicBiases": profile.get("preferences", {}).get("strategic_biases", {}),
            "variantPriority": profile.get("preferences", {}).get("default_variant_priority", []),
            "skills": profile.get("skills", {}),
            "achievements": profile.get("achievements", {}).get("achievements", [])[:6],
            "experience": [
                {
                    "company": experience.get("company", ""),
                    "title": experience.get("titles", {}).get("actual", experience.get("title", "")),
                    "dates": (
                        f"{experience.get('dates', {}).get('start', '')} - {experience.get('dates', {}).get('end', '')}"
                    ).strip(" -"),
                    "themes": sorted(
                        {
                            theme
                            for bullet in experience.get("bullets", [])
                            for theme in bullet.get("supported_themes", [])
                        }
                    )[:6],
                }
                for experience in profile.get("experience", {}).get("experiences", [])
            ],
        },
        "sources": sources,
        "offers": serialized_offers,
        "counts": {
            "offers": len(serialized_offers),
            "canonicalOffers": len(canonical_serialized_offers),
            "duplicates": len([item for item in serialized_offers if item["isDuplicate"]]),
            "discovered": status_breakdown.get("discovered", 0),
            "shortlisted": status_breakdown.get("shortlisted", 0),
            "autoShortlisted": sum(1 for item in canonical_serialized_offers if item["autoShortlist"]),
            "readyToApply": 0,
            "applied": status_breakdown.get("applied", 0),
            "interviewing": status_breakdown.get("interviewing", 0),
        },
        "roleFamilyBreakdown": dict(role_family_breakdown),
        "statusBreakdown": dict(status_breakdown),
        "providerBreakdown": dict(provider_breakdown),
        "sourceBreakdown": dict(source_breakdown),
        "shortlistCandidates": shortlist_candidates[:24],
        "duplicateGroups": duplicate_groups,
        "focusQueue": focus_queue[:18],
        "executionQueue": sorted(
            [
                {
                    "id": offer["id"],
                    "company": offer["company"],
                    "role": offer["role"],
                    "status": offer["status"],
                    "score": offer["scores"]["final"],
                    "reviewNeeded": offer["reviewNeeded"],
                    "followUpDueAt": offer["followUpDueAt"],
                    "followUpOverdue": offer["followUpOverdue"],
                    "action": offer["nextAction"],
                }
                for offer in serialized_offers
                if not offer["isDuplicate"] and offer["status"] in {"discovered", "screened", "scored", "shortlisted", "applied", "follow_up_due", "recruiter_contact", "interviewing"}
            ],
            key=lambda item: item["action"].get("priority", 0),
            reverse=True,
        )[:10],
    }


def refresh_dashboard_data() -> dict[str, Any]:
    store = build_dashboard_store()
    write_json(DASHBOARD_OVERVIEW, store["overview"])
    write_json(DASHBOARD_STORE, store)
    return store
