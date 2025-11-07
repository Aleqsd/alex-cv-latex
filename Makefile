# ==========================
#   CV Makefile (XeLaTeX)
# ==========================

TEX           := cv.tex
CLASS         := muratcan_cv.cls
PHOTO         := photo.jpg
PDF           := CV_Alexandre_DO_O_ALMEIDA_2025.pdf
PNG           := CV_Alexandre_DO_O_ALMEIDA_2025.png

LATEXMK       ?= latexmk
LATEXMK_OPTS  ?= -xelatex -interaction=nonstopmode -halt-on-error
PYTHON        ?= python3
REQUIREMENTS  ?= requirements.txt
JOBNAME       ?= $(basename $(PDF))

.PHONY: all pdf png clean distclean watch install check-env

# --- Main targets ---

all: pdf png

pdf: $(PDF)

$(PDF): $(TEX) $(CLASS) $(PHOTO)
	@echo "🧩 Checking environment..."
	@$(MAKE) check-env
	@echo "📄 Building PDF with XeLaTeX..."
	$(LATEXMK) $(LATEXMK_OPTS) -jobname=$(JOBNAME) $(TEX)

png: $(PNG)

$(PNG): $(PDF) pdf_to_png.py
	@echo "🖼️  Converting PDF to PNG..."
	$(PYTHON) pdf_to_png.py


# --- Environment checks ---

check-env:
	@if echo "$$(pwd)" | grep -q "^/mnt/c/"; then \
		echo "⚠️  You are building from /mnt/c/... (Windows FS)."; \
		echo "   This may cause permission errors with XeLaTeX."; \
		echo "   Consider running: cp -r /mnt/c/Users/.../latex_cv ~/latex_cv && cd ~/latex_cv"; \
	fi
	@if ! command -v $(LATEXMK) >/dev/null 2>&1; then \
		echo "❌ latexmk not found. Run 'make install' first."; exit 1; fi
	@if ! command -v xelatex >/dev/null 2>&1; then \
		echo "❌ xelatex not found. Run 'make install' first."; exit 1; fi


# --- Install dependencies (Linux, macOS, Windows) ---

install:
	@echo "🔧 Installing LaTeX toolchain and Python deps..."
	@if command -v apt-get >/dev/null 2>&1; then \
		sudo apt-get update && sudo apt-get install -y latexmk texlive-xetex texlive-latex-extra texlive-fonts-extra; \
	elif command -v brew >/dev/null 2>&1; then \
		brew install --cask mactex-no-gui || brew install --cask mactex; \
		sudo /Library/TeX/texbin/tlmgr path add >/dev/null 2>&1 || true; \
	elif command -v choco >/dev/null 2>&1; then \
		choco install -y miktex; \
	else \
		echo "Unsupported system. Install TeX Live (with XeLaTeX) manually."; exit 1; \
	fi
	@echo "📦 Installing Python dependencies..."
	$(PYTHON) -m pip install --upgrade pip
	@if [ -f "$(REQUIREMENTS)" ]; then $(PYTHON) -m pip install -r $(REQUIREMENTS); fi


# --- Cleaning ---

clean:
	@echo "🧹 Cleaning temporary LaTeX files..."
	$(LATEXMK) -jobname=$(JOBNAME) -c >/dev/null 2>&1 || true
	rm -f $(PNG) $(basename $(TEX)).pdf *.aux *.log *.out *.fls *.fdb_latexmk *.synctex.gz

distclean: clean
	rm -f $(PDF)
	@echo "🗑️  All generated files removed."

# --- Live rebuild ---

watch:
	@echo "👀 Watching for file changes..."
	$(LATEXMK) $(LATEXMK_OPTS) -pvc -jobname=$(JOBNAME) $(TEX)
