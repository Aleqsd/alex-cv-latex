from argparse import ArgumentParser
from pathlib import Path

from pdf2image import convert_from_path


def main() -> None:
    parser = ArgumentParser(description="Convert the first page of a PDF to PNG.")
    parser.add_argument(
        "--input",
        default="output/main/CV_Alexandre_DO_O_ALMEIDA_2025.pdf",
        help="Input PDF path.",
    )
    parser.add_argument(
        "--output",
        default="output/main/CV_Alexandre_DO_O_ALMEIDA_2025.png",
        help="Output PNG path.",
    )
    parser.add_argument(
        "--dpi",
        type=int,
        default=300,
        help="Render DPI.",
    )
    args = parser.parse_args()

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    images = convert_from_path(args.input, dpi=args.dpi)
    images[0].save(output_path, "PNG")


if __name__ == "__main__":
    main()
