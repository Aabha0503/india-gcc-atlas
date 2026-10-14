"""Render the intake brief as a print-ready, in-memory PDF."""

from __future__ import annotations

import re
from datetime import date
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


PAGE_WIDTH = 1240
PAGE_HEIGHT = 1754
DPI = 150
MARGIN_X = 112
CONTENT_WIDTH = PAGE_WIDTH - 2 * MARGIN_X
NAVY = "#14243A"
CHARCOAL = "#253247"
MUTED = "#526173"
BLUE = "#005A9C"
PALE_BLUE = "#E7F1FC"
LIGHT_GREY = "#F1F3F6"
RULE = "#D5DCE5"
WHITE = "#FFFFFF"


def _font_path(bold: bool = False) -> Path:
    font_names = ("arialbd.ttf", "segoeuib.ttf") if bold else (
        "arial.ttf",
        "segoeui.ttf",
    )
    for name in font_names:
        path = Path("C:/Windows/Fonts") / name
        if path.exists():
            return path
    raise FileNotFoundError(
        "A supported Windows font (Arial or Segoe UI) is required to render the PDF."
    )


def _clean_markdown(text: str) -> str:
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"`(.+?)`", r"\1", text)
    return text.strip()


def _wrap_text(text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    lines: list[str] = []
    for paragraph in text.splitlines() or [""]:
        if not paragraph:
            lines.append("")
            continue
        words = paragraph.split()
        line = ""
        for word in words:
            candidate = f"{line} {word}".strip()
            if font.getlength(candidate) <= max_width:
                line = candidate
                continue
            if line:
                lines.append(line)
            line = ""
            if font.getlength(word) <= max_width:
                line = word
                continue
            fragment = ""
            for character in word:
                if font.getlength(fragment + character) > max_width and fragment:
                    lines.append(fragment)
                    fragment = character
                else:
                    fragment += character
            line = fragment
        if line:
            lines.append(line)
    return lines


def _brief_values(markdown: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in markdown.splitlines():
        match = re.match(r"^- (Company|Headquarters country|Industry|Target headcount|Planned functions|Ramp timeline): (.*)$", line)
        if match:
            values[match.group(1)] = _clean_markdown(match.group(2))
    return values


class _PdfPages:
    def __init__(self) -> None:
        self.font_body = ImageFont.truetype(str(_font_path()), 23)
        self.font_small = ImageFont.truetype(str(_font_path()), 19)
        self.font_label = ImageFont.truetype(str(_font_path(bold=True)), 18)
        self.font_h2 = ImageFont.truetype(str(_font_path(bold=True)), 30)
        self.font_h3 = ImageFont.truetype(str(_font_path(bold=True)), 24)
        self.font_title = ImageFont.truetype(str(_font_path(bold=True)), 49)
        self.pages: list[Image.Image] = []
        self.image: Image.Image
        self.draw: ImageDraw.ImageDraw
        self.y = 0
        self._new_page(first=True)

    def _new_page(self, first: bool = False) -> None:
        self.image = Image.new("RGB", (PAGE_WIDTH, PAGE_HEIGHT), WHITE)
        self.draw = ImageDraw.Draw(self.image)
        self.pages.append(self.image)
        self.draw.rectangle((0, 0, PAGE_WIDTH, 16), fill=BLUE)
        self.draw.text((MARGIN_X, 48), "INDIA GCC ATLAS  /  INTAKE BRIEF", font=self.font_label, fill=BLUE)
        self.draw.line((MARGIN_X, 86, PAGE_WIDTH - MARGIN_X, 86), fill=RULE, width=2)
        self.y = 122
        if first:
            self.draw.text((MARGIN_X, self.y), "India GCC entry brief", font=self.font_title, fill=NAVY)
            self.y += 72
            self.draw.text(
                (MARGIN_X, self.y),
                f"Generated {date.today().strftime('%d %B %Y')}",
                font=self.font_small,
                fill=MUTED,
            )
            self.y += 50

    def _ensure_space(self, height: int) -> None:
        if self.y + height > PAGE_HEIGHT - 105:
            self._new_page()

    def _draw_lines(
        self,
        lines: list[str],
        font: ImageFont.FreeTypeFont,
        color: str,
        x: int = MARGIN_X,
        line_gap: int = 10,
    ) -> int:
        line_height = font.getbbox("Ag")[3] - font.getbbox("Ag")[1] + line_gap
        for line in lines:
            self._ensure_space(line_height)
            self.draw.text((x, self.y), line, font=font, fill=color)
            self.y += line_height
        return len(lines) * line_height

    def _add_panel(
        self,
        title: str,
        lines: list[str],
        font: ImageFont.FreeTypeFont,
        color: str,
        fill: str,
    ) -> None:
        line_height = font.getbbox("Ag")[3] - font.getbbox("Ag")[1] + 8
        line_index = 0
        while line_index < len(lines):
            if PAGE_HEIGHT - 105 - self.y < 150:
                self._new_page()
            available_height = PAGE_HEIGHT - 105 - self.y
            lines_per_panel = max(1, (available_height - 76) // line_height)
            panel_lines = lines[line_index : line_index + lines_per_panel]
            panel_height = 44 + len(panel_lines) * line_height + 24
            top = self.y
            self.draw.rounded_rectangle(
                (MARGIN_X, top, PAGE_WIDTH - MARGIN_X, top + panel_height),
                radius=12,
                fill=fill,
                outline=RULE,
                width=2,
            )
            panel_title = title if line_index == 0 else f"{title} (continued)"
            self.draw.text(
                (MARGIN_X + 22, self.y + 14),
                panel_title.upper(),
                font=self.font_label,
                fill=BLUE,
            )
            self.y += 43
            self._draw_lines(
                panel_lines,
                font,
                color,
                x=MARGIN_X + 22,
                line_gap=8,
            )
            self.y = top + panel_height + 20
            line_index += len(panel_lines)

    def add_summary(self, markdown: str) -> None:
        values = _brief_values(markdown)
        details = []
        for label in ("Company", "Headquarters country", "Industry"):
            value = values.get(label, "")
            if value and value != "Not provided":
                details.append(f"{label}: {value}")
        plan = values.get("Planned functions", "")
        if plan and plan != "Not provided":
            details.append(f"Planned functions: {plan}")
        headcount = values.get("Target headcount", "")
        ramp = values.get("Ramp timeline", "")
        if headcount and headcount != "Not provided":
            details.append(f"Target team: {headcount}")
        if ramp and ramp != "Not provided":
            details.append(f"Hiring timeline: {ramp}")

        summary = (
            "This brief summarizes information supplied during intake. "
            "It is intended to support an initial planning discussion, not to make a city recommendation."
        )
        if details:
            summary += " " + " · ".join(details) + "."
        wrapped = _wrap_text(summary, self.font_body, CONTENT_WIDTH - 44)
        self._add_panel("Executive summary", wrapped, self.font_body, CHARCOAL, LIGHT_GREY)

        note = (
            "Evidence note: This intake brief contains user-provided information, not independently "
            "verified research. Market comparisons, city recommendations, policy findings, and "
            "financial projections still require research."
        )
        note_lines = _wrap_text(note, self.font_small, CONTENT_WIDTH - 44)
        self._add_panel("Evidence note", note_lines, self.font_small, NAVY, PALE_BLUE)

    def add_heading(self, text: str, level: int) -> None:
        font = self.font_h2 if level == 2 else self.font_h3
        height = 66 if level == 2 else 52
        self._ensure_space(height + 90)
        if level == 2:
            self.y += 8
            self.draw.rectangle((MARGIN_X, self.y + 3, MARGIN_X + 6, self.y + 38), fill=BLUE)
            x = MARGIN_X + 20
        else:
            x = MARGIN_X
        self.draw.text((x, self.y), text, font=font, fill=NAVY)
        self.y += height

    def add_paragraph(self, text: str) -> None:
        text = _clean_markdown(text)
        if not text:
            self.y += 12
            return
        lines = _wrap_text(text, self.font_body, CONTENT_WIDTH)
        self._draw_lines(lines, self.font_body, CHARCOAL, line_gap=10)
        self._ensure_space(12)
        self.y += 12

    def add_bullet(self, text: str, number: str | None = None) -> None:
        text = _clean_markdown(text)
        prefix_width = 42
        lines = _wrap_text(text, self.font_body, CONTENT_WIDTH - prefix_width)
        line_height = self.font_body.getbbox("Ag")[3] - self.font_body.getbbox("Ag")[1] + 10
        for index, line in enumerate(lines):
            self._ensure_space(line_height)
            if index == 0:
                if number is None:
                    self.draw.ellipse(
                        (MARGIN_X + 4, self.y + 11, MARGIN_X + 14, self.y + 21),
                        fill=BLUE,
                    )
                else:
                    self.draw.text((MARGIN_X, self.y), number, font=self.font_label, fill=BLUE)
            self._draw_lines(
                [line],
                self.font_body,
                CHARCOAL,
                x=MARGIN_X + prefix_width,
                line_gap=10,
            )
        self._ensure_space(8)
        self.y += 8

    def add_notice(self, text: str) -> None:
        lines = _wrap_text(_clean_markdown(text), self.font_small, CONTENT_WIDTH - 44)
        line_height = self.font_small.getbbox("Ag")[3] - self.font_small.getbbox("Ag")[1] + 8
        line_index = 0
        while line_index < len(lines):
            if PAGE_HEIGHT - 105 - self.y < 120:
                self._new_page()
            available_height = PAGE_HEIGHT - 105 - self.y
            lines_per_panel = max(1, (available_height - 34) // line_height)
            panel_lines = lines[line_index : line_index + lines_per_panel]
            panel_height = len(panel_lines) * line_height + 28
            top = self.y
            self.draw.rounded_rectangle(
                (MARGIN_X, top, PAGE_WIDTH - MARGIN_X, top + panel_height),
                radius=10,
                fill=PALE_BLUE,
                outline="#9CB9D6",
                width=2,
            )
            self.y += 14
            self._draw_lines(
                panel_lines,
                self.font_small,
                NAVY,
                x=MARGIN_X + 22,
                line_gap=8,
            )
            self.y = top + panel_height + 14
            line_index += len(panel_lines)

    def add_markdown(self, markdown: str) -> None:
        self.add_summary(markdown)
        for raw_line in markdown.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            if line.startswith("# "):
                continue
            if line.startswith("## "):
                self.add_heading(_clean_markdown(line[3:]), 2)
            elif line.startswith("### "):
                self.add_heading(_clean_markdown(line[4:]), 3)
            elif line.startswith("> "):
                self.add_notice(line[2:])
            elif line.startswith("- "):
                self.add_bullet(line[2:])
            else:
                numbered = re.match(r"^(\d+)\.\s+(.*)$", line)
                if numbered:
                    self.add_bullet(numbered.group(2), f"{numbered.group(1)}.")
                else:
                    self.add_paragraph(line)

    def to_pdf(self) -> bytes:
        total = len(self.pages)
        for page_number, page in enumerate(self.pages, start=1):
            draw = ImageDraw.Draw(page)
            footer_y = PAGE_HEIGHT - 70
            draw.line((MARGIN_X, footer_y - 16, PAGE_WIDTH - MARGIN_X, footer_y - 16), fill=RULE, width=2)
            draw.text(
                (MARGIN_X, footer_y),
                "India GCC Atlas  ·  Intake-generated; research findings require validation",
                font=self.font_small,
                fill=MUTED,
            )
            label = f"{page_number} / {total}"
            label_width = self.font_small.getlength(label)
            draw.text(
                (PAGE_WIDTH - MARGIN_X - label_width, footer_y),
                label,
                font=self.font_small,
                fill=NAVY,
            )

        output = BytesIO()
        self.pages[0].save(
            output,
            format="PDF",
            save_all=True,
            append_images=self.pages[1:],
            resolution=float(DPI),
        )
        return output.getvalue()


def build_pdf_report(markdown: str) -> bytes:
    """Create a styled, multi-page PDF from the current Markdown brief."""
    pages = _PdfPages()
    pages.add_markdown(markdown)
    return pages.to_pdf()
