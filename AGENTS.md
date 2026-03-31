# Repository Guidelines

## Project Structure & Module Organization
- `cv.tex` is the single source of truth for the résumé content; keep sections modular with clear comment blocks so reviewers can diff changes quickly.
- `muratcan_cv.cls` defines the custom document class, typography, and spacing; update it only when adjusting global styling for the layout.
- `photo.jpg` holds the profile image referenced inside `cv.tex`; replace it with identically named assets to avoid code changes.
- `pdf_to_png.py` converts the generated PDF (`CV_Alexandre_DO_O_ALMEIDA_2025.pdf`) into a PNG preview; keep derivative outputs (`*.pdf`, `*.png`, `*.aux`, etc.) out of PRs unless the build artifact itself is the point of the change.

## Build, Test, and Development Commands
- `latexmk -pdf cv.tex` produces a clean PDF build and reruns compilation as needed to resolve cross-references.
- `pdflatex -interaction=nonstopmode cv.tex` is the quick single-pass option; run it twice when editing tables or references.
- `python pdf_to_png.py` regenerates the PNG preview; ensure `pip install pdf2image` and a local Poppler install are available beforehand.

## Coding Style & Naming Conventions
- Write LaTeX with two-space indentation inside environments and align ampersands in tables for readability.
- Declare reusable snippets via `\newcommand` in `cv.tex` and keep macro names in uppercase snake case (e.g., `\NEWROLEHEADER`).
- Preserve the document’s one-page layout: prefer manual line breaks (`\\`) over altering class-level spacing unless absolutely necessary.
- Comment structural sections with `% --- Section Name ---` so diffs surface intent without expanding the whole file.

## Testing Guidelines
- Compile the PDF and fail the review if `CV_Alexandre_DO_O_ALMEIDA_2025.log` reports undefined references, overfull boxes, or font warnings.
- Compare the newly generated PDF/PNG against prior versions using a PDF diff tool or by toggling pages side-by-side to confirm layout stability.
- When touching `pdf_to_png.py`, rerun it and spot-check the PNG’s resolution and cropping.

## Commit & Pull Request Guidelines
- Existing history favors short, present-tense summaries (e.g., “Update cv header copy”); follow that style and keep each commit focused on one logical edit.
- For PRs, include: a concise purpose statement, bullet highlights of noteworthy layout or content changes, screenshots of the rendered PDF if the visual changes matter, and references to any tracking issues.
- Double-check that generated build artifacts are excluded unless explicitly required for review; attach them as PR assets when reviewers need to compare output.
