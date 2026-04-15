"""
reports/asc35060-report.md → reports/asc35060-report.pdf 변환 스크립트
사용: python3 scripts/md_to_pdf.py
"""

import re
import sys
from pathlib import Path
from markdown_it import MarkdownIt
from fpdf import FPDF

BASE_DIR = Path(__file__).parent.parent
MD_PATH  = BASE_DIR / "reports" / "asc35060-report.md"
PDF_PATH = BASE_DIR / "reports" / "asc35060-report.pdf"

FONT_REGULAR = str(Path.home() / "Library/Fonts/NanumGothic.otf")
FONT_BOLD    = str(Path.home() / "Library/Fonts/NanumGothicBold.otf")
FONT_MONO    = "/System/Library/Fonts/Supplemental/Courier New.ttf"

# ── 색상 ───────────────────────────────────────────────────────────────────
COL_TITLE     = (15,  55, 120)   # 짙은 남색
COL_H1        = (20,  70, 140)
COL_H2        = (30,  90, 160)
COL_H3        = (50, 110, 180)
COL_BODY      = (30,  30,  30)
COL_CODE_BG   = (245, 246, 248)
COL_CODE_TEXT = (50,  50,  50)
COL_TABLE_HDR = (220, 230, 245)
COL_TABLE_ROW = (255, 255, 255)
COL_TABLE_ALT = (245, 248, 255)
COL_BORDER    = (180, 190, 210)
COL_LINE      = (200, 210, 230)


class ReportPDF(FPDF):
    def __init__(self):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.set_margins(20, 20, 20)
        self.set_auto_page_break(auto=True, margin=20)

        self.add_font("Nanum",  "",  FONT_REGULAR)
        self.add_font("Nanum",  "B", FONT_BOLD)

        self._page_label = ""   # 머리말 제목
        self._toc = []          # (level, title, page)

    # ── 머리글 / 바닥글 ──────────────────────────────────────────────────
    def header(self):
        if self.page_no() == 1:
            return
        self.set_font("Nanum", "", 8)
        self.set_text_color(140, 150, 170)
        self.cell(0, 8, "ASC 350-60 가상자산 회계기준 분석 보고서", align="L")
        self.ln(0)
        self.set_draw_color(*COL_LINE)
        self.line(20, 16, 190, 16)
        self.ln(4)

    def footer(self):
        self.set_y(-15)
        self.set_font("Nanum", "", 8)
        self.set_text_color(140, 150, 170)
        self.cell(0, 8, f"- {self.page_no()} -", align="C")

    # ── 표지 ─────────────────────────────────────────────────────────────
    def cover_page(self, meta: dict):
        self.add_page()

        # 배경 상단 블록
        self.set_fill_color(*COL_TITLE)
        self.rect(0, 0, 210, 80, "F")

        self.set_y(20)
        self.set_font("Nanum", "B", 22)
        self.set_text_color(255, 255, 255)
        self.multi_cell(0, 12, "ASC 350-60 가상자산\n회계기준 분석 보고서", align="C")

        self.set_y(58)
        self.set_font("Nanum", "", 11)
        self.set_text_color(200, 215, 240)
        self.cell(0, 8, "US GAAP & IFRS 비교 분석 | 재무 영향 | 시장 반응", align="C")

        # 구분선
        self.set_y(90)
        self.set_draw_color(*COL_LINE)
        self.set_line_width(0.4)
        self.line(30, 90, 180, 90)

        # 메타 정보
        self.set_y(100)
        self.set_text_color(*COL_BODY)
        rows = [
            ("작성일",    meta.get("작성일", "-")),
            ("대상 독자", meta.get("대상 독자", "-")),
            ("버전",      meta.get("버전", "-")),
            ("출처",      f"{meta.get('A등급', 0)}건(A등급) / {meta.get('B등급', 0)}건(B등급) / {meta.get('C등급', 0)}건(C등급)  ·  계 {meta.get('총출처', 0)}건"),
        ]
        for label, value in rows:
            self.set_x(30)
            self.set_font("Nanum", "B", 10)
            self.cell(35, 8, label, border=0)
            self.set_font("Nanum", "",  10)
            self.multi_cell(130, 8, value, border=0)

        # 하단 면책 문구
        self.set_y(245)
        self.set_font("Nanum", "", 8)
        self.set_text_color(150, 150, 150)
        self.multi_cell(0, 5,
            "본 보고서는 공개된 1차 출처(FASB, IASB, SEC 공시)와 공신력 있는 해설 자료를 바탕으로 작성되었습니다.\n"
            "사실(ASC 350-60에 의거)과 해석(분석)을 구분하여 표기하였으며, 투자 조언을 목적으로 하지 않습니다.",
            align="C")

    # ── 섹션 구분선 ──────────────────────────────────────────────────────
    def section_line(self):
        self.set_draw_color(*COL_LINE)
        self.set_line_width(0.3)
        self.line(20, self.get_y(), 190, self.get_y())
        self.ln(3)

    # ── 헤딩 렌더링 ──────────────────────────────────────────────────────
    def render_heading(self, level: int, text: str):
        if level == 1:
            self.ln(6)
            self.set_font("Nanum", "B", 17)
            self.set_text_color(*COL_H1)
            self.multi_cell(0, 10, text)
            self.set_draw_color(*COL_H1)
            self.set_line_width(0.6)
            self.line(20, self.get_y(), 190, self.get_y())
            self.ln(4)
        elif level == 2:
            self.ln(5)
            # 왼쪽 강조 바
            self.set_fill_color(*COL_H2)
            self.rect(20, self.get_y(), 3, 8, "F")
            self.set_x(25)
            self.set_font("Nanum", "B", 13)
            self.set_text_color(*COL_H2)
            self.multi_cell(0, 8, text)
            self.ln(2)
        elif level == 3:
            self.ln(3)
            self.set_font("Nanum", "B", 11)
            self.set_text_color(*COL_H3)
            self.multi_cell(0, 7, ">> " + text)
            self.ln(1)
        else:
            self.ln(2)
            self.set_font("Nanum", "B", 10)
            self.set_text_color(*COL_BODY)
            self.multi_cell(0, 7, text)

        self._toc.append((level, text, self.page_no()))

    # ── 본문 단락 ────────────────────────────────────────────────────────
    def render_paragraph(self, text: str):
        self.set_font("Nanum", "", 9.5)
        self.set_text_color(*COL_BODY)
        self.multi_cell(0, 6, text)
        self.ln(2)

    # ── 인용/강조 블록 ───────────────────────────────────────────────────
    def render_blockquote(self, text: str):
        self.set_fill_color(235, 240, 252)
        self.set_draw_color(*COL_H2)
        x, y = self.get_x(), self.get_y()
        # 왼쪽 바
        self.set_fill_color(*COL_H2)
        self.rect(20, y, 2, 14, "F")
        self.set_x(24)
        self.set_font("Nanum", "", 9)
        self.set_text_color(60, 80, 130)
        self.multi_cell(0, 6, text)
        self.ln(2)

    # ── 불릿 리스트 ──────────────────────────────────────────────────────
    def render_bullet(self, text: str, depth: int = 0):
        indent = 5 + depth * 4
        bullet = "•" if depth == 0 else "–"
        self.set_x(20 + indent)
        self.set_font("Nanum", "", 9.5)
        self.set_text_color(*COL_BODY)
        # 불릿 기호
        self.cell(4, 6, bullet)
        self.multi_cell(0, 6, text)

    # ── 번호 리스트 ──────────────────────────────────────────────────────
    def render_numbered(self, num: int, text: str, depth: int = 0):
        indent = 5 + depth * 4
        self.set_x(20 + indent)
        self.set_font("Nanum", "", 9.5)
        self.set_text_color(*COL_BODY)
        self.cell(6, 6, f"{num}.")
        self.multi_cell(0, 6, text)

    # ── 코드 블록 ────────────────────────────────────────────────────────
    def render_code_block(self, text: str):
        self.ln(1)
        self.set_fill_color(*COL_CODE_BG)
        self.set_draw_color(*COL_BORDER)
        self.set_line_width(0.2)
        lines = text.split("\n")
        block_h = len(lines) * 5.5 + 4
        x, y = self.get_x(), self.get_y()
        self.rect(20, y, 170, block_h, "FD")
        self.set_y(y + 2)
        for line in lines:
            self.set_x(22)
            self.set_font("Nanum", "", 8)
            self.set_text_color(*COL_CODE_TEXT)
            self.cell(0, 5.5, line[:95])  # 너무 긴 줄 자르기
            self.ln()
        self.ln(2)

    # ── 구분선 ───────────────────────────────────────────────────────────
    def render_hr(self):
        self.ln(2)
        self.set_draw_color(*COL_LINE)
        self.set_line_width(0.3)
        self.line(20, self.get_y(), 190, self.get_y())
        self.ln(4)

    # ── 표 ───────────────────────────────────────────────────────────────
    def render_table(self, headers: list[str], rows: list[list[str]]):
        n_cols = len(headers)
        if n_cols == 0:
            return

        page_w = 170  # 여백 제외
        # 각 열 너비: 첫 열이 약간 넓게
        if n_cols == 1:
            col_w = [page_w]
        else:
            col_w = [page_w * 0.28] + [page_w * 0.72 / (n_cols - 1)] * (n_cols - 1)

        # 헤더 배경
        self.set_fill_color(*COL_TABLE_HDR)
        self.set_text_color(*COL_H2)
        self.set_font("Nanum", "B", 8.5)
        self.set_draw_color(*COL_BORDER)
        self.set_line_width(0.2)

        for i, h in enumerate(headers):
            self.cell(col_w[i], 7, h[:40], border=1, fill=True)
        self.ln()

        # 데이터 행
        for r_idx, row in enumerate(rows):
            fill_color = COL_TABLE_ALT if r_idx % 2 == 0 else COL_TABLE_ROW
            self.set_fill_color(*fill_color)
            self.set_text_color(*COL_BODY)
            self.set_font("Nanum", "", 8.5)

            # 행 높이: 최대 셀 줄 수 기준
            row_h = 6
            for i, cell_text in enumerate(row):
                if i < n_cols:
                    lines_needed = max(1, len(str(cell_text)) // max(1, int(col_w[i] / 2.2)) + 1)
                    row_h = max(row_h, lines_needed * 5.5)
            row_h = min(row_h, 24)  # 최대 높이 제한

            # 페이지 넘김 체크
            if self.get_y() + row_h > self.h - 25:
                self.add_page()
                # 헤더 반복
                self.set_fill_color(*COL_TABLE_HDR)
                self.set_text_color(*COL_H2)
                self.set_font("Nanum", "B", 8.5)
                for i, h in enumerate(headers):
                    self.cell(col_w[i], 7, h[:40], border=1, fill=True)
                self.ln()
                self.set_fill_color(*fill_color)
                self.set_text_color(*COL_BODY)
                self.set_font("Nanum", "", 8.5)

            for i in range(n_cols):
                cell_text = str(row[i]) if i < len(row) else ""
                self.cell(col_w[i], row_h, cell_text[:60], border=1, fill=True)
            self.ln()

        self.ln(3)


# ── 마크다운 → 토큰 파싱 후 PDF 렌더링 ──────────────────────────────────────

def clean_inline(text: str) -> str:
    """인라인 마크다운 기호 제거 (굵게, 이탤릭, 링크, 코드 스팬)."""
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)          # **bold**
    text = re.sub(r'\*(.+?)\*',     r'\1', text)           # *italic*
    text = re.sub(r'`(.+?)`',       r'\1', text)           # `code`
    text = re.sub(r'\[(.+?)\]\(.+?\)', r'\1', text)        # [link](url)
    text = re.sub(r'\[(.+?)\]\[.+?\]', r'\1', text)        # [link][ref]
    text = re.sub(r'\[SRC-\d+\]',   '', text)              # [SRC-NNN] 제거
    return text.strip()


def parse_table(lines: list[str]):
    """마크다운 표 파싱 → (headers, rows)."""
    headers, rows = [], []
    for i, line in enumerate(lines):
        line = line.strip()
        if not line.startswith("|"):
            break
        cells = [c.strip() for c in line.strip("|").split("|")]
        if i == 0:
            headers = [clean_inline(c) for c in cells]
        elif re.match(r'^[\-\s:|]+$', line.replace("|", "")):
            continue  # 구분 행
        else:
            rows.append([clean_inline(c) for c in cells])
    return headers, rows


def render_md_to_pdf(md_text: str, pdf: ReportPDF):
    lines = md_text.split("\n")
    i = 0
    in_code  = False
    code_buf = []
    bullet_num = {}   # depth → 현재 번호 (ordered list용)

    while i < len(lines):
        raw = lines[i]
        line = raw.rstrip()

        # ── 코드 블록 ────────────────────────────────────────────────
        if line.startswith("```"):
            if not in_code:
                in_code = True
                code_buf = []
            else:
                in_code = False
                pdf.render_code_block("\n".join(code_buf))
                code_buf = []
            i += 1
            continue

        if in_code:
            code_buf.append(line)
            i += 1
            continue

        # ── 표 ───────────────────────────────────────────────────────
        if line.startswith("|") and i + 1 < len(lines) and re.match(r'^[\|\-\s:]+$', lines[i+1]):
            table_lines = []
            while i < len(lines) and lines[i].startswith("|"):
                table_lines.append(lines[i])
                i += 1
            headers, rows = parse_table(table_lines)
            if headers:
                pdf.render_table(headers, rows)
            continue

        # ── 수평선 ──────────────────────────────────────────────────
        if re.match(r'^-{3,}$|^\*{3,}$|^_{3,}$', line.strip()):
            pdf.render_hr()
            i += 1
            continue

        # ── 헤딩 ────────────────────────────────────────────────────
        m = re.match(r'^(#{1,4})\s+(.+)', line)
        if m:
            level = len(m.group(1))
            text  = clean_inline(m.group(2))
            pdf.render_heading(level, text)
            i += 1
            continue

        # ── 불릿 리스트 ──────────────────────────────────────────────
        m = re.match(r'^(\s*)([-*+])\s+(.+)', line)
        if m:
            depth = len(m.group(1)) // 2
            text  = clean_inline(m.group(3))
            pdf.render_bullet(text, depth)
            i += 1
            continue

        # ── 번호 리스트 ──────────────────────────────────────────────
        m = re.match(r'^(\s*)(\d+)\.\s+(.+)', line)
        if m:
            depth = len(m.group(1)) // 2
            num   = int(m.group(2))
            text  = clean_inline(m.group(3))
            pdf.render_numbered(num, text, depth)
            i += 1
            continue

        # ── 인용 블록 ────────────────────────────────────────────────
        if line.startswith("> "):
            text = clean_inline(line[2:])
            pdf.render_blockquote(text)
            i += 1
            continue

        # ── 빈 줄 ───────────────────────────────────────────────────
        if not line.strip():
            pdf.ln(1.5)
            i += 1
            continue

        # ── 일반 단락 ────────────────────────────────────────────────
        text = clean_inline(line)
        if text:
            pdf.render_paragraph(text)
        i += 1


# ── 메인 ─────────────────────────────────────────────────────────────────

def main():
    md_text = MD_PATH.read_text(encoding="utf-8")

    # 메타 정보 추출
    meta = {
        "작성일":    "2026-04-14",
        "버전":      "1.0 (팩트체크 반영 최종본)",
        "대상 독자": "CFO, 회계팀장, 외부감사인, 투자자, 정책 담당자",
        "A등급": 11, "B등급": 10, "C등급": 6, "총출처": 27,
    }

    pdf = ReportPDF()

    # 1. 표지
    pdf.cover_page(meta)

    # 2. 본문 (첫 번째 줄 제목은 표지로 대체했으므로 스킵)
    body_text = re.sub(r'^#\s+.+\n', '', md_text, count=1)
    # 메타 줄(작성일/작성팀/버전...) 제거
    body_text = re.sub(r'^\*\*.+?\*\*:.+\n', '', body_text, flags=re.MULTILINE, count=6)

    pdf.add_page()
    render_md_to_pdf(body_text, pdf)

    # 3. 저장
    pdf.output(str(PDF_PATH))
    print(f"✓ PDF 저장 완료: {PDF_PATH}")
    print(f"  총 {pdf.page} 페이지")


if __name__ == "__main__":
    main()
