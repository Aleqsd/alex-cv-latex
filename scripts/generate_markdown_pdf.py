from __future__ import annotations

import argparse
import re
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, StyleSheet1, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    CondPageBreak,
    HRFlowable,
    ListFlowable,
    ListItem,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

FORCED_PAGEBREAK_BEFORE = set()

NAME_SECTION = "Alexandre Do-O Almeida"
EXPERIENCE_SECTION = "Expériences significatives"
CONTENT_WIDTH = 178 * mm


def build_styles() -> StyleSheet1:
    styles = getSampleStyleSheet()

    styles.add(
        ParagraphStyle(
            name="DocTitle",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=20.5,
            leading=24,
            textColor=colors.HexColor("#16324f"),
            spaceAfter=6,
            alignment=TA_CENTER,
        )
    )
    styles.add(
        ParagraphStyle(
            name="SubtitleDoc",
            parent=styles["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=10.6,
            leading=13,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#35536f"),
            spaceAfter=6,
        )
    )
    styles.add(
        ParagraphStyle(
            name="NameTitle",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=17.2,
            leading=20.5,
            textColor=colors.HexColor("#16324f"),
            spaceBefore=2,
            spaceAfter=4,
            alignment=TA_CENTER,
        )
    )
    styles.add(
        ParagraphStyle(
            name="ContactDoc",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=8.9,
            leading=11.2,
            textColor=colors.HexColor("#334155"),
            spaceAfter=0,
        )
    )
    styles.add(
        ParagraphStyle(
            name="Heading1Doc",
            parent=styles["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=14.2,
            leading=16.8,
            textColor=colors.HexColor("#16324f"),
            spaceBefore=10,
            spaceAfter=2,
        )
    )
    styles.add(
        ParagraphStyle(
            name="Heading2Doc",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=11.2,
            leading=13.2,
            textColor=colors.HexColor("#24496b"),
            spaceBefore=7,
            spaceAfter=3,
        )
    )
    styles.add(
        ParagraphStyle(
            name="ExperienceCompanyDoc",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=12.2,
            leading=14.4,
            textColor=colors.HexColor("#16324f"),
            spaceAfter=1,
        )
    )
    styles.add(
        ParagraphStyle(
            name="ExperienceRoleDoc",
            parent=styles["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=10,
            leading=12.4,
            textColor=colors.HexColor("#24496b"),
            spaceAfter=0,
        )
    )
    styles.add(
        ParagraphStyle(
            name="ExperiencePeriodDoc",
            parent=styles["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=8.7,
            leading=10.8,
            alignment=TA_RIGHT,
            textColor=colors.HexColor("#35536f"),
            spaceAfter=0,
        )
    )
    styles.add(
        ParagraphStyle(
            name="ExperienceMetaDoc",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=8.8,
            leading=11.2,
            textColor=colors.HexColor("#4d5b6a"),
            spaceAfter=0,
        )
    )
    styles.add(
        ParagraphStyle(
            name="BodyDoc",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=9.25,
            leading=12.3,
            spaceAfter=4,
        )
    )
    styles.add(
        ParagraphStyle(
            name="MetaDoc",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=8.8,
            leading=11.4,
            textColor=colors.HexColor("#4d5b6a"),
            spaceAfter=3,
        )
    )
    styles.add(
        ParagraphStyle(
            name="LabelDoc",
            parent=styles["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=10.2,
            leading=12.8,
            textColor=colors.HexColor("#24496b"),
            spaceBefore=2,
            spaceAfter=2,
        )
    )
    styles.add(
        ParagraphStyle(
            name="ExperienceLabelDoc",
            parent=styles["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=8.8,
            leading=10.8,
            textColor=colors.HexColor("#24496b"),
            spaceBefore=5,
            spaceAfter=2,
        )
    )
    styles.add(
        ParagraphStyle(
            name="BulletDoc",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=9.2,
            leading=11.9,
            leftIndent=0,
            spaceAfter=0,
        )
    )
    return styles


def apply_inline_markup(text: str) -> str:
    escaped = escape(text)
    return re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", escaped)


def strip_outer_bold(text: str) -> str:
    if text.startswith("**") and text.endswith("**"):
        return text[2:-2].strip()
    return text


def build_bullet_list(bullets: list[str], styles: StyleSheet1):
    items = [
        ListItem(Paragraph(apply_inline_markup(item), styles["BulletDoc"])) for item in bullets
    ]
    return ListFlowable(
        items,
        bulletType="bullet",
        start="circle",
        leftPadding=14,
        bulletFontName="Helvetica",
        bulletFontSize=8,
        bulletColor=colors.HexColor("#16324f"),
    )


def build_two_column_bullets(bullets: list[str], styles: StyleSheet1):
    midpoint = (len(bullets) + 1) // 2
    left = bullets[:midpoint]
    right = bullets[midpoint:]
    rows = []

    for idx in range(max(len(left), len(right))):
        left_cell = f"• {left[idx]}" if idx < len(left) else ""
        right_cell = f"• {right[idx]}" if idx < len(right) else ""
        rows.append(
            [
                Paragraph(apply_inline_markup(left_cell), styles["BulletDoc"]) if left_cell else "",
                Paragraph(apply_inline_markup(right_cell), styles["BulletDoc"]) if right_cell else "",
            ]
        )

    table = Table(rows, colWidths=[86 * mm, 86 * mm], hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 1),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
            ]
        )
    )
    return table


def build_experience_header(
    company: str, role: str | None, meta_lines: list[str], styles: StyleSheet1
):
    period_line = next((line for line in meta_lines if "Période :" in line), "")
    context_line = next((line for line in meta_lines if "Contexte :" in line), "")

    rows = [
        [
            Paragraph(apply_inline_markup(company), styles["ExperienceCompanyDoc"]),
            Paragraph(apply_inline_markup(strip_outer_bold(period_line)), styles["ExperiencePeriodDoc"])
            if period_line
            else "",
        ]
    ]

    if role:
        rows.append(
            [
                Paragraph(
                    apply_inline_markup(strip_outer_bold(role)),
                    styles["ExperienceRoleDoc"],
                ),
                "",
            ]
        )

    if context_line:
        rows.append(
            [
                Paragraph(
                    apply_inline_markup(strip_outer_bold(context_line)),
                    styles["ExperienceMetaDoc"],
                ),
                "",
            ]
        )

    table = Table(rows, colWidths=[124 * mm, 54 * mm], hAlign="LEFT")
    style_commands = [
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#edf4fa")),
        ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#d7e3ef")),
        ("LINEABOVE", (0, 0), (-1, 0), 1.2, colors.HexColor("#aac1d7")),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, 0), 6),
        ("TOPPADDING", (0, 1), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -2), 1),
        ("BOTTOMPADDING", (0, -1), (-1, -1), 6),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]
    if role:
        style_commands.append(("SPAN", (0, 1), (1, 1)))
    if context_line:
        row_index = 2 if role else 1
        style_commands.append(("SPAN", (0, row_index), (1, row_index)))

    table.setStyle(
        TableStyle(style_commands)
    )
    return table


def build_contact_block(items: list[str], styles: StyleSheet1):
    rows = []
    for item in items:
        if ":" in item:
            label, value = item.split(":", 1)
            content = f"<b>{escape(label.strip())} :</b> {escape(value.strip())}"
        else:
            content = escape(item)
        rows.append([Paragraph(content, styles["ContactDoc"])])

    table = Table(rows, colWidths=[CONTENT_WIDTH], hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f7fafc")),
                ("BOX", (0, 0), (-1, -1), 0.7, colors.HexColor("#d8e2ec")),
                ("LINEABOVE", (0, 0), (-1, 0), 1.0, colors.HexColor("#bfd0e0")),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, 0), 6),
                ("TOPPADDING", (0, 1), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -2), 1),
                ("BOTTOMPADDING", (0, -1), (-1, -1), 6),
            ]
        )
    )
    return table


def flush_bullets(blocks: list, pending_bullets: list[str]) -> None:
    if pending_bullets:
        blocks.append({"kind": "bullets", "items": pending_bullets[:]})
        pending_bullets.clear()


def parse_markdown(markdown_text: str) -> list[dict]:
    blocks: list[dict] = []
    pending_bullets: list[str] = []

    for raw_line in markdown_text.splitlines():
        line = raw_line.rstrip()

        if not line.strip():
            flush_bullets(blocks, pending_bullets)
            continue

        if line.startswith("- "):
            pending_bullets.append(line[2:].strip())
            continue

        flush_bullets(blocks, pending_bullets)

        if line.startswith("# "):
            blocks.append({"kind": "h1", "text": line[2:].strip()})
        elif line.startswith("## "):
            blocks.append({"kind": "h2", "text": line[3:].strip()})
        elif line.startswith("### "):
            blocks.append({"kind": "h3", "text": line[4:].strip()})
        elif line.startswith("**") and "Période :" in line:
            blocks.append({"kind": "meta", "text": line})
        elif line.startswith("**") and "Contexte :" in line:
            blocks.append({"kind": "meta", "text": line})
        elif line.startswith("**") and line.endswith("**"):
            blocks.append({"kind": "label", "text": line})
        else:
            blocks.append({"kind": "p", "text": line})

    flush_bullets(blocks, pending_bullets)
    return blocks


def render_block(block: dict, styles: StyleSheet1, compact_lists: bool = False) -> list:
    kind = block["kind"]
    text = block.get("text", "")

    if kind == "h1":
        return [Paragraph(apply_inline_markup(text), styles["DocTitle"]), Spacer(1, 2)]
    if kind == "h2":
        style_name = "NameTitle" if text == NAME_SECTION else "Heading1Doc"
        flows = [Paragraph(apply_inline_markup(text), styles[style_name])]
        if text != NAME_SECTION:
            flows.append(
                HRFlowable(
                    width="100%",
                    thickness=0.7,
                    color=colors.HexColor("#d9e3ef"),
                    spaceBefore=0,
                    spaceAfter=5,
                )
            )
        else:
            flows.append(Spacer(1, 2))
        return flows
    if kind == "h3":
        return [Paragraph(apply_inline_markup(text), styles["Heading2Doc"])]
    if kind == "label":
        return [Paragraph(apply_inline_markup(text), styles["LabelDoc"])]
    if kind == "meta":
        return [Paragraph(apply_inline_markup(text), styles["MetaDoc"])]
    if kind == "bullets":
        items = block["items"]
        if compact_lists and len(items) >= 4:
            return [build_two_column_bullets(items, styles), Spacer(1, 4)]
        return [build_bullet_list(items, styles), Spacer(1, 3)]
    if kind == "p":
        return [Paragraph(apply_inline_markup(text), styles["BodyDoc"])]
    return []


def render_experience_block(block: dict, styles: StyleSheet1) -> list:
    if block["kind"] == "label":
        return [
            Paragraph(
                apply_inline_markup(strip_outer_bold(block["text"])),
                styles["ExperienceLabelDoc"],
            )
        ]
    return render_block(block, styles)


def markdown_to_story(markdown_text: str, styles: StyleSheet1) -> list:
    blocks = parse_markdown(markdown_text)
    story: list = []
    current_section = ""
    idx = 0

    while idx < len(blocks):
        block = blocks[idx]
        kind = block["kind"]
        compact_lists = current_section in {
            "Compétences techniques",
            "Positionnement",
            "Certifications, distinctions et publications",
            "Types de missions cibles",
        }

        if kind == "h2":
            heading = block["text"]
            current_section = heading
            if story and heading in FORCED_PAGEBREAK_BEFORE:
                story.append(PageBreak())
            elif story:
                story.append(CondPageBreak(30 * mm))
            story.extend(render_block(block, styles))
            idx += 1
            if (
                current_section == NAME_SECTION
                and idx < len(blocks)
                and blocks[idx]["kind"] == "bullets"
            ):
                story.append(build_contact_block(blocks[idx]["items"], styles))
                story.append(Spacer(1, 6))
                idx += 1
            continue

        if kind == "h1":
            story.extend(render_block(block, styles))
            idx += 1
            if idx < len(blocks) and blocks[idx]["kind"] == "p":
                story.append(
                    Paragraph(
                        apply_inline_markup(blocks[idx]["text"]),
                        styles["SubtitleDoc"],
                    )
                )
                idx += 1
            continue

        if kind == "h3":
            if current_section == EXPERIENCE_SECTION:
                story.append(CondPageBreak(56 * mm))
                company = block["text"]
                idx += 1
                role = None
                meta_lines: list[str] = []
                if idx < len(blocks) and blocks[idx]["kind"] == "label":
                    role = blocks[idx]["text"]
                    idx += 1
                while idx < len(blocks) and blocks[idx]["kind"] == "meta":
                    meta_lines.append(blocks[idx]["text"])
                    idx += 1

                story.append(build_experience_header(company, role, meta_lines, styles))
                story.append(Spacer(1, 4))

                while idx < len(blocks) and blocks[idx]["kind"] not in {"h2", "h3"}:
                    story.extend(render_experience_block(blocks[idx], styles))
                    idx += 1

                story.append(Spacer(1, 4))
                story.append(
                    HRFlowable(
                        width="100%",
                        thickness=0.5,
                        color=colors.HexColor("#e6edf5"),
                        spaceBefore=0,
                        spaceAfter=4,
                    )
                )
                continue

            story.append(CondPageBreak(24 * mm))
            story.extend(render_block(block, styles, compact_lists=compact_lists))
            idx += 1
            while idx < len(blocks) and blocks[idx]["kind"] not in {"h2", "h3"}:
                story.extend(render_block(blocks[idx], styles, compact_lists=compact_lists))
                idx += 1
            continue

        story.extend(render_block(block, styles, compact_lists=compact_lists))
        idx += 1

    return story


def draw_footer(canvas, doc) -> None:
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#6b7280"))
    canvas.drawString(16 * mm, 10 * mm, "Dossier de compétences")
    canvas.drawRightString(doc.pagesize[0] - 18 * mm, 10 * mm, f"Page {doc.page}")
    canvas.restoreState()


def generate_pdf(input_path: Path, output_path: Path) -> None:
    styles = build_styles()
    markdown_text = input_path.read_text(encoding="utf-8")
    story = markdown_to_story(markdown_text, styles)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        leftMargin=16 * mm,
        rightMargin=16 * mm,
        topMargin=16 * mm,
        bottomMargin=14 * mm,
        title="Dossier de compétences - Software Engineer, Platform / DevOps, IA - Alexandre Do-O Almeida",
        author="Alexandre Do-O Almeida",
    )
    doc.build(story, onFirstPage=draw_footer, onLaterPages=draw_footer)


def main() -> None:
    parser = argparse.ArgumentParser(description="Render a markdown dossier to PDF.")
    parser.add_argument("--input", required=True, help="Input markdown file")
    parser.add_argument("--output", required=True, help="Output PDF file")
    args = parser.parse_args()

    generate_pdf(Path(args.input), Path(args.output))


if __name__ == "__main__":
    main()
