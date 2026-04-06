"""
edgar_nlp.py — Module C: EDGAR 10-K 다운로드 + NLP 분석

신뢰성 개선:
- Loughran-McDonald (LM 2011, JoF) 금융 사전 기반 감성 분석 (VADER 대비 10-K에 적합)
- 키워드 빈도 정규화 (10,000단어당 등장 횟수)
- 전체 암호화폐 관련 단락 합산 → 실제 섹션 길이 측정
- 단락 수준(paragraph-level) 추출로 맥락 보존
"""
import os
import re
import time
import requests
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import streamlit as st
from bs4 import BeautifulSoup

# NLTK VADER (보조 지표로 유지)
import ssl
import nltk

try:
    from nltk.sentiment.vader import SentimentIntensityAnalyzer
    _sid = SentimentIntensityAnalyzer()
except LookupError:
    ssl._create_default_https_context = ssl._create_unverified_context
    nltk.download("vader_lexicon", quiet=True)
    from nltk.sentiment.vader import SentimentIntensityAnalyzer
    _sid = SentimentIntensityAnalyzer()

CACHE_DIR = "data/cache"

COMPANIES = {
    "MSTR": {"name": "MicroStrategy", "cik": "0001050446"},
    "TSLA": {"name": "Tesla",         "cik": "0001318605"},
    "COIN": {"name": "Coinbase",      "cik": "0001679273"},
}

KEYWORDS = [
    "digital asset", "cryptocurrency", "bitcoin", "fair value",
    "impairment", "risk", "volatility", "regulation", "disclosure",
]

# ── Loughran-McDonald (LM 2011) 금융 사전 ─────────────────────────────────────
# 출처: Loughran & McDonald (2011), "When Is a Liability Not a Liability?",
#       Journal of Finance 66(1), pp. 35-65.
# 10-K 공시에 최적화된 금융 감성 분석의 학술 표준.
# 전체 사전 (2,355개 부정어 / 354개 긍정어) 중 핵심 단어 수록.

LM_NEGATIVE = {
    "abandon", "abnormal", "adverse", "allegation", "breach", "burden",
    "claim", "complaint", "concern", "conflict", "corrupt", "damage",
    "decline", "decrease", "deficiency", "delinquent", "deny", "deteriorate",
    "difficult", "difficulty", "dispute", "doubt", "downgrade", "downward",
    "erroneous", "error", "fail", "failure", "false", "fine", "foreclose",
    "forfeit", "fraud", "harm", "hinder", "impair", "impairment",
    "inadequate", "insufficient", "invalid", "investigation", "irreparable",
    "lack", "late", "lawsuit", "liability", "limitation", "liquidate",
    "litigation", "loss", "losses", "lower", "manipulate", "material weakness",
    "misappropriate", "misconduct", "misstate", "misstatement", "negative",
    "noncompliance", "obstacle", "penalty", "poor", "problem", "prohibit",
    "restate", "restatement", "restrict", "risk", "sanction", "serious",
    "severe", "shortage", "shortfall", "significant", "substandard",
    "suspend", "terminate", "uncertain", "uncertainty", "unable",
    "unfavorable", "unforeseen", "violation", "volatile", "volatility",
    "weak", "weakness", "worsen", "writedown", "write-down", "write-off",
}

LM_POSITIVE = {
    "achieve", "advantage", "beneficial", "benefit", "best", "capable",
    "consistent", "effective", "effectively", "efficient", "enhance",
    "excellent", "exceed", "favorable", "gain", "gains", "good", "grow",
    "growth", "high", "improve", "improvement", "increase", "innovative",
    "leading", "optimal", "outperform", "positive", "profit", "profitable",
    "profitability", "progress", "record", "recover", "recovery", "strong",
    "strength", "succeed", "success", "successful", "superior", "upward",
}


def _lm_sentiment(text: str) -> dict:
    """
    Loughran-McDonald 금융 사전 기반 감성 점수 계산.
    compound = (pos - neg) / (pos + neg + 1e-9), 범위 [-1, 1]
    """
    tokens = re.findall(r"\b[a-z]+(?:-[a-z]+)?\b", text.lower())
    n_pos = sum(1 for t in tokens if t in LM_POSITIVE)
    n_neg = sum(1 for t in tokens if t in LM_NEGATIVE)
    total = len(tokens) or 1
    compound = (n_pos - n_neg) / (n_pos + n_neg + 1e-9)
    return {
        "lm_pos_ratio": round(n_pos / total, 4),
        "lm_neg_ratio": round(n_neg / total, 4),
        "lm_compound":  round(float(np.clip(compound, -1, 1)), 4),
        "lm_pos_count": n_pos,
        "lm_neg_count": n_neg,
    }


# ── EDGAR 데이터 파이프라인 ────────────────────────────────────────────────────

def _cache_path(ticker: str, year: int) -> str:
    os.makedirs(CACHE_DIR, exist_ok=True)
    return os.path.join(CACHE_DIR, f"{ticker}_{year}.txt")


def _search_10k_filings(cik: str, year_start: int, year_end: int) -> list[dict]:
    results = []
    try:
        url = "https://data.sec.gov/submissions/CIK{}.json".format(cik.lstrip("0").zfill(10))
        resp = requests.get(url, headers={"User-Agent": "academic-research contact@example.com"}, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        filings = data.get("filings", {}).get("recent", {})
        forms         = filings.get("form", [])
        dates         = filings.get("filingDate", [])
        accessions    = filings.get("accessionNumber", [])
        primary_docs  = filings.get("primaryDocument", [])

        for form, date, acc, doc in zip(forms, dates, accessions, primary_docs):
            if form != "10-K":
                continue
            yr = int(date[:4])
            if year_start <= yr <= year_end:
                results.append({
                    "year": yr, "date": date,
                    "accession": acc.replace("-", ""), "document": doc,
                })
    except Exception as e:
        st.warning(f"EDGAR 조회 실패: {e}")
    return results


def _download_filing_text(cik: str, accession: str, document: str) -> str:
    cik_clean = cik.lstrip("0")
    url = f"https://www.sec.gov/Archives/edgar/data/{cik_clean}/{accession}/{document}"
    try:
        resp = requests.get(
            url,
            headers={"User-Agent": "academic-research contact@example.com"},
            timeout=30,
        )
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")
        for tag in soup(["script", "style", "table"]):
            tag.decompose()
        return soup.get_text(separator=" ", strip=True)
    except Exception:
        return ""


def _extract_crypto_paragraphs(text: str) -> list[str]:
    """
    암호화폐 관련 키워드가 포함된 문단(단락) 전체를 추출.
    단순 3000자 창(window) 방식 대신 문단 단위로 분리해 맥락 보존.
    """
    crypto_pattern = re.compile(
        r"(?:digital asset|cryptocurrency|bitcoin|virtual currency|crypto)", re.IGNORECASE
    )
    # 빈 줄 또는 2개 이상 공백으로 단락 분리
    paragraphs = re.split(r"\n{2,}|\s{3,}", text)
    matched = [p.strip() for p in paragraphs if crypto_pattern.search(p) and len(p.strip()) > 50]
    return matched


def _analyze_text(full_text: str, year: int) -> dict:
    words = re.findall(r"\b[a-zA-Z]+\b", full_text)
    total_words = len(words) or 1
    text_lower = full_text.lower()

    # 암호화폐 관련 단락 추출
    crypto_paragraphs = _extract_crypto_paragraphs(full_text)
    section_text = " ".join(crypto_paragraphs)
    section_length = len(section_text)   # 실제 암호화폐 섹션 총 글자수

    row = {
        "year": year,
        "section_length": section_length,
        "num_crypto_paragraphs": len(crypto_paragraphs),
        "total_words": total_words,
        "excerpt": section_text[:2000] if section_text else "[관련 섹션 없음]",
    }

    # 절대 빈도 + 10,000단어당 정규화 빈도
    for kw in KEYWORDS:
        count = len(re.findall(re.escape(kw), text_lower))
        row[f"kw_{kw.replace(' ', '_')}"] = count
        row[f"nkw_{kw.replace(' ', '_')}"] = round(count / total_words * 10000, 2)

    # LM 금융 사전 감성 (전체 암호화폐 섹션 대상)
    lm = _lm_sentiment(section_text) if section_text else {
        "lm_pos_ratio": 0, "lm_neg_ratio": 0, "lm_compound": 0,
        "lm_pos_count": 0, "lm_neg_count": 0,
    }
    row.update(lm)

    # VADER 보조 지표 (짧은 문장 감성용)
    if section_text:
        vader = _sid.polarity_scores(section_text[:5000])
        row["vader_compound"]  = vader["compound"]
        row["vader_pos"]       = vader["pos"]
        row["vader_neg"]       = vader["neg"]
    else:
        row["vader_compound"] = 0
        row["vader_pos"] = 0
        row["vader_neg"] = 0

    # 편의상 기존 필드명 유지 (app.py 호환)
    row["sentiment_compound"] = row["lm_compound"]
    row["sentiment_pos"] = row["lm_pos_ratio"]
    row["sentiment_neg"] = row["lm_neg_ratio"]

    return row


def _sample_data(ticker: str, year_start: int, year_end: int) -> pd.DataFrame:
    """API 실패 시 사용하는 합리적인 샘플 데이터 (LM 지표 포함)."""
    rng = np.random.default_rng(hash(ticker) % (2**32))
    years = list(range(year_start, year_end + 1))

    base = {
        "MSTR": {"digital_asset": 15, "bitcoin": 20, "fair_value": 8,  "lm": 0.05},
        "TSLA": {"digital_asset": 5,  "bitcoin": 8,  "fair_value": 4,  "lm": 0.02},
        "COIN": {"digital_asset": 40, "bitcoin": 35, "fair_value": 20, "lm": 0.08},
    }.get(ticker, {"digital_asset": 10, "bitcoin": 10, "fair_value": 5, "lm": 0.03})

    rows = []
    for yr in years:
        mult = 1 + (yr - year_start) * 0.35
        total_words = int(rng.integers(80000, 150000))
        da_count = int(base["digital_asset"] * mult + rng.integers(0, 5))
        bk_count = int(base["bitcoin"] * mult + rng.integers(0, 5))
        fv_count = int(base["fair_value"] * mult + rng.integers(0, 3))
        imp_count = int(rng.integers(2, 8) * mult)
        rows.append({
            "year": yr,
            "section_length":         int(rng.integers(5000, 30000) * mult),
            "num_crypto_paragraphs":  int(rng.integers(5, 20) * mult),
            "total_words":            total_words,
            "excerpt":                f"[샘플 데이터] {ticker} {yr}년 10-K (EDGAR 연결 필요)",
            # 절대 빈도
            "kw_digital_asset":   da_count,
            "kw_cryptocurrency":  int(rng.integers(3, 10) * mult),
            "kw_bitcoin":         bk_count,
            "kw_fair_value":      fv_count,
            "kw_impairment":      imp_count,
            "kw_risk":            int(rng.integers(10, 30) * mult),
            "kw_volatility":      int(rng.integers(3, 10) * mult),
            "kw_regulation":      int(rng.integers(2, 8) * mult),
            "kw_disclosure":      int(rng.integers(1, 6) * mult),
            # 정규화 빈도 (10,000단어당)
            "nkw_digital_asset":  round(da_count / total_words * 10000, 2),
            "nkw_bitcoin":        round(bk_count / total_words * 10000, 2),
            "nkw_fair_value":     round(fv_count / total_words * 10000, 2),
            "nkw_impairment":     round(imp_count / total_words * 10000, 2),
            # LM 감성
            "lm_compound":    round(float(base["lm"] + rng.uniform(-0.05, 0.05)), 4),
            "lm_pos_ratio":   round(float(rng.uniform(0.01, 0.04)), 4),
            "lm_neg_ratio":   round(float(rng.uniform(0.03, 0.08)), 4),
            "lm_pos_count":   int(rng.integers(50, 200)),
            "lm_neg_count":   int(rng.integers(100, 400)),
            # VADER 보조
            "vader_compound": round(float(rng.uniform(-0.1, 0.2)), 3),
            "vader_pos":      round(float(rng.uniform(0.05, 0.15)), 3),
            "vader_neg":      round(float(rng.uniform(0.02, 0.10)), 3),
            # 호환용
            "sentiment_compound": round(float(base["lm"] + rng.uniform(-0.05, 0.05)), 4),
            "sentiment_pos":      round(float(rng.uniform(0.01, 0.04)), 4),
            "sentiment_neg":      round(float(rng.uniform(0.03, 0.08)), 4),
        })
    return pd.DataFrame(rows)


@st.cache_data(ttl=86400, show_spinner=False)
def fetch_company_data(ticker: str, year_start: int = 2019, year_end: int = 2024) -> pd.DataFrame:
    info = COMPANIES[ticker]
    cik  = info["cik"]

    filings = _search_10k_filings(cik, year_start, year_end)
    if not filings:
        return _sample_data(ticker, year_start, year_end)

    rows = []
    progress = st.progress(0, text=f"{ticker} 10-K 분석 중...")
    for i, f in enumerate(filings):
        cache = _cache_path(ticker, f["year"])
        if os.path.exists(cache):
            with open(cache, "r", encoding="utf-8") as fp:
                text = fp.read()
        else:
            text = _download_filing_text(cik, f["accession"], f["document"])
            if text:
                with open(cache, "w", encoding="utf-8") as fp:
                    fp.write(text)
            time.sleep(0.2)

        if text:
            rows.append(_analyze_text(text, f["year"]))
        progress.progress((i + 1) / len(filings), text=f"{ticker} {f['year']}년 완료")

    progress.empty()
    if not rows:
        return _sample_data(ticker, year_start, year_end)
    return pd.DataFrame(rows).sort_values("year").reset_index(drop=True)


# ── Charts ────────────────────────────────────────────────────────────────────

def chart_keyword_heatmap(df: pd.DataFrame, ticker: str) -> go.Figure:
    """정규화 빈도(10,000단어당) 히트맵."""
    nkw_cols = [c for c in df.columns if c.startswith("nkw_")]
    if not nkw_cols:
        # 절대 빈도 fallback
        nkw_cols = [c for c in df.columns if c.startswith("kw_")]
    labels = [c.replace("nkw_", "").replace("kw_", "").replace("_", " ") for c in nkw_cols]
    matrix = df[nkw_cols].values.T.tolist()

    fig = go.Figure(go.Heatmap(
        z=matrix,
        x=[str(y) for y in df["year"]],
        y=labels,
        colorscale="YlOrRd",
        text=[[f"{v:.1f}" for v in row] for row in matrix],
        texttemplate="%{text}",
        showscale=True,
        colorbar=dict(title="10,000단어당"),
    ))
    fig.update_layout(
        title=f"{ticker} — 키워드 정규화 빈도 히트맵 (10,000단어당, LM 기준)",
        height=420,
        plot_bgcolor="#0E1117", paper_bgcolor="#0E1117",
        font_color="white",
        xaxis_title="연도", yaxis_title="키워드",
    )
    return fig


def chart_sentiment(df: pd.DataFrame, ticker: str) -> go.Figure:
    """LM 감성 vs VADER 감성 비교 차트."""
    fig = go.Figure()

    # LM compound
    fig.add_trace(go.Scatter(
        x=df["year"], y=df["lm_compound"],
        name="LM Compound (금융 사전)", mode="lines+markers",
        line=dict(color="#F4845F", width=3),
        marker=dict(size=10, symbol="circle"),
    ))

    # LM pos/neg ratio
    fig.add_trace(go.Bar(
        x=df["year"], y=df["lm_pos_ratio"],
        name="LM 긍정 비율", marker_color="#2ECC71", opacity=0.5,
        yaxis="y2",
    ))
    fig.add_trace(go.Bar(
        x=df["year"], y=[-v for v in df["lm_neg_ratio"]],
        name="LM 부정 비율 (반전)", marker_color="#E74C3C", opacity=0.5,
        yaxis="y2",
    ))

    # VADER 보조
    if "vader_compound" in df.columns:
        fig.add_trace(go.Scatter(
            x=df["year"], y=df["vader_compound"],
            name="VADER Compound (참고용)", mode="lines+markers",
            line=dict(color="#6EA8D0", dash="dot", width=1.5),
            marker=dict(size=6),
        ))

    fig.add_hline(y=0, line_dash="dash", line_color="gray")
    fig.update_layout(
        title=f"{ticker} — Loughran-McDonald 금융 감성 분석 (10-K 기준)",
        height=420,
        plot_bgcolor="#0E1117", paper_bgcolor="#0E1117",
        font_color="white",
        barmode="relative",
        yaxis=dict(title="LM Compound Score [-1, 1]", side="left"),
        yaxis2=dict(title="LM 긍/부정 비율", overlaying="y", side="right"),
        xaxis=dict(tickmode="linear", dtick=1),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    return fig


def chart_disclosure_length(df: pd.DataFrame, ticker: str) -> go.Figure:
    """실제 암호화폐 섹션 길이 + 단락 수 이중 축 차트."""
    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=[str(y) for y in df["year"]],
        y=df["section_length"],
        name="섹션 총 글자수",
        marker_color="#6EA8D0",
        opacity=0.8,
    ))

    if "num_crypto_paragraphs" in df.columns:
        fig.add_trace(go.Scatter(
            x=[str(y) for y in df["year"]],
            y=df["num_crypto_paragraphs"],
            name="관련 단락 수",
            mode="lines+markers",
            line=dict(color="#F4845F", width=2),
            marker=dict(size=8),
            yaxis="y2",
        ))

    fig.update_layout(
        title=f"{ticker} — 암호화폐 공시 분량 (실제 단락 합산)",
        height=360,
        plot_bgcolor="#0E1117", paper_bgcolor="#0E1117",
        font_color="white",
        yaxis=dict(title="총 글자수", side="left"),
        yaxis2=dict(title="단락 수", overlaying="y", side="right"),
        xaxis_title="연도",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    return fig


def chart_lm_wordcount(df: pd.DataFrame, ticker: str) -> go.Figure:
    """LM 긍정어 / 부정어 절대 개수 누적 막대."""
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=[str(y) for y in df["year"]], y=df["lm_pos_count"],
        name="LM 긍정어 수", marker_color="#2ECC71",
    ))
    fig.add_trace(go.Bar(
        x=[str(y) for y in df["year"]], y=df["lm_neg_count"],
        name="LM 부정어 수", marker_color="#E74C3C",
    ))
    fig.update_layout(
        title=f"{ticker} — LM 금융 사전 긍/부정어 등장 횟수 추이",
        barmode="group", height=340,
        plot_bgcolor="#0E1117", paper_bgcolor="#0E1117",
        font_color="white", yaxis_title="단어 수",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    return fig
