"""
Generate a PDF listing words from a training Session, laid out as a
bordered table.

Word selection reuses training.Session.build_session(), the same
interactive setup (vocabulary/top-verbs, test type, part of speech, JLPT
level) used to start a training session, so the PDF always lists the same
words a training Session would quiz on (burned words excluded).

Usage:
    python generate_jlpt_pdf.py
    (then answer the same prompts as when starting a training session)

Requires: pip install reportlab
"""

import os
import sys

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Table, TableStyle

from training import Session, SessionTopVerbs, SessionVocabulary, Word

JAPANESE_FONT = "NotoSansJP"
JAPANESE_FONT_PATH = r"C:\Windows\Fonts\NotoSansJP-VF.ttf"


def register_japanese_font():
    pdfmetrics.registerFont(TTFont(JAPANESE_FONT, JAPANESE_FONT_PATH))


def collect_words(session: Session) -> list[Word]:
    """Words a training Session would ask about, restored to CSV order
    (Session.__init__ shuffles questions_word in place for quizzing)."""
    return sorted((question.item for question in session.questions_word), key=lambda word: word.index)


def describe_session(session: Session) -> str:
    if isinstance(session, SessionVocabulary):
        word_type = session.part_of_speech or "all"
    elif isinstance(session, SessionTopVerbs):
        word_type = "top_verbs"
    else:
        word_type = "words"
    jlpt_label = "all" if session.jlpt_levels is None else "_".join(str(level) for level in session.jlpt_levels)
    return f"{word_type}_JLPT_{jlpt_label}"


def main():
    session = Session.build_session()

    words = collect_words(session)

    if not words:
        print("No words found for this session (burned words excluded, or a kanji-only test was selected).")
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

    for word in words:
        data.append([
            Paragraph(word.word, jp_style),
            Paragraph(word.kana, jp_style),
            Paragraph(word.romaji, en_style),
            Paragraph(word.meaning, en_style),
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

    label = describe_session(session)
    output_path = os.path.abspath(f"{label}.pdf")

    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        title=label,
    )
    doc.build([table])

    print(f"Generated {output_path} with {len(words)} word(s).")


if __name__ == "__main__":
    sys.exit(main())
