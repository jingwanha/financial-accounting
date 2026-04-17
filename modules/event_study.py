"""
event_study.py — 이벤트 연구: ASC 350-60 발표(2023-12-13)의 주가 영향
대상: MSTR, Block(SQ)
세 가지 벤치마크 모델: (1) S&P 500  (2) BTC  (3) S&P 500 + BTC 다요인

의존성: numpy, pandas, plotly, streamlit, yfinance (statsmodels/scipy 불필요)
"""

import math
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

# ══════════════════════════════════════════════════════════════════════════════
# 상수
# ══════════════════════════════════════════════════════════════════════════════

EVENT_DATE = pd.Timestamp("2023-12-13")

TICKER_INFO = {
    "MSTR": {
        "label": "MicroStrategy (MSTR)",
        "color": "#6EA8D0",
        "description": "BTC 대규모 보유 기업. ASC 350-60 영향이 가장 큼.",
    },
    "SQ": {
        "label": "Block (SQ/XYZ)",
        "color": "#00D632",
        "description": "핀테크 기업. BTC 보유 비중 ~1.6%. FY2023 조기 적용.",
    },
}

MODEL_CONFIGS = {
    "sp500": {
        "label": "S&P 500 시장모형",
        "color": "#6EA8D0",
        "est_start": "2023-06-01",
        "est_end": "2023-12-01",
        "win_start": "2023-11-13",
        "win_end": "2024-02-13",
        "factors": ["^GSPC"],
        "beta_labels": ["Beta (S&P 500)"],
    },
    "btc": {
        "label": "비트코인 벤치마크 모형",
        "color": "#F4845F",
        "est_start": "2023-10-01",
        "est_end": "2023-11-10",
        "win_start": "2023-11-13",
        "win_end": "2024-02-13",
        "factors": ["BTC-USD"],
        "beta_labels": ["Beta (BTC)"],
    },
    "multi": {
        "label": "다요인 모형 (S&P 500 + BTC)",
        "color": "#9B59B6",
        "est_start": "2023-10-01",
        "est_end": "2023-11-30",
        "win_start": "2023-11-13",
        "win_end": "2024-02-13",
        "factors": ["^GSPC", "BTC-USD"],
        "beta_labels": ["Beta (S&P 500)", "Beta (BTC)"],
    },
}

# ══════════════════════════════════════════════════════════════════════════════
# 데이터 수집
# ══════════════════════════════════════════════════════════════════════════════


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_event_study_data() -> pd.DataFrame:
    """
    MSTR, SQ, BTC-USD, ^GSPC의 일별 종가를 yfinance로 다운로드하고
    일별 수익률 DataFrame을 반환한다.
    columns: ["MSTR", "SQ", "BTC-USD", "^GSPC"]
    index: DatetimeIndex (tz-naive)
    """
    try:
        import yfinance as yf

        raw = yf.download(
            ["MSTR", "SQ", "BTC-USD", "^GSPC"],
            start="2023-05-01",
            end="2024-03-01",
            progress=False,
        )

        # MultiIndex 컬럼 처리 (yfinance 버전에 따라 다름)
        if isinstance(raw.columns, pd.MultiIndex):
            close = raw["Close"].copy()
        else:
            close = raw.copy()

        # 컬럼명 정리
        close.columns = [c if isinstance(c, str) else c[0] for c in close.columns]

        # 필요한 컬럼만 선택
        needed = ["MSTR", "SQ", "BTC-USD", "^GSPC"]
        close = close[[c for c in needed if c in close.columns]]

        # 인덱스 tz 제거
        if hasattr(close.index, "tz") and close.index.tz is not None:
            close.index = close.index.tz_localize(None)
        close.index = close.index.normalize()

        returns = close.pct_change().dropna()
        return returns

    except Exception:
        return pd.DataFrame()


# ══════════════════════════════════════════════════════════════════════════════
# OLS 엔진 (pure numpy)
# ══════════════════════════════════════════════════════════════════════════════


def _norm_cdf(x: float) -> float:
    """표준정규분포 CDF — math.erfc 기반 (scipy 불필요)."""
    return 0.5 * math.erfc(-x / math.sqrt(2))


def _ols_fit(
    X: np.ndarray,
    y: np.ndarray,
) -> tuple:
    """
    상수항 포함 OLS 회귀분석 (numpy.linalg.lstsq).
    반환: (alpha, betas, r_squared, sigma_resid)
    """
    n = len(y)
    X_aug = np.column_stack([np.ones(n), X])
    k = X_aug.shape[1]

    coeffs, _, _, _ = np.linalg.lstsq(X_aug, y, rcond=None)
    alpha = float(coeffs[0])
    betas = coeffs[1:].tolist()

    y_hat = X_aug @ coeffs
    resid = y - y_hat
    ss_res = float(resid @ resid)
    ss_tot = float(((y - y.mean()) ** 2).sum())
    r_squared = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0
    sigma_resid = math.sqrt(ss_res / max(n - k, 1))

    return alpha, betas, r_squared, sigma_resid


# ══════════════════════════════════════════════════════════════════════════════
# 모델 계산
# ══════════════════════════════════════════════════════════════════════════════


def compute_model_results(
    returns: pd.DataFrame,
    model_key: str,
    ticker: str = "MSTR",
    est_start: str = None,
    est_end: str = None,
    win_start: str = None,
    win_end: str = None,
) -> dict:
    """
    하나의 모델(sp500 / btc / multi)에 대해 추정 및 이벤트 윈도우 분석을 수행한다.
    ticker: 분석 대상 종목 (예: "MSTR", "SQ")
    반환 dict 키:
        alpha, betas, r_squared, sigma_resid,
        event_window (DataFrame: actual/expected/AR/CAR/T_stat/P_value),
        ar_event_day, t_stat_event, p_value_event,
        model_label, model_color, n_est_obs, ticker
    """
    cfg = MODEL_CONFIGS[model_key]
    factors = cfg["factors"]

    est_s = est_start or cfg["est_start"]
    est_e = est_end or cfg["est_end"]
    win_s = win_start or cfg["win_start"]
    win_e = win_end or cfg["win_end"]

    # 추정 기간 OLS
    est_data = returns.loc[est_s:est_e].dropna(subset=[ticker] + factors)
    X_est = est_data[factors].values
    y_est = est_data[ticker].values

    alpha, betas, r_squared, sigma_resid = _ols_fit(X_est, y_est)

    # 이벤트 윈도우
    win_data = returns.loc[win_s:win_e].dropna(subset=[ticker] + factors).copy()

    # 기대 수익률: alpha + sum(beta_i * factor_i)
    expected = np.full(len(win_data), alpha)
    for beta, factor in zip(betas, factors):
        expected += beta * win_data[factor].values

    win_data["actual"] = win_data[ticker].values
    win_data["expected"] = expected
    win_data["AR"] = win_data["actual"] - win_data["expected"]
    win_data["CAR"] = win_data["AR"].cumsum()
    win_data["T_stat"] = win_data["AR"] / sigma_resid if sigma_resid > 0 else 0.0
    win_data["P_value"] = win_data["T_stat"].apply(
        lambda t: 2 * (1 - _norm_cdf(abs(t)))
    )

    # 이벤트 당일 값
    ar_event = float("nan")
    t_event = float("nan")
    p_event = float("nan")

    if EVENT_DATE in win_data.index:
        row = win_data.loc[EVENT_DATE]
        ar_event = float(row["AR"])
        t_event = float(row["T_stat"])
        p_event = float(row["P_value"])
    else:
        # 가장 가까운 거래일 탐색 (±2 영업일)
        for offset in [1, -1, 2, -2]:
            candidate = EVENT_DATE + pd.tseries.offsets.BusinessDay(offset)
            if candidate in win_data.index:
                row = win_data.loc[candidate]
                ar_event = float(row["AR"])
                t_event = float(row["T_stat"])
                p_event = float(row["P_value"])
                break

    ticker_info = TICKER_INFO.get(ticker, {"label": ticker, "color": "#6EA8D0"})

    return {
        "alpha": alpha,
        "betas": betas,
        "beta_labels": cfg["beta_labels"],
        "r_squared": r_squared,
        "sigma_resid": sigma_resid,
        "event_window": win_data,
        "ar_event_day": ar_event,
        "t_stat_event": t_event,
        "p_value_event": p_event,
        "model_label": cfg["label"],
        "model_color": cfg["color"],
        "n_est_obs": len(est_data),
        "factors": factors,
        "ticker": ticker,
        "ticker_label": ticker_info["label"],
        "ticker_color": ticker_info["color"],
    }


def build_kpi_dict(results: dict) -> dict:
    """st.metric에 표시할 문자열 dict를 반환한다."""
    alpha = results["alpha"]
    betas = results["betas"]
    labels = results["beta_labels"]
    r2 = results["r_squared"]
    ar = results["ar_event_day"]
    t = results["t_stat_event"]
    p = results["p_value_event"]

    significant = not math.isnan(p) and p < 0.05

    return {
        "alpha_pct": f"{alpha:.4%}",
        "beta_labels": labels,
        "beta_values": [f"{b:.4f}" for b in betas],
        "r_squared_pct": f"{r2:.1%}",
        "ar_event_pct": f"{ar:.2%}" if not math.isnan(ar) else "N/A",
        "t_stat_str": f"{t:.4f}" if not math.isnan(t) else "N/A",
        "p_value_str": f"{p:.4f}" if not math.isnan(p) else "N/A",
        "significant": significant,
    }


# ══════════════════════════════════════════════════════════════════════════════
# Plotly 차트
# ══════════════════════════════════════════════════════════════════════════════

_DARK_LAYOUT = dict(
    template="plotly_dark",
    paper_bgcolor="#0d1117",
    plot_bgcolor="#0d1117",
    font=dict(family="'Noto Sans KR', sans-serif", color="#d0d0d0"),
    margin=dict(l=40, r=20, t=50, b=40),
)

_EVENT_DATE_STR = EVENT_DATE.strftime("%Y-%m-%d")


def _hex_to_rgba(hex_color: str, alpha: float = 0.13) -> str:
    """'#RRGGBB' → 'rgba(R,G,B,alpha)' 변환."""
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


def _add_event_line(fig, xref="x", yref="paper", show_label=True):
    """
    add_vline 대신 add_shape + add_annotation으로 이벤트 수직선을 그린다.
    (plotly의 add_vline + annotation이 날짜 문자열에서 TypeError를 일으키는 버그 우회)
    """
    fig.add_shape(
        type="line",
        x0=_EVENT_DATE_STR,
        x1=_EVENT_DATE_STR,
        y0=0,
        y1=1,
        xref=xref,
        yref=yref,
        line=dict(color="red", width=2, dash="dash"),
    )
    if show_label:
        fig.add_annotation(
            x=_EVENT_DATE_STR,
            y=0.98,
            xref=xref,
            yref=yref,
            text="ASC 350-60 발표",
            showarrow=False,
            font=dict(color="red", size=10),
            xanchor="left",
            yanchor="top",
            bgcolor="rgba(13,17,23,0.7)",
        )


def chart_daily_returns(returns: pd.DataFrame, ticker: str = "MSTR") -> go.Figure:
    """
    이벤트 윈도우(2023-11-13 ~ 2024-02-13) 내 대상 종목 / BTC / S&P 500
    일별 수익률 비교 라인 차트.
    """
    win = returns.loc["2023-11-13":"2024-02-13"]
    ti = TICKER_INFO.get(ticker, {"label": ticker, "color": "#6EA8D0"})

    fig = go.Figure()

    if ticker in win.columns:
        fig.add_trace(
            go.Scatter(
                x=win.index,
                y=win[ticker],
                name=ti["label"],
                line=dict(color=ti["color"], width=2),
            )
        )
    if "BTC-USD" in win.columns:
        fig.add_trace(
            go.Scatter(
                x=win.index,
                y=win["BTC-USD"],
                name="Bitcoin (BTC-USD)",
                line=dict(color="#F4845F", width=1.5),
                opacity=0.8,
            )
        )
    if "^GSPC" in win.columns:
        fig.add_trace(
            go.Scatter(
                x=win.index,
                y=win["^GSPC"],
                name="S&P 500 (^GSPC)",
                line=dict(color="#888888", width=1),
                opacity=0.6,
            )
        )

    _add_event_line(fig)
    fig.add_hline(y=0, line_color="#555", line_width=0.5)

    fig.update_layout(
        **_DARK_LAYOUT,
        title=f"일별 수익률 비교: {ti['label']} vs BTC vs S&P 500",
        yaxis=dict(tickformat=".1%", title="일별 수익률"),
        xaxis_title="날짜",
        legend=dict(orientation="h", y=1.08),
        height=380,
    )
    return fig


def chart_actual_vs_expected(results: dict) -> go.Figure:
    """
    2-패널 subplot:
      상단: 실제 수익률 vs 모델 기대 수익률
      하단: 비정상 수익률(AR) 막대 + 0 기준선
    """
    df = results["event_window"]
    color = results["model_color"]
    label = results["model_label"]

    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        subplot_titles=("실제 수익률 vs 기대 수익률", "비정상 수익률 (AR)"),
        row_heights=[0.6, 0.4],
        vertical_spacing=0.08,
    )

    # 상단: 실제 vs 기대
    ticker = results.get("ticker", "MSTR")
    ti = TICKER_INFO.get(ticker, {"label": ticker, "color": "#6EA8D0"})
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["actual"],
            name=f"실제 ({ti['label']})",
            line=dict(color=ti["color"], width=2),
        ),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["expected"],
            name="기대 수익률",
            line=dict(color=color, width=1.5, dash="dot"),
            opacity=0.8,
        ),
        row=1,
        col=1,
    )

    # 하단: AR 막대
    ar_colors = ["#2ECC71" if v >= 0 else "#E74C3C" for v in df["AR"]]
    fig.add_trace(
        go.Bar(
            x=df.index,
            y=df["AR"],
            name="AR",
            marker_color=ar_colors,
            showlegend=False,
        ),
        row=2,
        col=1,
    )

    # 이벤트 수직선: subplot은 xref="x", "x2"로 각 패널에 별도 add_shape
    for xref, yref in [("x", "y domain"), ("x2", "y2 domain")]:
        fig.add_shape(
            type="line",
            x0=_EVENT_DATE_STR,
            x1=_EVENT_DATE_STR,
            y0=0,
            y1=1,
            xref=xref,
            yref=yref,
            line=dict(color="red", width=2, dash="dash"),
        )
    # 레이블은 상단 패널에만
    fig.add_annotation(
        x=_EVENT_DATE_STR,
        y=1,
        xref="x",
        yref="y domain",
        text="ASC 350-60",
        showarrow=False,
        font=dict(color="red", size=10),
        xanchor="left",
        yanchor="top",
        bgcolor="rgba(13,17,23,0.7)",
    )

    fig.add_hline(y=0, line_color="#555", line_width=0.5, row=2, col=1)

    fig.update_layout(
        **_DARK_LAYOUT,
        title=f"{label} — 실제 vs 기대 수익률",
        height=500,
        legend=dict(orientation="h", y=1.05),
    )
    fig.update_yaxes(tickformat=".1%")
    return fig


def chart_car(results: dict) -> go.Figure:
    """
    누적 비정상 수익률(CAR) + 95% 신뢰구간 밴드.
    """
    df = results["event_window"]
    color = results["model_color"]
    label = results["model_label"]
    sigma = results["sigma_resid"]

    upper = df["CAR"] + 1.96 * sigma
    lower = df["CAR"] - 1.96 * sigma

    fig = go.Figure()

    # 신뢰구간 밴드
    fig.add_trace(
        go.Scatter(
            x=list(df.index) + list(df.index[::-1]),
            y=list(upper) + list(lower[::-1]),
            fill="toself",
            fillcolor=_hex_to_rgba(color, alpha=0.13),
            line=dict(color="rgba(0,0,0,0)"),
            name="95% 신뢰구간",
            showlegend=True,
        )
    )

    # CAR 라인
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["CAR"],
            name="CAR",
            line=dict(color=color, width=2.5),
        )
    )

    _add_event_line(fig)
    fig.add_hline(y=0, line_color="#555", line_width=0.5)

    fig.update_layout(
        **_DARK_LAYOUT,
        title=f"누적 비정상 수익률 (CAR) — {label}",
        yaxis=dict(tickformat=".1%", title="CAR"),
        xaxis_title="날짜",
        height=360,
        legend=dict(orientation="h", y=1.08),
    )
    return fig


def chart_ar_bar(results: dict) -> go.Figure:
    """
    일별 비정상 수익률(AR) 막대차트.
    양수=초록, 음수=빨강, 이벤트 당일 강조.
    """
    df = results["event_window"]
    label = results["model_label"]

    bar_colors = []
    for idx, val in zip(df.index, df["AR"]):
        if idx == EVENT_DATE:
            bar_colors.append("#FFD700")  # 이벤트 당일 골드
        elif val >= 0:
            bar_colors.append("#2ECC71")
        else:
            bar_colors.append("#E74C3C")

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=df.index,
            y=df["AR"],
            marker_color=bar_colors,
            name="AR (일별)",
        )
    )

    _add_event_line(fig, show_label=False)
    fig.add_hline(y=0, line_color="#555", line_width=0.5)

    fig.update_layout(
        **_DARK_LAYOUT,
        title=f"일별 비정상 수익률 (AR) — {label}",
        yaxis=dict(tickformat=".1%", title="AR"),
        xaxis_title="날짜",
        height=360,
        showlegend=False,
    )
    return fig
