# Job Search Repository Specification

## Purpose

This repository will evolve from a CV-generation workspace into a full personal job-search operating system.

The target system must help:

- ingest and normalize job offers
- score each offer against the candidate profile
- decide whether to pursue the offer
- track offer status from discovery to rejection / interview / acceptance
- keep all generated material truthful, auditable, and reusable

The repository is intended to be both:

- a content system for profile facts and review notes
- an execution system for discovery, scoring, and follow-up workflows

## Product Vision

The repository should answer one question quickly:

`Given a job offer, is it worth pursuing, and how should it be tracked and reviewed?`

It should also make it easy to answer:

- Which offers are high-fit?
- Which companies or roles are worth prioritizing?
- What gaps exist between the offer and the current profile?
- Which applications are in progress, submitted, ghosted, rejected, or advancing?

## Core Principles

### Truthfulness

No generated fit report, review note, or offer record may invent:

- technologies
- dates
- metrics
- job scope
- achievements
- management scope
- AI expertise level

All output must be traceable to source profile data.

### Reusability

The system must separate:

- stable profile facts
- reusable editorial building blocks
- offer-specific adaptations

This avoids rewriting from scratch for each application.

### Auditability

Every generated artifact should be reproducible from:

- source profile data
- job offer data
- generation strategy
- prompt or template version

### ATS-First, Human-Strong

Generated outputs must be optimized for:

- ATS readability
- role-specific keywords
- strong recruiter readability

without degrading into keyword stuffing.

### Manual Override

The user must always be able to:

- override scores
- override application decisions
- edit generated text
- pin preferred CV variants
- mark specific companies as strategic or blocked

## Scope

### In Scope

- job offer ingestion from manual copy/paste, links, PDFs, or structured files
- normalization of offer metadata and extracted requirements
- fit scoring on a 0-100 scale
- role-family classification
- application tracking and pipeline state
- repository organization for offers, assets, history, and decisions
- optional job-search dashboards and reports

### Out of Scope For V1

- fully autonomous job board scraping at scale
- automatic one-click application submission to third-party platforms
- browser automation against anti-bot flows as a core dependency
- CRM-level outreach automation
- salary negotiation modeling

### Non-Goals

The repository is not intended to become:

- a public job board
- a multi-user ATS product
- a generic outreach CRM
- a replacement for human judgment on role desirability
- a system that optimizes keyword stuffing over truthful positioning

## MVP Definition

The first working version should solve one narrow workflow well:

1. ingest one offer manually
2. normalize it into a canonical record
3. compute fit scores
4. recommend `apply / maybe / skip`
5. save a fit report and optional research note
6. track application status over time

Everything else should remain secondary until this path works end to end.

## Acceptance Criteria For V1

V1 is successful only if the repository can:

- ingest a new offer into `jobs/<job_id>/`
- produce a truthful `fit_report.md`
- compute ATS, human, and strategic fit scores
- derive a final recommendation from those scores
- save a truthful `research.md` note when needed
- track the application state with history
- expose the current job pipeline through a private local dashboard

## Main User Journeys

### 1. Evaluate a New Offer

Input:

- URL, screenshot, PDF, or pasted job description

System should:

1. create a normalized offer record
2. classify role family
3. extract requirements, keywords, seniority, location, constraints
4. compute fit score
5. explain strengths, weaknesses, and risks
6. recommend `apply / maybe / skip`

Output:

- offer record
- fit report
- score explanation

### 2. Review and Shortlist an Offer

Input:

- one normalized offer record

System should:

1. refresh the source or application page when useful
2. preserve extracted application questions in `offer.yaml`
3. save supporting review artifacts:
   - fit report
   - research note
   - decision log
4. mark whether the offer should be shortlisted, skipped, or pursued

Output:

- updated offer record
- fit report
- optional research note
- decision log

### 3. Track Application State

System should track:

- discovered
- shortlisted
- tailored
- ready to apply
- applied
- recruiter reached out
- interview scheduled
- rejected
- withdrawn
- offer received
- accepted

Output:

- canonical status field
- state history
- notes and timestamps

### 4. Review Search Pipeline

System should provide:

- top scored active offers
- applications needing follow-up
- offers missing tailored assets
- companies with multiple openings
- role-family distribution

## Candidate Profile Model

The profile should become structured source data rather than only LaTeX text.

### Candidate Source of Truth

Recommended canonical files:

- `profile/basics.yaml`
- `profile/experience.yaml`
- `profile/education.yaml`
- `profile/skills.yaml`
- `profile/achievements.yaml`
- `profile/preferences.yaml`
- `profile/constraints.yaml`

### Examples of Candidate Data

`basics.yaml`

- full name
- email
- location
- remote preference
- links

`experience.yaml`

- company
- title
- normalized titles
- start/end dates
- location
- bullets
- supported technologies
- supported metrics
- supported themes

`skills.yaml`

- languages
- frameworks
- cloud/platform
- AI/tooling
- practices

`preferences.yaml`

- preferred role families
- preferred locations
- minimum compensation target
- preferred company stage
- blocked company types

`constraints.yaml`

- visa constraints if any
- remote/hybrid/on-site rules
- disallowed industries if any

## Evidence Model

Truthfulness should be enforced through explicit evidence links, not only through prompts.

### Evidence Units

Each reusable fact should be represented as an evidence-backed unit:

- technology evidence
- achievement evidence
- scope evidence
- leadership evidence
- AI/tooling evidence

### Evidence Levels

Every generated claim and every score component should classify support as:

- `direct`
- `adjacent`
- `weak`
- `unsupported`

### Suggested Structure

Each canonical experience bullet should allow metadata such as:

- `evidence_id`
- `supported_technologies`
- `supported_metrics`
- `supported_themes`
- `leadership_scope`
- `ai_relevance_level`

Example:

```yaml
- evidence_id: sony_ci_cd_001
  bullet: Built CI/CD and automated test infrastructure for Sony PlayStation emulators.
  supported_technologies:
    - Python
    - GitHub Actions
    - AWS
  supported_metrics:
    - 5000+ games
    - 50+ PlayStation Classics
  supported_themes:
    - ci_cd
    - developer_tooling
    - release_engineering
    - test_automation
  ai_relevance_level: none
```

### Evidence Requirements

- no generated bullet may include a technology without at least `adjacent` evidence
- no generated metric may exist without `direct` evidence
- no leadership claim may exceed supported scope
- AI wording must map to explicit evidence level

## Job Offer Domain Model

Each offer should be stored as a normalized record.

Recommended fields:

- `id`
- `company_name`
- `job_title`
- `normalized_role_family`
- `source`
- `source_url`
- `source_date`
- `location`
- `remote_policy`
- `employment_type`
- `salary_range`
- `job_description_raw`
- `job_description_clean`
- `keywords_required`
- `keywords_preferred`
- `responsibilities`
- `must_haves`
- `nice_to_haves`
- `seniority_estimate`
- `fit_score`
- `fit_recommendation`
- `fit_summary`
- `risks`
- `notes`
- `status`
- `status_history`

Recommended file path:

- `jobs/<job_id>/offer.yaml`

Supporting files inside the same folder:

- `raw.md`
- `research.md`
- `fit_report.md`
- `decision.md`

## Role Families

The first supported role families should be:

- software_engineer
- backend_engineer
- founding_engineer
- platform_devops_engineer

Later extensions:

- product_engineer
- full_stack_engineer
- developer_experience_engineer
- solutions_engineer

## Repository Structure Target

```text
docs/
  JOB_SEARCH_REPOSITORY_SPEC.md

profile/
  basics.yaml
  experience.yaml
  education.yaml
  skills.yaml
  achievements.yaml
  preferences.yaml
  constraints.yaml

src/
  cv.tex
  muratcan_cv.cls
  photo.jpg

variants/
  software_engineer.tex
  founding_engineer.tex
  platform_devops_engineer.tex
  strategy.md

jobs/
  <job_id>/
    offer.yaml
    raw.md
    research.md
    fit_report.md
    decision.md

data/
  jobs_index.yaml
  companies.yaml
  prompts.yaml
  taxonomy.yaml

scripts/
  ingest_job.py
  score_job.py
  discover_jobs.py
  refresh_application_page.py
  update_status.py
  pdf_to_png.py
  requirements.txt

output/
  main/
  variants/
  jobs/

templates/
  job_offer.yaml
  fit_report.md
  research.md
  decision.md

build/
  ...
```

## Scoring Model

The repository should compute multiple scores from `0` to `100`.

### Score Types

- `fit_score_ats`: keyword and structural relevance for ATS screening
- `fit_score_human`: recruiter and hiring-manager narrative fit
- `fit_score_strategic`: desirability for the candidate
- `fit_score_final`: weighted recommendation score

### Score Meaning

- `90-100`: very high fit, strong apply priority
- `75-89`: good fit, apply
- `60-74`: possible fit, apply selectively
- `40-59`: weak fit, only apply if strategic
- `0-39`: poor fit, skip

### Score Composition

Recommended composition:

```text
fit_score_final =
  0.45 * fit_score_ats +
  0.40 * fit_score_human +
  0.15 * fit_score_strategic
```

This weighting should remain explicit and inspectable.

### Score Dimensions

Recommended weighted dimensions:

- role family match: `20`
- core skills match: `20`
- experience relevance: `20`
- seniority alignment: `10`
- industry / domain relevance: `5`
- delivery / achievement relevance: `10`
- logistics fit: `10`
- strategic preference fit: `5`

Total: `100`

### Role Family Match

Measures whether the offer matches:

- software
- backend
- founding
- platform/devops

This should be driven by title, description, and dominant responsibility clusters.

### Core Skills Match

Measures overlap between:

- required technologies
- demonstrated candidate technologies

This must distinguish:

- explicit evidence
- adjacent evidence
- unsupported claims

### Experience Relevance

Measures whether the existing experience bullets support the work type requested.

Examples:

- backend product features
- developer tooling
- CI/CD ownership
- 0-to-1 startup execution
- cloud systems

### Seniority Alignment

Measures whether the offer appears:

- junior
- mid
- senior
- staff/principal

and whether the profile supports that level.

### Logistics Fit

Measures:

- remote compatibility
- location compatibility
- language compatibility
- authorization constraints if any

### Strategic Preference Fit

Measures candidate preferences:

- startup vs large company
- preferred domains
- blocked or favored employers

## Score Output Requirements

Every score must include:

- ATS score
- human score
- strategic score
- final score
- sub-scores
- apply recommendation
- 3 strongest fit reasons
- 3 largest mismatch reasons
- confidence level
- evidence quality summary

Example:

```yaml
fit_score_ats: 86
fit_score_human: 79
fit_score_strategic: 74
fit_score_final: 81
fit_recommendation: apply
confidence: high
subscores:
  role_family_match: 18
  core_skills_match: 16
  experience_relevance: 17
  seniority_alignment: 8
  domain_relevance: 4
  achievement_relevance: 9
  logistics_fit: 8
  strategic_fit: 2
strengths:
  - Strong evidence in Go, TypeScript, React, Python, AWS, and GCP.
  - Direct startup and product-shipping experience at Jam.gg.
  - Quantified scale and delivery outcomes.
risks:
  - Limited explicit evidence in technology X.
  - Title may imply broader platform than pure backend scope.
  - Offer asks for staff-level organizational influence.
evidence_quality:
  direct: 8
  adjacent: 4
  weak: 1
  unsupported: 0
```

## Decision Log Specification

The repository should store decision rationale, not only scores.

Each offer should include:

- `decision`
- `decision_reason`
- `decision_confidence`
- `customization_notes`
- `post_application_notes`

Recommended companion file:

- `jobs/<job_id>/decision.md`

The decision log should answer:

- Why was this offer pursued or skipped?
- What was customized in the CV?
- What concerns remained at submission time?
- What was learned after the process progressed or failed?

## CV Generation Specification

### Inputs

- canonical profile data
- target role family
- normalized offer record
- existing base variant

### Output Types

- generic role-family variant
- offer-specific tailored variant

### Rules

- preserve truthfulness
- preserve one-page limit by default
- optimize wording for role family and offer keywords
- keep strongest metrics
- do not overclaim AI expertise
- do not introduce unsupported technologies

### CV Selection Logic

Base mapping:

- `software_engineer` -> `variants/software_engineer.tex`
- `backend_engineer` -> `variants/software_engineer.tex`
- `founding_engineer` -> `variants/founding_engineer.tex`
- `platform_devops_engineer` -> `variants/platform_devops_engineer.tex`

### Tailoring Logic

Tailoring should change:

- headline / subtitle
- summary
- skills ordering
- 2 to 5 bullets in the most relevant roles
- minor title normalization where justified

Tailoring should not change:

- factual dates
- actual achievements
- actual technologies used

## Asset Priority

Generated assets should be prioritized to avoid overproduction.

### Core Assets

- fit report
- research note
- decision log

### Optional Assets

- source HTML snapshot
- company research summary
- interview prep notes

### Asset Generation Rule

V1 should generate core review artifacts by default.
Optional assets should be created on demand or only for high-priority opportunities.

## Review Notes

The repository should favor compact, auditable notes over generated application copy.

### Review Note Types

- fit report
- research note
- decision log
- application-question snapshot in `offer.yaml`

### Review Requirements

- truthful
- concise
- role-targeted
- reusable
- grounded in the same offer and profile source data

## Offer Research Specification

Per company or offer, a lightweight research note may include:

- company summary
- product/domain
- funding/stage
- size estimate
- technical angle if relevant
- potential resume hooks
- risks or red flags

This should remain lightweight and practical, not a full analyst report.

## Dashboard Specification

The repository should include a private dashboard usable only by the repository owner in local mode.

### Dashboard Goals

- show current pipeline health
- show top-fit offers
- show applications requiring action
- show fit score composition
- show why an offer is attractive or risky

### Privacy Requirement

The first dashboard implementation should be:

- local-only
- served on `127.0.0.1`
- not publicly deployed

This is sufficient for V1. Authentication is only needed if remote access is introduced later.

### Dashboard Views

Recommended initial views:

- overview
- offers list
- offer detail
- application pipeline
- generated assets status

### Dashboard Data Sources

The dashboard should read from repository files, not a separate opaque state store.

Primary sources:

- `data/jobs_index.yaml`
- `jobs/<job_id>/offer.yaml`
- `jobs/<job_id>/fit_report.md`
- `jobs/<job_id>/notes/research.md`

### Dashboard Non-Goals For V1

- collaborative editing
- public sharing
- heavy analytics
- database-backed multi-user state

## Status Tracking

Canonical statuses:

- `discovered`
- `screened`
- `scored`
- `shortlisted`
- `applied`
- `follow_up_due`
- `recruiter_contact`
- `interviewing`
- `rejected`
- `withdrawn`
- `offer`
- `accepted`

Each status change should record:

- date
- previous status
- new status
- reason or note

## Index Files

Recommended repository-level indexes:

`data/jobs_index.yaml`

- lightweight index of all offers
- path to full offer folder
- current status
- score
- title
- company

`data/companies.yaml`

- company aliases
- blocked/favored flags
- notes

`data/taxonomy.yaml`

- role families
- standard keywords
- scoring mappings

## Suggested Automation / Script Surface

### `scripts/ingest_job.py`

Responsibilities:

- create a new `jobs/<job_id>/`
- store raw source text
- extract structured offer fields

### `scripts/score_job.py`

Responsibilities:

- read profile + offer
- compute score and sub-scores
- write `fit_report.md` and offer score fields

### `scripts/discover_jobs.py`

Responsibilities:

- fetch jobs from configured public sources
- keep only relevant remote offers
- ingest normalized offer records
- score discovered jobs immediately

### `scripts/generate_application_assets.py`

Responsibilities:

- generate outreach messages
- generate answers
- generate company/role-specific notes

### `scripts/update_status.py`

Responsibilities:

- mutate status safely
- append history entry

### `scripts/build_resume.py`

Responsibilities:

- compile main/variant/offer-specific CVs
- centralize existing build logic

### `scripts/serve_dashboard.py`

Responsibilities:

- serve the dashboard locally on `127.0.0.1`
- expose static dashboard assets
- avoid external dependencies for V1

## Prompting and Generation Rules

The repository should store generation rules centrally, not only in chat history.

Recommended:

- `data/prompts.yaml`

Prompt families:

- offer parsing
- scoring
- CV tailoring
- outreach message generation
- application answer generation

Each prompt family should define:

- purpose
- inputs
- required guardrails
- output schema

## Quality Bar

Generated outputs should be rejected if they:

- invent facts
- exceed one page when one page is required
- use unsupported keywords
- overstate AI experience
- fail ATS text extraction
- produce vague or generic summaries

## Non-Functional Requirements

### Reproducibility

- all generated artifacts should be derivable from tracked source files
- prompt versions should be explicit
- data files should be deterministic and diff-friendly

### Data Format Discipline

V1 should standardize on:

- `YAML` for canonical structured data
- `Markdown` for human-readable reports and notes
- `LaTeX` for final CV rendering

### Local-First Operation

The repository should remain usable without a hosted backend.

### Testability

At minimum, V1 scripts should support:

- schema validation
- dry-run mode
- deterministic output where possible

## Observability

The system should record generation metadata where useful:

- timestamp
- source offer ID
- source variant
- prompt version
- generator version

This can live in sidecar files such as:

- `jobs/<job_id>/generation_meta.yaml`

## Security and Privacy

This repository will contain sensitive personal and application data.

Requirements:

- avoid committing secrets
- avoid storing tokens in tracked files
- treat company notes and application URLs as sensitive
- consider keeping some outputs ignored locally if needed

## Phased Delivery Plan

### Phase 1: Repository Foundations

- define directory model
- define profile source files
- define offer schema
- define status taxonomy
- preserve the current scoring and tracking workflow

### Phase 2: Offer Ingestion and Scoring

- add `ingest_job.py`
- add `score_job.py`
- create first scoring rubric
- create first fit reports

### Phase 3: Review Workflow

- refresh shortlisted offers from the source page
- maintain research notes and decision logs
- improve dashboard review ergonomics

### Phase 4: Tracking and Reporting

- add indexes
- add search / summaries
- add stale follow-up reminders

### Phase 5: Workflow Polish

- improve prompt configs
- refine score explainability
- add dashboards or summary views

## Open Questions

These decisions still need confirmation:

- Should the canonical source of profile truth move fully from LaTeX into YAML/JSON?
- Should the repository keep only one canonical main CV, separate from offer discovery and tracking?
- Should offer ingestion support browser URLs directly inside the repo workflow?
- Should the status system live in YAML files only, or also in a lightweight local database?
- Should there be one global score, or separate scores for:
  - ATS fit
  - human fit
  - strategic desirability
- Should the system support multiple application languages later?
- Should the repository include saved company research beyond active offers?

## Recommended Immediate Next Steps

1. Create the canonical `profile/` source files.
2. Create a template schema for `jobs/<job_id>/offer.yaml`.
3. Create `data/jobs_index.yaml` and `data/taxonomy.yaml`.
4. Implement `scripts/ingest_job.py`.
5. Implement `scripts/score_job.py`.
6. Define the first stable scoring rubric with sample offers.
