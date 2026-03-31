from __future__ import annotations

import argparse
import re
from pathlib import Path

import requests
from bs4 import BeautifulSoup


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch and clean a job offer page into markdown-friendly text.")
    parser.add_argument("--url", required=True, help="Job offer URL.")
    parser.add_argument("--output", help="Optional output file path.")
    parser.add_argument("--timeout", type=int, default=20, help="HTTP timeout in seconds.")
    return parser.parse_args()


def clean_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "svg", "img"]):
        tag.decompose()

    title = soup.title.get_text(" ", strip=True) if soup.title else ""
    headings = [node.get_text(" ", strip=True) for node in soup.find_all(["h1", "h2", "h3"])[:12]]
    paragraphs = [
        node.get_text(" ", strip=True)
        for node in soup.find_all(["p", "li"])
        if node.get_text(" ", strip=True)
    ]
    merged = "\n".join(filter(None, [title, *headings, *paragraphs]))
    merged = re.sub(r"\n{3,}", "\n\n", merged)
    merged = re.sub(r"[ \t]+", " ", merged)
    return merged.strip()


def main() -> None:
    args = parse_args()
    response = requests.get(
        args.url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
            )
        },
        timeout=args.timeout,
    )
    response.raise_for_status()
    text = clean_text(response.text)

    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text, encoding="utf-8")
        print(f"Wrote cleaned job text to {output}")
    else:
        print(text)


if __name__ == "__main__":
    main()
