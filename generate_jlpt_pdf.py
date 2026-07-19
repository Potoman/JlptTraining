"""
Generate a PDF listing words from all_hiragana_with_pos.csv, filtered by
part_of_speech and JLPT level, laid out as a bordered table.

Usage:
    python generate_jlpt_pdf.py
    (then answer the word type and JLPT level prompts, e.g. "verb" and "JLPT_4")

Requires: pip install reportlab
"""

import csv
import os
import re
import sys

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Table, TableStyle

CSV_PATH = "all_hiragana_with_pos.csv"

JAPANESE_FONT = "NotoSansJP"
JAPANESE_FONT_PATH = r"C:\Windows\Fonts\NotoSansJP-VF.ttf"


def register_japanese_font():
    pdfmetrics.registerFont(TTFont(JAPANESE_FONT, JAPANESE_FONT_PATH))


def normalize_jlpt(value):
    """Turn '4', 'N4', 'n4', 'JLPT_4' into 'JLPT_4'."""
    match = re.search(r"(\d)", value)
    if not match:
        raise ValueError(f"Could not parse a JLPT level out of '{value}'")
    return f"JLPT_{match.group(1)}"


def main():
    word_type = input("Word type (e.g. verb, adjective, noun, adverb, other): ").strip()
    jlpt_input = input("JLPT level (e.g. JLPT_4, 4, N4): ").strip()
    csv_tag = normalize_jlpt(jlpt_input)

    with open(CSV_PATH, encoding="utf-8") as f:
        rows = [
            row
            for row in csv.DictReader(f)
            if row["part_of_speech"] == word_type and row["tags"] == csv_tag
        ]

    if not rows:
        print(f"No rows found for part_of_speech='{word_type}' and tags='{csv_tag}'.")
        return

    register_japanese_font()

    header_style = ParagraphStyle(name="Header", fontName="Helvetica-Bold", fontSize=10, leading=12)
    jp_style = ParagraphStyle(name="Japanese", fontName=JAPANESE_FONT, fontSize=11, leading=14)
    en_style = ParagraphStyle(name="English", fontName="Helvetica", fontSize=9, leading=12)

    data = [[
        Paragraph("Expression", header_style),
        Paragraph("Reading", header_style),
        Paragraph("Romaji", header_style),
        Paragraph("Meaning", header_style),
    ]]

    for row in rows:
        data.append([
            Paragraph(row["expression"], jp_style),
            Paragraph(row["reading"], jp_style),
            Paragraph(row["romaji"], en_style),
            Paragraph(row["meaning"], en_style),
        ])

    col_widths = [32 * mm, 32 * mm, 32 * mm, 90 * mm]

    table = Table(data, colWidths=col_widths, repeatRows=1)
    table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))

    output_path = os.path.abspath(f"{word_type}_{csv_tag}.pdf")

    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        title=f"{word_type} - {csv_tag}",
    )
    doc.build([table])

    print(f"Generated {output_path} with {len(rows)} word(s).")


if __name__ == "__main__":
    sys.exit(main())
