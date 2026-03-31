# Alexandre DO-O ALMEIDA CV

This repository contains the LaTeX sources for the main CV and three ATS-targeted resume variants.
It is now primarily a local-first job search repository focused on discovery, scoring, offer tracking, and a private dashboard.

## Structure

```text
docs/       product and repository specifications
dashboard/  private local-only job search dashboard
data/       canonical indexes, taxonomy, and prompt metadata
jobs/       one folder per ingested offer
profile/    canonical profile facts and evidence in YAML
src/        main CV source, shared class, shared assets
templates/  reusable templates for offer and application artifacts
variants/   targeted resume variants + editorial strategy notes
scripts/    helper scripts and Python requirements
output/     final PDFs and PNG preview ready to send
build/      temporary compilation artifacts
```

## Files To Keep

- `src/cv.tex`
- `src/muratcan_cv.cls`
- `src/photo.jpg`
- `variants/software_engineer.tex`
- `variants/founding_engineer.tex`
- `variants/platform_devops_engineer.tex`
- `variants/strategy.md`
- `profile/*.yaml`
- `data/*.yaml`
- `scripts/pdf_to_png.py`
- `scripts/ingest_job.py`
- `scripts/ingest_job_url.py`
- `scripts/score_job.py`
- `scripts/update_status.py`
- `scripts/mark_followups_due.py`
- `scripts/discover_jobs.py`
- `scripts/refresh_application_page.py`
- `scripts/codex_discover_jobs.py`
- `scripts/build_dashboard_data.py`
- `scripts/serve_dashboard.py`
- `scripts/requirements.txt`
- `Makefile`

## Build

```bash
make pdf       # build output/main/CV_Alexandre_DO_O_ALMEIDA_2025.pdf
make png       # build output/main/CV_Alexandre_DO_O_ALMEIDA_2025.png
make variants  # build the 3 HR-ready resume PDFs
make dashboard-data # refresh dashboard/data/overview.json from repository data
make dashboard # serve the private dashboard on http://127.0.0.1:4173/dashboard/
make followups DAYS=7 # mark stale applied jobs as follow_up_due
make discover SOURCE_ID=example LIMIT=25 # scan enabled sources and ingest relevant matches
make codex-discover # let Codex search the web for relevant public jobs and ingest them
make refresh-apply JOB_ID=example-corp-senior-backend-engineer BROWSER=auto # refetch the application page and detect form questions
make clean     # remove build artifacts
```

The Makefile expects a local Tectonic binary at `.tools/tectonic/tectonic.exe`.

## Job Search Workflow

```bash
python scripts/ingest_job.py --company "Example" --title "Senior Backend Engineer" --description "Go, Python, APIs, remote"
python scripts/score_job.py --all
python scripts/update_status.py --job-id example-senior-backend-engineer --status scored --note "Reviewed manually"
make dashboard
```

Single-command deterministic workflow:

```bash
python scripts/mark_followups_due.py --days 7
python scripts/discover_jobs.py
python scripts/codex_discover_jobs.py
```

## Automatic Discovery

Discovery sources are configured in [data/job_sources.yaml](/C:/Users/aleqs/Documents/GitHub/latex_cv/data/job_sources.yaml).
The first implementation supports:
- Greenhouse public boards
- Lever public boards
- Workable public boards
- Ashby hosted job boards
- Teamtailor feeds via `jobs.rss`

Each source can also narrow discovery using:
- `allow_title_terms`
- `deny_title_terms`
- `require_keywords`
- `detail_fetch_limit` for providers where full detail pages are expensive

Application-page refresh supports:
- static HTML extraction by default
- browser-assisted extraction for JS-driven apply flows via `python scripts/refresh_application_page.py --job-id <id> --browser auto`

If you want browser-assisted inspection, install dependencies and browsers:

```bash
pip install -r scripts/requirements.txt
python -m playwright install chromium
```

Typical flow:

```bash
python scripts/discover_jobs.py
python scripts/discover_jobs.py --limit 25
```

This will:
1. fetch public postings from enabled sources
2. keep only postings likely relevant to the target profile
3. ingest them into `jobs/`
4. score them immediately
5. leave the strongest matches ready for shortlist review in the dashboard

The dashboard now separates:
- `Overview` for the global pipeline
- `Discovery` for automatically found leads and provider/source coverage
- `Sources` for enabling feeds, running discovery per source, and inspecting source health
- `Offers` for all tracked offers
- `Ready` for shortlisted offers that are close to an apply decision
- `Applications` for submitted roles, follow-ups, and interview-stage tracking
- `Pipeline` for the operational queue and the next commands to run

When served through `python scripts/serve_dashboard.py`, the dashboard is also locally actionable:
- offer detail pages can rescore, refresh the apply page, or update status
- offer detail pages focus on fit reports, notes, and live source inspection
- shortlisted cards expose fit signals and direct review actions
- applications can be filtered and advanced directly through follow-up and interview statuses
- overview highlights enabled sources, collapsed duplicates, shortlisted offers, and follow-up pressure
- sources can be enabled or disabled without editing YAML manually
- the pipeline page can run batch discovery and follow-up promotion
- all actions stay bound to `127.0.0.1` and refresh the dashboard data automatically

The dashboard also collapses detected duplicate offers by default in the main queue surfaces so reposts and multi-location variants do not dominate the workflow.

The repository can also track post-application follow-up timing:
- mark an offer `applied` after manual submission
- run `python scripts/mark_followups_due.py --days 7`
- stale applications will surface as `follow_up_due` in the queue

Each ingested offer should converge toward a usable folder containing:
- `offer.yaml` with normalized metadata, apply URL, platform, and detected application questions
- `source/raw.md` and optionally `source/source.html`
- `artifacts/fit_report.md`
- `notes/research.md` and `notes/decision.md`

The dashboard offer detail page is designed to point back to those artifacts so you can review the offer, inspect the live source page, and decide whether to shortlist, apply, or reject.
