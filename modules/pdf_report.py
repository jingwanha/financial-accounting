"""
pdf_report.py — GPT 리포트 + 차트를 PDF로 변환 (한글 지원)
fpdf2 + plotly kaleido 사용
NanumGothic TTF 자동 다운로드 (한글 렌더링)
"""
import io
import os
import re
import tempfile
import requests
from datetime import datetime
import plotly.graph_objects as go


# ── 한글 폰트 확보 ────────────────────────────────────────────────────────────

def _get_korean_font() -> tuple[str | None, str | None]:
    """
    (regular_path, bold_path) 반환.
    캐시 없으면 NanumGothic을 GitHub에서 다운로드.
    """
    cache_dir = os.path.join("data", "cache")
    os.makedirs(cache_dir, exist_ok=True)
    reg_path  = os.path.join(cache_dir, "NanumGothic-Regular.ttf")
    bold_path = os.path.join(cache_dir, "NanumGothic-Bold.ttf")

    base_url = "https://raw.githubusercontent.com/google/fonts/main/ofl/nanumgothic"
    headers  = {"User-Agent": "Mozilla/5.0"}

    for path, fname in [(reg_path, "NanumGothic-Regular.ttf"),
                        (bold_path, "NanumGothic-Bold.ttf")]:
        if not os.path.exists(path):
            try:
                r = requests.get(f"{base_url}/{fname}", headers=headers, timeout=20)
                r.raise_for_status()
                with open(path, "wb") as f:
                    f.write(r.content)
            except Exception:
                pass

    return (
        reg_path  if os.path.exists(reg_path)  else None,
        bold_path if os.path.exists(bold_path) else None,
    )


# ── Plotly → PNG ─────────────────────────────────────────────────────────────

def _fig_to_png_bytes(fig: go.Figure, width: int = 900, height: int = 380) -> bytes:
    try:
        return fig.to_image(format="png", width=width, height=height, scale=1.5)
    except Exception:
        return b""


# ── 마크다운 파싱 헬퍼 ────────────────────────────────────────────────────────

def _strip_md(text: str) -> str:
    """마크다운 기호 제거 (PDF 텍스트용)."""
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
    text = re.sub(r"\*(.*?)\*", r"\1", text)
    text = re.sub(r"`(.*?)`", r"\1", text)
    return text.strip()


# ── PDF 생성 ──────────────────────────────────────────────────────────────────

def generate_pdf(
    report_text: str,
    title: str,
    charts: list[tuple[str, go.Figure]],
    subtitle: str = "KAIST 디지털금융 MBA · 재무회계 · Spring 2026",
) -> bytes:
    from fpdf import FPDF

    reg_font, bold_font = _get_korean_font()
    use_korean = reg_font is not None

    # ── FPDF 서브클래스 ───────────────────────────────────────────────────────
    class ReportPDF(FPDF):
        def setup_fonts(self):
            if use_korean:
                self.add_font("KR",  "",  reg_font)
                self.add_font("KRB", "",  bold_font or reg_font)
            self._kr = use_korean

        def kr(self, bold=False, size=10):
            """폰트 설정 헬퍼."""
            if self._kr:
                self.set_font("KRB" if bold else "KR", size=size)
            else:
                self.set_font("Helvetica", "B" if bold else "", size)

        def header(self):
            self.kr(bold=True, size=9)
            self.set_text_color(244, 132, 95)
            self.cell(0, 7, "ASC 350-60 Cryptocurrency Accounting Analysis | KAIST Digital Finance MBA", align="C")
            self.ln(3)
            self.set_draw_color(244, 132, 95)
            self.line(10, self.get_y(), 200, self.get_y())
            self.ln(2)

        def footer(self):
            self.set_y(-12)
            self.kr(size=8)
            self.set_text_color(150, 150, 150)
            self.cell(0, 8, f"Page {self.page_no()} | Generated {datetime.now().strftime('%Y-%m-%d')}", align="C")

    pdf = ReportPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.setup_fonts()
    pdf.add_page()

    # ── 표지 ──────────────────────────────────────────────────────────────────
    pdf.ln(10)
    pdf.kr(bold=True, size=17)
    pdf.set_text_color(244, 132, 95)
    pdf.multi_cell(0, 10, _strip_md(title), align="C")
    pdf.ln(4)
    pdf.kr(size=11)
    pdf.set_text_color(180, 180, 180)
    pdf.multi_cell(0, 7, subtitle, align="C")
    pdf.ln(2)
    pdf.kr(size=10)
    pdf.set_text_color(150, 150, 150)
    pdf.cell(0, 6, datetime.now().strftime("%Y년 %m월 %d일"), align="C")
    pdf.ln(12)
    pdf.set_draw_color(244, 132, 95)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(10)

    # ── AI 리포트 섹션 헤더 ────────────────────────────────────────────────────
    pdf.set_fill_color(26, 31, 46)
    pdf.kr(bold=True, size=12)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 9, "  AI Analysis Report", fill=True)
    pdf.ln(8)

    # ── 텍스트 렌더링 ─────────────────────────────────────────────────────────
    for line in report_text.split("\n"):
        raw = line.strip()
        if not raw:
            pdf.ln(3)
            continue

        if raw.startswith("### "):
            pdf.ln(2)
            pdf.kr(bold=True, size=11)
            pdf.set_text_color(244, 132, 95)
            pdf.multi_cell(0, 7, _strip_md(raw[4:]))
            pdf.kr(size=10)
            pdf.set_text_color(220, 220, 220)

        elif raw.startswith("## "):
            pdf.ln(3)
            # 배경 강조 박스
            pdf.set_fill_color(20, 40, 70)
            pdf.kr(bold=True, size=12)
            pdf.set_text_color(110, 168, 208)
            pdf.multi_cell(0, 8, "  " + _strip_md(raw[3:]), fill=True)
            pdf.kr(size=10)
            pdf.set_text_color(220, 220, 220)

        elif raw.startswith("# "):
            pdf.ln(5)
            # 강조 박스
            pdf.set_fill_color(40, 20, 10)
            pdf.set_draw_color(244, 132, 95)
            y_before = pdf.get_y()
            pdf.kr(bold=True, size=14)
            pdf.set_text_color(244, 132, 95)
            pdf.multi_cell(0, 9, "  " + _strip_md(raw[2:]), fill=True)
            pdf.set_draw_color(244, 132, 95)
            pdf.line(10, y_before, 10, pdf.get_y())
            pdf.kr(size=10)
            pdf.set_text_color(220, 220, 220)

        elif raw.startswith("- ") or raw.startswith("• "):
            pdf.set_x(16)
            pdf.kr(size=10)
            pdf.set_text_color(200, 200, 200)
            # 숫자 포함 줄은 오렌지로 강조
            content = _strip_md(raw[2:])
            has_number = bool(re.search(r'\$[\d,]+|\d+\.?\d*%|\d+\.?\d*배', content))
            if has_number:
                pdf.set_text_color(244, 180, 120)
            pdf.multi_cell(0, 6, u"\u25b8  " + content)
            pdf.set_text_color(220, 220, 220)

        elif raw.startswith("**") and raw.endswith("**"):
            pdf.kr(bold=True, size=10)
            pdf.set_text_color(255, 215, 0)
            pdf.multi_cell(0, 6, _strip_md(raw))
            pdf.kr(size=10)
            pdf.set_text_color(220, 220, 220)

        else:
            pdf.kr(size=10)
            content = _strip_md(raw)
            has_number = bool(re.search(r'\$[\d,]+|\d+\.?\d*%|\d+\.?\d*배|\d+\.?\d*x\b', content))
            pdf.set_text_color(244, 180, 120 if has_number else 220)
            pdf.multi_cell(0, 6, content)
            pdf.set_text_color(220, 220, 220)

    # ── 차트 삽입 ──────────────────────────────────────────────────────────────
    if charts:
        pdf.add_page()
        pdf.set_fill_color(26, 31, 46)
        pdf.kr(bold=True, size=12)
        pdf.set_text_color(110, 168, 208)
        pdf.cell(0, 9, "  Supporting Charts & Data Visualization", fill=True)
        pdf.ln(8)

        for chart_title, fig in charts:
            png_bytes = _fig_to_png_bytes(fig)
            if not png_bytes:
                continue
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                tmp.write(png_bytes)
                tmp_path = tmp.name
            try:
                pdf.kr(bold=True, size=9)
                pdf.set_text_color(244, 132, 95)
                pdf.multi_cell(0, 6, _strip_md(chart_title))
                pdf.ln(1)
                img_w = 180
                img_h = img_w * 380 / 900
                if pdf.get_y() + img_h > pdf.h - 20:
                    pdf.add_page()
                pdf.image(tmp_path, x=15, w=img_w, h=img_h)
                pdf.ln(6)
            finally:
                os.unlink(tmp_path)

    return bytes(pdf.output())
