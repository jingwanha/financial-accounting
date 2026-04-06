"""
config.py — 프로젝트 전역 설정
OpenAI 모델, 분석 파라미터 등을 여기서 관리합니다.
"""

# ── OpenAI 설정 ───────────────────────────────────────────────────────────────
OPENAI_MODEL = "gpt-5.4"  # 변경 가능: "gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo"
OPENAI_MAX_TOKENS = 1000
OPENAI_TEMPERATURE = 0.3

# ── 분석 파라미터 ──────────────────────────────────────────────────────────────
BTC_HISTORY_DAYS = 2000  # yfinance BTC 이력 조회 기간 (일)
EDGAR_YEAR_START = 2019
EDGAR_YEAR_END = 2024

# ── 기업 목록 ──────────────────────────────────────────────────────────────────
TICKERS = ["MSTR", "TSLA", "COIN"]
