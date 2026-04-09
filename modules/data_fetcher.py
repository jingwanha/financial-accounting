"""
data_fetcher.py — BTC 가격(yfinance) + CoinGecko 현재가 + yfinance 주가 유틸
"""

import requests
import pandas as pd
import numpy as np
import streamlit as st

COINGECKO_BASE = "https://api.coingecko.com/api/v3"
_CG_HEADERS = {"Accept": "application/json"}


# ── BTC 일별 가격 (yfinance, 무료 전체 이력) ──────────────────────────────────


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_btc_price_history(days: int = 1825) -> pd.DataFrame:
    """
    yfinance로 BTC-USD 일별 종가 조회.
    CoinGecko 무료 API는 365일로 제한되어 있어 yfinance 사용.
    days 파라미터는 대략적 기간 힌트로만 사용.
    """
    try:
        import yfinance as yf

        period = "max" if days >= 1800 else ("2y" if days >= 700 else "1y")
        df = yf.download("BTC-USD", period=period, progress=False, auto_adjust=True)
        if df.empty:
            raise ValueError("yfinance 빈 응답")
        df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
        price_col = "Close"
        out = df[[price_col]].copy()
        out.columns = ["price"]
        out.index = pd.to_datetime(out.index).tz_localize(None).normalize()
        out = out.dropna().sort_index()
        return out
    except Exception as e:
        st.warning(f"yfinance BTC 조회 실패: {e}. 하드코딩 데이터로 대체합니다.")
        return _btc_fallback()


@st.cache_data(ttl=300, show_spinner=False)
def fetch_btc_current_price() -> float:
    """CoinGecko로 현재 BTC 가격 조회 (실시간, 365일 제한 없음)."""
    try:
        resp = requests.get(
            f"{COINGECKO_BASE}/simple/price",
            params={"ids": "bitcoin", "vs_currencies": "usd"},
            headers=_CG_HEADERS,
            timeout=10,
        )
        resp.raise_for_status()
        return float(resp.json()["bitcoin"]["usd"])
    except Exception:
        return 0.0


def _btc_fallback() -> pd.DataFrame:
    """분기말 BTC 가격 하드코딩 (API 전체 실패 시 최후 수단)."""
    rows = [
        ("2019-12-31", 7193),
        ("2020-03-31", 6424),
        ("2020-06-30", 9137),
        ("2020-09-30", 10784),
        ("2020-12-31", 28990),
        ("2021-03-31", 58726),
        ("2021-06-30", 35045),
        ("2021-09-30", 43791),
        ("2021-12-31", 46306),
        ("2022-03-31", 44350),
        ("2022-06-30", 19784),
        ("2022-09-30", 19432),
        ("2022-12-31", 16547),
        ("2023-03-31", 28478),
        ("2023-06-30", 30477),
        ("2023-09-30", 26969),
        ("2023-12-31", 42265),
        ("2024-03-31", 71240),
        ("2024-06-30", 62678),
        ("2024-09-30", 63301),
        ("2024-12-31", 93429),
    ]
    df = pd.DataFrame(rows, columns=["date", "price"])
    df["date"] = pd.to_datetime(df["date"])
    return df.set_index("date")


def get_quarter_end_price(df_prices: pd.DataFrame, date_str: str) -> float:
    """주어진 날짜에 가장 가까운 BTC 가격 반환."""
    target = pd.Timestamp(date_str)
    if target in df_prices.index:
        return float(df_prices.loc[target, "price"])
    idx = df_prices.index.get_indexer([target], method="nearest")
    return float(df_prices.iloc[idx[0]]["price"])


# ── 대용량 일별 분석용 ──────────────────────────────────────────────────────────


def compute_daily_eps_series(
    btc_df: pd.DataFrame, holdings: float, shares: float, cost_basis: float
) -> pd.DataFrame:
    """
    일별 BTC 가격으로 연속 EPS 시계열 계산.
    holdings: 현재 보유 BTC 수량
    shares: 발행주식수
    cost_basis: 평균 취득단가
    반환: date, btc_price, fair_value, unrealized_pnl, daily_eps_delta
    """
    df = btc_df.copy()
    df["fair_value"] = df["price"] * holdings
    df["unrealized_pnl"] = (df["price"] - cost_basis) * holdings
    df["daily_eps_impact"] = df["price"].diff() * holdings / shares
    df["cumulative_eps_impact"] = df["unrealized_pnl"] / shares
    df = df.dropna()
    return df


def compute_rolling_volatility(btc_df: pd.DataFrame, window: int = 30) -> pd.DataFrame:
    """BTC 일별 수익률 기반 롤링 변동성 계산."""
    df = btc_df.copy()
    df["returns"] = df["price"].pct_change()
    df[f"vol_{window}d"] = df["returns"].rolling(window).std() * np.sqrt(365) * 100
    return df.dropna()


# ── yfinance 주가 ──────────────────────────────────────────────────────────────


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_stock_history(ticker: str, period: str = "5y") -> pd.DataFrame:
    """주가 데이터 (MSTR, TSLA, COIN)."""
    try:
        import yfinance as yf

        df = yf.download(ticker, period=period, progress=False, auto_adjust=True)
        if df.empty:
            return pd.DataFrame()
        df.index = pd.to_datetime(df.index).tz_localize(None).normalize()
        df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
        return df[["Close", "Volume"]].rename(columns={"Close": "close"})
    except Exception as e:
        st.warning(f"{ticker} 주가 조회 실패: {e}")
        return pd.DataFrame()
