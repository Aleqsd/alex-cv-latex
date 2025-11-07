# Alexandre DO-O ALMEIDA — CV

This repository contains the LaTeX source for my one-page résumé.

## 🧰 Prerequisites

Installing Latex and it's a mess so use ChatGPT for instructions.

## 📦 Installation

There's a pip install to do also

```bash
pip install pdf2image
```

And then the CTRL+S will automatically adapt the PDF and convert it to PNG. It's done in settings.json

## 🚀 Usage

```bash
make install   # install LaTeX + python dependencies (interactive if packages are missing)
make pdf       # build CV_Alexandre_DO_O_ALMEIDA_2025.pdf with latexmk
make png       # regenerate the PNG preview from the latest PDF
make clean     # drop LaTeX aux files + PNG preview
```
