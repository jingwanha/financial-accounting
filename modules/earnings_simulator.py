"""
earnings_simulator.py — Module B: ASC 350-60 EPS 시뮬레이터
구 기준(원가법) vs 신 기준(공정가치법) EPS 비교
"""
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from modules.data_fetcher import (
    fetch_btc_price_history, get_quarter_end_price, _btc_fallback,
    compute_daily_eps_series, compute_rolling_volatility,
)


DATA_PATH = "data/mstr_holdings.csv"


def load_holdings() -> pd.DataFrame:
    df = pd.read_csv(DATA_PATH)
    df["date"] = pd.to_datetime(df["date"])
    if "is_actual_asc360" not in df.columns:
        df["is_actual_asc360"] = False
    df["is_actual_asc360"] = df["is_actual_asc360"].astype(bool)
    df = df.sort_values("date").reset_index(drop=True)
    return df


def compute_eps(df: pd.DataFrame, btc_prices: pd.DataFrame) -> pd.DataFrame:
    """
    분기별 EPS 계산:
    - old_eps: 구 기준 (원가법) — 손상 미인식 단순화 버전
    - new_eps: ASC 350-60 (공정가치법) — 미실현 손익 반영
    """
    rows = []
    for i, row in df.iterrows():
        date_str = row["date"].strftime("%Y-%m-%d")
        shares = row["shares_outstanding"]
        reported_ni = row["reported_net_income_usd"]

        # 당기말 BTC 가격
        btc_end = get_quarter_end_price(btc_prices, date_str)

        # 전기말 BTC 가격 (첫 분기는 전기 없으므로 취득원가 사용)
        if i == 0:
            btc_start = row["avg_cost_usd"]
        else:
            prev_date = df.iloc[i - 1]["date"].strftime("%Y-%m-%d")
            btc_start = get_quarter_end_price(btc_prices, prev_date)

        holdings = row["btc_holdings"]
        is_actual = bool(row.get("is_actual_asc360", False))

        # 분기별 BTC 공정가치 변동액
        fair_value_gain_loss = (btc_end - btc_start) * holdings

        if is_actual:
            # ── 2025~: 실제 ASC 350-60 공시값 ──────────────────────────────
            # reported_ni = 공정가치법 적용 순이익 (실제)
            new_ni  = reported_ni
            new_eps = reported_ni / shares if shares else 0
            # 구 기준 역산: 공정가치 손익 제거 → 원가법 추정치
            old_ni  = reported_ni - fair_value_gain_loss
            old_eps = old_ni / shares if shares else 0
        else:
            # ── ~2024: Counterfactual 시뮬레이션 ───────────────────────────
            # reported_ni = 원가법(구 기준) 실제 공시값 → old_eps가 실제값
            old_ni  = reported_ni
            old_eps = reported_ni / shares if shares else 0
            # ASC 350-60 소급 적용: 공정가치 손익을 순이익에 추가 → new_eps가 counterfactual
            new_ni  = reported_ni + fair_value_gain_loss
            new_eps = new_ni / shares if shares else 0

        rows.append({
            "quarter": row["quarter"],
            "date": row["date"],
            "btc_holdings": holdings,
            "btc_price_start": btc_start,
            "btc_price_end": btc_end,
            "fair_value_gain_loss": fair_value_gain_loss,
            "reported_net_income": reported_ni,
            "old_net_income": old_ni,
            "new_net_income": new_ni,
            "new_eps": new_eps,
            "old_eps": old_eps,
            "eps_delta": new_eps - old_eps,
            "shares_outstanding": shares,
            "is_actual_asc360": is_actual,
        })

    return pd.DataFrame(rows)


def apply_sensitivity(df: pd.DataFrame, btc_change_pct: float) -> pd.DataFrame:
    """BTC 가격이 btc_change_pct% 변할 때 EPS 변화 시뮬레이션."""
    df = df.copy()
    df["sim_btc_end"] = df["btc_price_end"] * (1 + btc_change_pct / 100)
    df["sim_fv_gain_loss"] = (df["sim_btc_end"] - df["btc_price_start"]) * df["btc_holdings"]
    df["sim_new_ni"] = df["reported_net_income"] + (df["sim_fv_gain_loss"] - df["fair_value_gain_loss"])
    df["sim_new_eps"] = df["sim_new_ni"] / df["shares_outstanding"]
    df["sim_eps_delta"] = df["sim_new_eps"] - df["old_eps"]
    return df


def filter_by_quarter_range(df: pd.DataFrame, start_q: str, end_q: str) -> pd.DataFrame:
    quarters = df["quarter"].tolist()
    si = quarters.index(start_q) if start_q in quarters else 0
    ei = quarters.index(end_q) + 1 if end_q in quarters else len(quarters)
    return df.iloc[si:ei].copy()


# ── Charts ────────────────────────────────────────────────────────────────────

def chart_pre_post_comparison(eps_df: pd.DataFrame) -> go.Figure:
    """
    핵심 비교 차트: 소급 시뮬레이션(~2024) vs 실제 ASC 350-60 적용(2025~)
    - 구 기준 EPS (전 기간)
    - 시뮬레이션 ASC 350-60 EPS (~2024, 소급 역산)
    - 실제 ASC 350-60 EPS (2025~, 실제 공시)
    """
    sim = eps_df[~eps_df["is_actual_asc360"]].copy()
    actual = eps_df[eps_df["is_actual_asc360"]].copy()

    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=(
            "EPS 비교: 구 기준 / 소급 시뮬레이션(~2024) / 실제 ASC 350-60(2025~)",
            "공정가치 평가손익 (ASC 350-60 기준)",
        ),
        vertical_spacing=0.14,
        row_heights=[0.65, 0.35],
    )

    # ── Row 1: EPS ──
    # 구 기준 (전 기간 — 점선)
    fig.add_trace(go.Scatter(
        x=eps_df["quarter"], y=eps_df["old_eps"],
        name="구 기준 EPS (원가법, 전 기간)",
        mode="lines+markers",
        line=dict(color="#6EA8D0", dash="dot", width=2),
        marker=dict(size=6),
    ), row=1, col=1)

    # 소급 시뮬레이션 (~2024)
    fig.add_trace(go.Bar(
        x=sim["quarter"], y=sim["new_eps"],
        name="시뮬레이션 ASC 350-60 (~2024)",
        marker_color="rgba(244,132,95,0.6)",
        marker_line_color="#F4845F",
        marker_line_width=1.5,
        offsetgroup=0,
    ), row=1, col=1)

    # 실제 적용 (2025~)
    fig.add_trace(go.Bar(
        x=actual["quarter"], y=actual["new_eps"],
        name="실제 ASC 350-60 적용 (2025~)",
        marker_color="rgba(46,204,113,0.85)",
        marker_line_color="#27AE60",
        marker_line_width=2,
        offsetgroup=0,
    ), row=1, col=1)

    fig.add_hline(y=0, line_dash="dot", line_color="gray", row=1, col=1)

    # ── Row 2: 공정가치 손익 ──
    colors_sim = ["rgba(244,132,95,0.6)" if v >= 0 else "rgba(231,76,60,0.6)"
                  for v in sim["fair_value_gain_loss"]]
    colors_act = ["rgba(46,204,113,0.9)" if v >= 0 else "rgba(231,76,60,0.9)"
                  for v in actual["fair_value_gain_loss"]]

    fig.add_trace(go.Bar(
        x=sim["quarter"], y=sim["fair_value_gain_loss"] / 1e9,
        name="공정가치 손익 (시뮬레이션)",
        marker_color=colors_sim,
        showlegend=False,
    ), row=2, col=1)
    fig.add_trace(go.Bar(
        x=actual["quarter"], y=actual["fair_value_gain_loss"] / 1e9,
        name="공정가치 손익 (실제)",
        marker_color=colors_act,
        showlegend=False,
    ), row=2, col=1)
    fig.add_hline(y=0, line_dash="dot", line_color="gray", row=2, col=1)

    # 구분선: 카테고리 인덱스 기준으로 2024Q4와 2025Q1 사이
    quarters_list = eps_df["quarter"].tolist()
    if "2025Q1" in quarters_list:
        boundary = quarters_list.index("2025Q1") - 0.5
        # row=1 구분선
        fig.add_shape(type="line", xref="x", yref="paper",
                      x0=boundary, x1=boundary, y0=0, y1=1,
                      line=dict(color="#F39C12", width=2, dash="dash"),
                      row=1, col=1)
        fig.add_annotation(x=boundary, y=1, xref="x", yref="paper",
                           text="ASC 350-60<br>의무 적용 →",
                           showarrow=False, font=dict(color="#F39C12", size=11),
                           xanchor="right", yanchor="top", row=1, col=1)
        # row=2 구분선
        fig.add_shape(type="line", xref="x2", yref="paper",
                      x0=boundary, x1=boundary, y0=0, y1=0.38,
                      line=dict(color="#F39C12", width=2, dash="dash"))

    fig.update_layout(
        barmode="overlay",
        height=600,
        plot_bgcolor="#0E1117", paper_bgcolor="#0E1117",
        font_color="white",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    fig.update_xaxes(tickangle=-45)
    fig.update_yaxes(title_text="EPS (USD)", row=1, col=1)
    fig.update_yaxes(title_text="손익 (USD Billion)", row=2, col=1)
    return fig


def chart_eps_volatility_comparison(eps_df: pd.DataFrame) -> go.Figure:
    """소급 시뮬레이션 기간 vs 실제 적용 기간의 EPS 변동성 비교 박스플롯."""
    sim    = eps_df[~eps_df["is_actual_asc360"]]
    actual = eps_df[eps_df["is_actual_asc360"]]

    fig = go.Figure()
    fig.add_trace(go.Box(
        y=sim["old_eps"], name="구 기준 EPS<br>(2020~2024)",
        marker_color="#6EA8D0", boxmean=True,
    ))
    fig.add_trace(go.Box(
        y=sim["new_eps"], name="시뮬레이션 ASC 350-60<br>(2020~2024)",
        marker_color="#F4845F", boxmean=True,
    ))
    fig.add_trace(go.Box(
        y=actual["new_eps"], name="실제 ASC 350-60<br>(2025~)",
        marker_color="#2ECC71", boxmean=True,
    ))
    fig.update_layout(
        title="EPS 변동성 비교 (소급 시뮬레이션 vs 실제 적용)",
        height=380,
        plot_bgcolor="#0E1117", paper_bgcolor="#0E1117",
        font_color="white",
        yaxis_title="EPS (USD)",
        showlegend=True,
    )
    return fig


def chart_simulation_accuracy(eps_df: pd.DataFrame) -> go.Figure:
    """
    2025 실제 데이터와 시뮬레이션 모델 정확도 검증.
    실제 ASC 350-60 EPS와 '만약 소급 적용했다면' 차이를 보여줌.
    """
    actual = eps_df[eps_df["is_actual_asc360"]].copy()
    if actual.empty:
        return go.Figure()

    # 시뮬레이션 모델의 EPS(old 역산 기반) vs 실제 보고 EPS
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=actual["quarter"], y=actual["new_eps"],
        name="실제 보고 EPS (ASC 350-60)",
        marker_color="#2ECC71",
        offsetgroup=0,
    ))
    fig.add_trace(go.Bar(
        x=actual["quarter"], y=actual["old_eps"],
        name="구 기준으로 역산한 EPS (참고)",
        marker_color="#6EA8D0",
        offsetgroup=1,
    ))
    fig.add_hline(y=0, line_dash="dot", line_color="gray")
    fig.update_layout(
        title="2025 실제 적용 결과: ASC 350-60 EPS vs 구 기준 역산 EPS",
        barmode="group",
        height=360,
        plot_bgcolor="#0E1117", paper_bgcolor="#0E1117",
        font_color="white",
        yaxis_title="EPS (USD)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    return fig


def chart_eps_comparison(df: pd.DataFrame) -> go.Figure:
    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=("분기별 EPS: 구 기준 vs ASC 350-60", "EPS 차이 (신 기준 − 구 기준)"),
        vertical_spacing=0.15,
        row_heights=[0.65, 0.35],
    )

    fig.add_trace(go.Bar(
        x=df["quarter"], y=df["old_eps"],
        name="구 기준 EPS (원가법)",
        marker_color="#6EA8D0",
        offsetgroup=0,
    ), row=1, col=1)

    fig.add_trace(go.Bar(
        x=df["quarter"], y=df["new_eps"],
        name="ASC 350-60 EPS (공정가치)",
        marker_color="#F4845F",
        offsetgroup=1,
    ), row=1, col=1)

    colors = ["#2ECC71" if v >= 0 else "#E74C3C" for v in df["eps_delta"]]
    fig.add_trace(go.Bar(
        x=df["quarter"], y=df["eps_delta"],
        name="EPS 차이",
        marker_color=colors,
        showlegend=False,
    ), row=2, col=1)

    fig.add_hline(y=0, line_dash="dash", line_color="gray", row=2, col=1)

    fig.update_layout(
        barmode="group",
        height=520,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        plot_bgcolor="#0E1117",
        paper_bgcolor="#0E1117",
        font_color="white",
        yaxis_title="EPS (USD)",
        yaxis2_title="Δ EPS (USD)",
    )
    fig.update_xaxes(tickangle=-45)
    return fig


def chart_sensitivity(df: pd.DataFrame, btc_change_pct: float, y_range: list | None = None) -> go.Figure:
    df_sim = apply_sensitivity(df, btc_change_pct)

    # BTC 주당가치 = 분기말 BTC 시가총액 / 발행주식수
    # EPS 민감도의 핵심 드라이버: ΔEPS per 1% = BTC주당가치 / 100
    df_sim["btc_value_per_share"] = (
        df_sim["btc_price_end"] * df_sim["btc_holdings"] / df_sim["shares_outstanding"]
    )

    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=(
            f"민감도 분석: BTC 가격 {btc_change_pct:+.0f}% 변동 시 EPS",
            "BTC 주당가치 (EPS 민감도 드라이버 — BTC가 1% 변할 때 ΔEPS = 아래값 ÷ 100)",
        ),
        vertical_spacing=0.16,
        row_heights=[0.62, 0.38],
    )

    # ── Row 1: EPS ──
    fig.add_trace(go.Scatter(
        x=df_sim["quarter"], y=df_sim["old_eps"],
        name="구 기준 EPS",
        line=dict(color="#6EA8D0", dash="dash"),
        mode="lines+markers",
        marker=dict(size=6),
    ), row=1, col=1)
    fig.add_trace(go.Scatter(
        x=df_sim["quarter"], y=df_sim["sim_new_eps"],
        name=f"ASC 350-60 EPS (BTC {btc_change_pct:+.0f}%)",
        line=dict(color="#F4845F"),
        mode="lines+markers",
        marker=dict(size=6),
    ), row=1, col=1)
    fig.add_hline(y=0, line_dash="dot", line_color="gray", row=1, col=1)

    # ── Row 2: BTC 주당가치 ──
    colors_btv = [
        "#F7931A" if is_actual else "rgba(247,147,26,0.45)"
        for is_actual in df_sim["is_actual_asc360"]
    ]
    fig.add_trace(go.Bar(
        x=df_sim["quarter"],
        y=df_sim["btc_value_per_share"],
        name="BTC 주당가치 (USD/주)",
        marker_color=colors_btv,
        text=[f"${v:,.0f}" for v in df_sim["btc_value_per_share"]],
        textposition="outside",
        textfont=dict(size=9),
        showlegend=True,
    ), row=2, col=1)

    fig.update_layout(
        height=560,
        plot_bgcolor="#0E1117",
        paper_bgcolor="#0E1117",
        font_color="white",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(t=80),
    )
    fig.update_xaxes(tickangle=-45)
    fig.update_yaxes(title_text="EPS (USD)", row=1, col=1,
                     **({"range": y_range} if y_range else {}))
    fig.update_yaxes(title_text="USD / 주", row=2, col=1)
    return fig


def chart_fv_gain_loss(df: pd.DataFrame) -> go.Figure:
    colors = ["#2ECC71" if v >= 0 else "#E74C3C" for v in df["fair_value_gain_loss"]]
    fig = go.Figure(go.Bar(
        x=df["quarter"],
        y=df["fair_value_gain_loss"] / 1e9,
        marker_color=colors,
        text=[f"${v/1e9:.2f}B" for v in df["fair_value_gain_loss"]],
        textposition="outside",
    ))
    fig.update_layout(
        title="분기별 BTC 공정가치 평가손익 (ASC 350-60)",
        height=340,
        plot_bgcolor="#0E1117",
        paper_bgcolor="#0E1117",
        font_color="white",
        yaxis_title="금액 (USD Billion)",
    )
    fig.update_xaxes(tickangle=-45)
    return fig


# ── 대용량 일별 데이터 차트 ────────────────────────────────────────────────────

def chart_daily_eps_impact(btc_df: pd.DataFrame, holdings: float,
                            shares: float, cost_basis: float) -> go.Figure:
    """
    일별 BTC 가격 전체 기간에 걸친 누적 EPS 영향 (ASC 350-60 기준).
    ~1800개 데이터 포인트.
    """
    df = compute_daily_eps_series(btc_df, holdings, shares, cost_basis)
    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=("일별 BTC 가격 (USD)", "ASC 350-60 누적 EPS 영향 (구 기준 대비)"),
        vertical_spacing=0.12,
        shared_xaxes=True,
    )
    fig.add_trace(go.Scatter(
        x=df.index, y=df["price"],
        name="BTC 가격", mode="lines",
        line=dict(color="#F7931A", width=1),
        fill="tozeroy", fillcolor="rgba(247,147,26,0.08)",
    ), row=1, col=1)

    fig.add_trace(go.Scatter(
        x=df.index, y=df["cumulative_eps_impact"],
        name="누적 EPS 차이", mode="lines",
        line=dict(color="#6EA8D0", width=1.5),
        fill="tozeroy", fillcolor="rgba(110,168,208,0.12)",
    ), row=2, col=1)
    fig.add_hline(y=0, line_dash="dash", line_color="gray", row=2, col=1)

    fig.update_layout(
        height=500,
        plot_bgcolor="#0E1117", paper_bgcolor="#0E1117",
        font_color="white",
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    fig.update_yaxes(title_text="USD", row=1, col=1)
    fig.update_yaxes(title_text="EPS (USD)", row=2, col=1)
    return fig


def chart_volatility(btc_df: pd.DataFrame) -> go.Figure:
    """BTC 30일/90일 롤링 연환산 변동성 차트."""
    df30 = compute_rolling_volatility(btc_df, 30)
    df90 = compute_rolling_volatility(btc_df, 90)
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df30.index, y=df30["vol_30d"],
        name="30일 변동성 (연환산 %)", mode="lines",
        line=dict(color="#F4845F", width=1.5),
    ))
    fig.add_trace(go.Scatter(
        x=df90.index, y=df90["vol_90d"],
        name="90일 변동성 (연환산 %)", mode="lines",
        line=dict(color="#6EA8D0", width=1.5),
    ))
    fig.update_layout(
        title="BTC 가격 변동성 (ASC 350-60 하 EPS 변동성과 직결)",
        height=350,
        plot_bgcolor="#0E1117", paper_bgcolor="#0E1117",
        font_color="white",
        yaxis_title="변동성 (%)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    return fig


def chart_btc_stock_correlation(btc_df: pd.DataFrame, stock_df: pd.DataFrame,
                                 ticker: str = "MSTR") -> go.Figure:
    """BTC 일별 수익률 vs 주가 수익률 상관관계 산점도."""
    if stock_df.empty:
        return go.Figure()
    merged = pd.merge(
        btc_df["price"].pct_change().rename("btc_ret"),
        stock_df["close"].pct_change().rename("stock_ret"),
        left_index=True, right_index=True,
        how="inner",
    ).dropna()
    merged = merged[(merged["btc_ret"].abs() < 0.3) & (merged["stock_ret"].abs() < 0.5)]
    corr = merged.corr().iloc[0, 1]

    z = np.polyfit(merged["btc_ret"], merged["stock_ret"], 1)
    x_line = np.linspace(merged["btc_ret"].min(), merged["btc_ret"].max(), 100)

    fig = go.Figure(go.Scatter(
        x=merged["btc_ret"] * 100,
        y=merged["stock_ret"] * 100,
        mode="markers",
        marker=dict(color="#F4845F", size=3, opacity=0.4),
        name=f"일별 수익률 (n={len(merged):,})",
    ))
    fig.add_trace(go.Scatter(
        x=x_line * 100, y=np.polyval(z, x_line) * 100,
        mode="lines", name=f"회귀선 (r={corr:.3f})",
        line=dict(color="#2ECC71", width=2),
    ))
    fig.update_layout(
        title=f"BTC 일별 수익률 vs {ticker} 주가 수익률 상관관계 (r={corr:.3f})",
        height=380,
        plot_bgcolor="#0E1117", paper_bgcolor="#0E1117",
        font_color="white",
        xaxis_title="BTC 수익률 (%)",
        yaxis_title=f"{ticker} 수익률 (%)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    return fig
