"""
multi_company.py — MSTR / TSLA / MARA 멀티 기업 비교 분석
"""
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from modules.data_fetcher import get_quarter_end_price

COMPANY_META = {
    "MSTR": {"name": "MicroStrategy", "color": "#F4845F", "strategy": "전략적 대규모 보유"},
    "TSLA": {"name": "Tesla",         "color": "#6EA8D0", "strategy": "단기 투자 후 부분 매각"},
    "MARA": {"name": "Marathon Digital","color": "#2ECC71","strategy": "채굴 후 보유 (Miner)"},
}

DATA_PATHS = {
    "MSTR": "data/mstr_holdings.csv",
    "TSLA": "data/tsla_holdings.csv",
    "MARA": "data/mara_holdings.csv",
}


def load_all_holdings() -> dict[str, pd.DataFrame]:
    result = {}
    for ticker, path in DATA_PATHS.items():
        df = pd.read_csv(path)
        df["date"] = pd.to_datetime(df["date"])
        if "is_actual_asc360" not in df.columns:
            df["is_actual_asc360"] = False
        df["is_actual_asc360"] = df["is_actual_asc360"].astype(bool)
        df["ticker"] = ticker
        result[ticker] = df.sort_values("date").reset_index(drop=True)
    return result


def compute_all_eps(holdings: dict, btc_prices: pd.DataFrame) -> pd.DataFrame:
    """세 기업 모두 EPS 계산 후 하나의 DataFrame으로 합침."""
    from modules.earnings_simulator import compute_eps
    frames = []
    for ticker, df in holdings.items():
        eps = compute_eps(df, btc_prices)
        eps["ticker"] = ticker
        frames.append(eps)
    return pd.concat(frames, ignore_index=True)


# ── Charts ────────────────────────────────────────────────────────────────────

def chart_btc_holdings_comparison(holdings: dict) -> go.Figure:
    """3개 기업 BTC 보유량 추이 비교."""
    fig = go.Figure()
    for ticker, df in holdings.items():
        meta = COMPANY_META[ticker]
        fig.add_trace(go.Scatter(
            x=df["quarter"], y=df["btc_holdings"],
            name=f"{ticker} ({meta['strategy']})",
            mode="lines+markers",
            line=dict(color=meta["color"], width=2),
            marker=dict(size=6),
        ))
    fig.update_layout(
        title="기업별 BTC 보유량 추이 비교",
        height=380,
        plot_bgcolor="#0E1117", paper_bgcolor="#0E1117",
        font_color="white", yaxis_title="BTC 보유량",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    fig.update_xaxes(tickangle=-45)
    return fig


def chart_eps_delta_comparison(all_eps: pd.DataFrame) -> go.Figure:
    """3개 기업 ASC 350-60 EPS 차이(구 기준 대비) 비교."""
    fig = go.Figure()
    for ticker in ["MSTR", "TSLA", "MARA"]:
        df = all_eps[all_eps["ticker"] == ticker]
        meta = COMPANY_META[ticker]
        fig.add_trace(go.Bar(
            x=df["quarter"], y=df["eps_delta"],
            name=ticker,
            marker_color=meta["color"],
            opacity=0.8,
        ))
    fig.add_hline(y=0, line_dash="dot", line_color="gray")
    fig.update_layout(
        title="기업별 EPS 차이 (ASC 350-60 − 구 기준) — 보유량 규모별 영향 비교",
        barmode="group",
        height=420,
        plot_bgcolor="#0E1117", paper_bgcolor="#0E1117",
        font_color="white", yaxis_title="EPS 차이 (USD)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    fig.update_xaxes(tickangle=-45)
    return fig


def chart_eps_volatility_panel(all_eps: pd.DataFrame) -> go.Figure:
    """3개 기업 × 2개 기준 EPS 변동성 비교 박스플롯."""
    fig = go.Figure()
    for ticker in ["MSTR", "TSLA", "MARA"]:
        df = all_eps[all_eps["ticker"] == ticker]
        meta = COMPANY_META[ticker]
        fig.add_trace(go.Box(
            y=df["old_eps"], name=f"{ticker}<br>구 기준",
            marker_color=meta["color"], opacity=0.5, boxmean=True,
            legendgroup=ticker,
        ))
        fig.add_trace(go.Box(
            y=df["new_eps"], name=f"{ticker}<br>ASC 350-60",
            marker_color=meta["color"], boxmean=True,
            legendgroup=ticker,
        ))
    fig.update_layout(
        title="기업별 EPS 분포 비교 (구 기준 vs ASC 350-60)",
        height=420,
        plot_bgcolor="#0E1117", paper_bgcolor="#0E1117",
        font_color="white", yaxis_title="EPS (USD)",
    )
    return fig


def chart_fv_impact_heatmap(all_eps: pd.DataFrame) -> go.Figure:
    """공정가치 손익 히트맵: 기업 × 분기."""
    pivot = all_eps.pivot_table(
        index="ticker", columns="quarter",
        values="fair_value_gain_loss", aggfunc="sum"
    ) / 1e6  # Million USD

    fig = go.Figure(go.Heatmap(
        z=pivot.values,
        x=list(pivot.columns),
        y=list(pivot.index),
        colorscale="RdYlGn",
        zmid=0,
        text=[[f"${v:.0f}M" for v in row] for row in pivot.values],
        texttemplate="%{text}",
        colorbar=dict(title="USD Million"),
    ))
    fig.update_layout(
        title="기업별 분기별 공정가치 평가손익 히트맵 (ASC 350-60 기준, USD M)",
        height=280,
        plot_bgcolor="#0E1117", paper_bgcolor="#0E1117",
        font_color="white",
        xaxis=dict(tickangle=-45),
    )
    return fig


def chart_eps_std_bar(all_eps: pd.DataFrame) -> go.Figure:
    """기업별 EPS 표준편차(변동성) 구 기준 vs ASC 350-60."""
    tickers = ["MSTR", "TSLA", "MARA"]
    old_stds = [all_eps[all_eps["ticker"] == t]["old_eps"].std() for t in tickers]
    new_stds = [all_eps[all_eps["ticker"] == t]["new_eps"].std() for t in tickers]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=tickers, y=old_stds, name="구 기준 EPS 표준편차",
        marker_color="#6EA8D0", offsetgroup=0,
    ))
    fig.add_trace(go.Bar(
        x=tickers, y=new_stds, name="ASC 350-60 EPS 표준편차",
        marker_color="#F4845F", offsetgroup=1,
    ))
    fig.update_layout(
        title="기업별 EPS 변동성 증가폭 — BTC 보유 규모에 비례",
        barmode="group", height=360,
        plot_bgcolor="#0E1117", paper_bgcolor="#0E1117",
        font_color="white", yaxis_title="표준편차 (USD)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    return fig


def summary_stats(all_eps: pd.DataFrame) -> pd.DataFrame:
    """3개 기업 핵심 통계 요약 테이블."""
    rows = []
    for ticker in ["MSTR", "TSLA", "MARA"]:
        df = all_eps[all_eps["ticker"] == ticker]
        btc_max = df["btc_holdings"].max()
        old_std = df["old_eps"].std()
        new_std = df["new_eps"].std()
        vol_inc = (new_std / old_std - 1) * 100 if old_std > 0 else 0
        total_fv = df["fair_value_gain_loss"].sum() / 1e9
        rows.append({
            "기업": ticker,
            "최대 BTC 보유": f"{btc_max:,.0f}",
            "구기준 EPS 표준편차": f"${old_std:.1f}",
            "ASC350-60 EPS 표준편차": f"${new_std:.1f}",
            "변동성 증가율": f"{vol_inc:+.0f}%",
            "누적 공정가치 손익": f"${total_fv:.2f}B",
        })
    return pd.DataFrame(rows)
