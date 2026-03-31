.DEFAULT_GOAL := help

TEX                     := src/cv.tex
CLASS                   := src/muratcan_cv.cls
PHOTO                   := src/photo.jpg
PDF                     := output/main/CV_Alexandre_DO_O_ALMEIDA_2025.pdf
PNG                     := output/main/CV_Alexandre_DO_O_ALMEIDA_2025.png
SOFTWARE_TEX            := variants/software_engineer.tex
FOUNDING_TEX            := variants/founding_engineer.tex
PLATFORM_TEX            := variants/platform_devops_engineer.tex
SOFTWARE_PDF            := output/variants/Alexandre_DO_O_ALMEIDA_Resume_Software_Engineer.pdf
FOUNDING_PDF            := output/variants/Alexandre_DO_O_ALMEIDA_Resume_Founding_Engineer.pdf
PLATFORM_PDF            := output/variants/Alexandre_DO_O_ALMEIDA_Resume_Platform_DevOps_Engineer.pdf
VARIANT_PDFS            := $(SOFTWARE_PDF) $(FOUNDING_PDF) $(PLATFORM_PDF)
TECTONIC                ?= ./.tools/tectonic/tectonic.exe
PYTHON                  ?= python
REQUIREMENTS            := scripts/requirements.txt
PNG_SCRIPT              := scripts/pdf_to_png.py
BUILD_MAIN_DIR          := build/main
BUILD_VARIANTS_DIR      := build/variants

.PHONY: help all build cv pdf preview png variants resumes install \
        dashboard dashboard-data ingest-url ingest-file score score-all \
        discover codex-discover refresh-apply followups archive-blocked archive-skip clean distclean

help:
	@echo ""
	@echo "Classic commands"
	@echo "  make install                    Install Python dependencies"
	@echo "  make cv                         Build main CV PDF"
	@echo "  make preview                    Build main CV PDF + PNG"
	@echo "  make variants                   Build all targeted resume PDFs"
	@echo "  make build                      Build main CV, preview, and variants"
	@echo "  make dashboard                  Launch local dashboard"
	@echo "  make dashboard-data             Rebuild dashboard JSON data"
	@echo ""
	@echo "Job search commands"
	@echo "  make discover                   Discover jobs from configured sources"
	@echo "  make ingest-url JOB_URL=<url>   Ingest one offer from a URL"
	@echo "  make ingest-file COMPANY=... TITLE=... JOB_FILE=<path>"
	@echo "  make score JOB_ID=<id>          Score a single offer"
	@echo "  make score-all                  Rescore all offers"
	@echo "  make refresh-apply JOB_ID=<id>  Re-scan application page/questions"
	@echo "  make followups                  Promote stale applications to follow-up due"
	@echo "  make archive-blocked            Archive offers blocked by location constraints"
	@echo "  make archive-skip               Archive offers currently scored as skip"
	@echo ""
	@echo "Useful variables"
	@echo "  JOB_ID=<id> JOB_URL=<url> SOURCE_ID=<source> LIMIT=<n>"
	@echo "  MIN_SCORE=<n> BROWSER=auto DAYS=<n> DRY_RUN=1"
	@echo ""

all: build

build: preview variants

cv: pdf

pdf: $(PDF)

preview: $(PNG)

png: $(PNG)

resumes: variants

variants: $(VARIANT_PDFS)

$(PDF): $(TEX) $(CLASS) $(PHOTO)
	$(PYTHON) -c "from pathlib import Path; Path('$(BUILD_MAIN_DIR)').mkdir(parents=True, exist_ok=True); Path('output/main').mkdir(parents=True, exist_ok=True)"
	$(TECTONIC) --keep-logs --keep-intermediates -o $(BUILD_MAIN_DIR) $(TEX)
	$(PYTHON) -c "import shutil; shutil.copy2('$(BUILD_MAIN_DIR)/cv.pdf', '$(PDF)')"

$(PNG): $(PDF) $(PNG_SCRIPT)
	$(PYTHON) $(PNG_SCRIPT) --input $(PDF) --output $(PNG)

$(SOFTWARE_PDF): $(SOFTWARE_TEX) $(CLASS)
	$(PYTHON) -c "from pathlib import Path; Path('$(BUILD_VARIANTS_DIR)').mkdir(parents=True, exist_ok=True); Path('output/variants').mkdir(parents=True, exist_ok=True)"
	$(TECTONIC) --keep-logs --keep-intermediates -Z search-path=src -o $(BUILD_VARIANTS_DIR) $(SOFTWARE_TEX)
	$(PYTHON) -c "import shutil; shutil.copy2('$(BUILD_VARIANTS_DIR)/software_engineer.pdf', '$(SOFTWARE_PDF)')"

$(FOUNDING_PDF): $(FOUNDING_TEX) $(CLASS)
	$(PYTHON) -c "from pathlib import Path; Path('$(BUILD_VARIANTS_DIR)').mkdir(parents=True, exist_ok=True); Path('output/variants').mkdir(parents=True, exist_ok=True)"
	$(TECTONIC) --keep-logs --keep-intermediates -Z search-path=src -o $(BUILD_VARIANTS_DIR) $(FOUNDING_TEX)
	$(PYTHON) -c "import shutil; shutil.copy2('$(BUILD_VARIANTS_DIR)/founding_engineer.pdf', '$(FOUNDING_PDF)')"

$(PLATFORM_PDF): $(PLATFORM_TEX) $(CLASS)
	$(PYTHON) -c "from pathlib import Path; Path('$(BUILD_VARIANTS_DIR)').mkdir(parents=True, exist_ok=True); Path('output/variants').mkdir(parents=True, exist_ok=True)"
	$(TECTONIC) --keep-logs --keep-intermediates -Z search-path=src -o $(BUILD_VARIANTS_DIR) $(PLATFORM_TEX)
	$(PYTHON) -c "import shutil; shutil.copy2('$(BUILD_VARIANTS_DIR)/platform_devops_engineer.pdf', '$(PLATFORM_PDF)')"

install:
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -r $(REQUIREMENTS)

dashboard:
	$(PYTHON) scripts/serve_dashboard.py

dashboard-data:
	$(PYTHON) scripts/build_dashboard_data.py

ingest-url:
	$(PYTHON) -c "import os, sys; url = os.environ.get('JOB_URL', '').strip(); sys.exit('Usage: make ingest-url JOB_URL=<url>') if not url else None"
	$(PYTHON) scripts/ingest_job_url.py --url "$(JOB_URL)"

ingest-file:
	$(PYTHON) -c "import os, sys; company = os.environ.get('COMPANY', '').strip(); title = os.environ.get('TITLE', '').strip(); path = os.environ.get('JOB_FILE', '').strip(); sys.exit('Usage: make ingest-file COMPANY=<company> TITLE=<title> JOB_FILE=<path>') if not (company and title and path) else None"
	$(PYTHON) scripts/ingest_job.py --company "$(COMPANY)" --title "$(TITLE)" --raw-file "$(JOB_FILE)" $(if $(JOB_URL),--source-url "$(JOB_URL)",) $(if $(LOCATION),--location "$(LOCATION)",) $(if $(REMOTE_POLICY),--remote-policy "$(REMOTE_POLICY)",) $(if $(EMPLOYMENT_TYPE),--employment-type "$(EMPLOYMENT_TYPE)",) $(if $(COMPANY_STAGE),--company-stage "$(COMPANY_STAGE)",) $(if $(ROLE_FAMILY),--role-family "$(ROLE_FAMILY)",)

score:
	$(PYTHON) -c "import os, sys; job_id = os.environ.get('JOB_ID', '').strip(); sys.exit('Usage: make score JOB_ID=<job-id>') if not job_id else None"
	$(PYTHON) scripts/score_job.py --job-id $(JOB_ID)

score-all:
	$(PYTHON) scripts/score_job.py --all

discover:
	$(PYTHON) scripts/discover_jobs.py $(if $(SOURCE_ID),--source-id $(SOURCE_ID),) $(if $(LIMIT),--limit $(LIMIT),) $(if $(MIN_SCORE),--min-score $(MIN_SCORE),)

codex-discover:
	$(PYTHON) scripts/codex_discover_jobs.py

refresh-apply:
	$(PYTHON) -c "import os, sys; job_id = os.environ.get('JOB_ID', '').strip(); sys.exit('Usage: make refresh-apply JOB_ID=<job-id>') if not job_id else None"
	$(PYTHON) scripts/refresh_application_page.py --job-id $(JOB_ID) $(if $(BROWSER),--browser $(BROWSER),)

followups:
	$(PYTHON) scripts/mark_followups_due.py $(if $(DAYS),--days $(DAYS),) $(if $(DRY_RUN),--dry-run,)

archive-blocked:
	$(PYTHON) scripts/archive_blocked_jobs.py $(if $(DRY_RUN),--dry-run,)

archive-skip:
	$(PYTHON) scripts/archive_skip_jobs.py $(if $(DRY_RUN),--dry-run,)

clean:
	$(PYTHON) -c "import shutil; shutil.rmtree('build', ignore_errors=True)"

distclean: clean
	$(PYTHON) -c "import shutil; from pathlib import Path; [shutil.rmtree(path, ignore_errors=True) for path in ['output/main', 'output/variants']]; [Path(path).mkdir(parents=True, exist_ok=True) for path in ['output/main', 'output/variants']]"
