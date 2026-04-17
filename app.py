"""
app.py — Streamlit 메인 앱
ASC 350-60 가상자산 회계 기준이 기업 이익 및 공시에 미치는 영향
KAIST 디지털금융 MBA | 재무회계 | Spring 2026
"""

import os
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

st.set_page_config(
    page_title="ASC 350-60 암호화폐 회계 대시보드",
    page_icon="₿",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
[data-testid="stMetricValue"] { font-size: 1.5rem; font-weight: 700; }
.section-header {
    background: linear-gradient(90deg, #1a1f2e, #0e1117);
    border-left: 4px solid #F4845F;
    padding: 10px 16px;
    border-radius: 4px;
    margin-bottom: 16px;
}
.ai-box {
    background: #1a1f2e;
    border: 1px solid #F4845F44;
    border-radius: 8px;
    padding: 16px;
    margin-top: 8px;
}
</style>
""",
    unsafe_allow_html=True,
)

# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.title("₿ ASC 350-60 Dashboard")
    st.divider()

    st.markdown(
        """
**모듈**
- 📊 EPS 시뮬레이터
- ⚖️ 전후 비교 (핵심)
- 🏢 멀티 기업 비교
- 🔍 EDGAR NLP 분석
- 📈 이벤트 연구
- 💡 인사이트
- ℹ️ 연구 배경
"""
    )
    st.divider()
    st.caption("데이터: yfinance · CoinGecko · SEC EDGAR")

# ══════════════════════════════════════════════════════════════════════════════
# TABS
# ══════════════════════════════════════════════════════════════════════════════
tab_b, tab_compare, tab_multi, tab_c, tab_event, tab_ai, tab_about = st.tabs(
    [
        "📊 EPS 시뮬레이터",
        "⚖️ 전후 비교 (핵심)",
        "🏢 멀티 기업 비교",
        "🔍 EDGAR NLP 분석",
        "📈 이벤트 연구",
        "💡 인사이트",
        "ℹ️ 연구 배경",
    ]
)

# ── BTC 데이터 공통 로드 (캐시) ──────────────────────────────────────────────
from modules.data_fetcher import (
    fetch_btc_price_history,
    _btc_fallback,
    fetch_btc_current_price,
    fetch_stock_history,
)

with st.spinner("BTC 가격 데이터 로딩 중 (yfinance)..."):
    btc_prices = fetch_btc_price_history()
    if btc_prices is None or btc_prices.empty:
        st.warning("yfinance 연결 실패 — 하드코딩 분기 데이터 사용")
        btc_prices = _btc_fallback()

# ══════════════════════════════════════════════════════════════════════════════
# TAB B: EPS 시뮬레이터
# ══════════════════════════════════════════════════════════════════════════════
with tab_b:
    st.markdown(
        '<div class="section-header"><h2>📊 EPS 시뮬레이터 — MSTR 분기별 분석</h2></div>',
        unsafe_allow_html=True,
    )

    from modules.earnings_simulator import (
        load_holdings,
        compute_eps,
        chart_eps_comparison,
        chart_sensitivity,
        chart_fv_gain_loss,
        chart_volatility,
        chart_btc_stock_correlation,
    )

    holdings = load_holdings()
    eps_df = compute_eps(holdings, btc_prices)

    quarters_list = eps_df["quarter"].tolist()
    col1, col2 = st.columns(2)
    with col1:
        q_start = st.selectbox("시작 분기", quarters_list, index=0, key="b_start")
    with col2:
        q_end = st.selectbox(
            "종료 분기", quarters_list, index=len(quarters_list) - 1, key="b_end"
        )

    i_start = quarters_list.index(q_start)
    i_end = quarters_list.index(q_end)
    if i_start > i_end:
        st.error("시작 분기가 종료 분기보다 늦습니다.")
        st.stop()

    filtered = eps_df.iloc[i_start : i_end + 1]

    # KPI
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("평균 EPS 차이", f"${filtered['eps_delta'].mean():.2f}")
    with col2:
        st.metric("최대 EPS 차이", f"${filtered['eps_delta'].max():.2f}")
    with col3:
        st.metric(
            "EPS 변동성 증가",
            (
                f"{filtered['new_eps'].std() / filtered['old_eps'].std() * 100 - 100:.0f}%"
                if filtered["old_eps"].std() > 0
                else "N/A"
            ),
        )
    with col4:
        btc_now = fetch_btc_current_price()
        st.metric("현재 BTC 가격", f"${btc_now:,.0f}" if btc_now else "N/A")

    st.plotly_chart(chart_eps_comparison(filtered), width='stretch')
    st.plotly_chart(chart_fv_gain_loss(filtered), width='stretch')

    # Sensitivity
    st.divider()
    st.markdown("#### 🎚️ Sensitivity 분석 — BTC 가격 변동 시 EPS 영향")
    btc_change_pct = st.slider("BTC 가격 변동률 (%)", -80, 200, 0, 5, key="b_sens")
    latest = holdings.iloc[-1]

    # 슬라이더 전체 범위에서 가능한 EPS min/max를 미리 계산해 y축 고정
    from modules.earnings_simulator import apply_sensitivity
    all_eps_vals = []
    for _pct in range(-80, 201, 5):
        _df = apply_sensitivity(filtered, _pct)
        all_eps_vals.extend(_df["sim_new_eps"].tolist())
        all_eps_vals.extend(_df["old_eps"].tolist())
    _pad = (max(all_eps_vals) - min(all_eps_vals)) * 0.05
    sens_y_range = [min(all_eps_vals) - _pad, max(all_eps_vals) + _pad]

    sens_fig = chart_sensitivity(filtered, btc_change_pct, y_range=sens_y_range)
    st.plotly_chart(sens_fig, width='stretch')

    # Volatility & Correlation
    st.divider()
    st.markdown("#### 📉 BTC 가격 변동성 분석 (일별 데이터 기반)")
    vol_fig = chart_volatility(btc_prices)
    if vol_fig:
        st.plotly_chart(vol_fig, width='stretch')

    st.markdown("#### 🔗 BTC-MSTR 주가 상관관계")
    mstr_hist = fetch_stock_history("MSTR")
    corr_fig = chart_btc_stock_correlation(btc_prices, mstr_hist)
    if corr_fig:
        st.plotly_chart(corr_fig, width='stretch')

    # 테이블
    st.divider()
    st.markdown("#### 📋 분기별 상세 데이터")
    display_cols = [
        "quarter",
        "btc_price_start",
        "btc_price_end",
        "btc_holdings",
        "fair_value_gain_loss",
        "old_eps",
        "new_eps",
        "eps_delta",
    ]
    st.dataframe(
        filtered[display_cols]
        .rename(
            columns={
                "quarter": "분기",
                "btc_price_start": "BTC 시가",
                "btc_price_end": "BTC 종가",
                "btc_holdings": "BTC 보유량",
                "fair_value_gain_loss": "FV 손익",
                "old_eps": "구 기준 EPS",
                "new_eps": "ASC 350-60 EPS",
                "eps_delta": "EPS 차이",
            }
        )
        .style.format(
            {
                "BTC 시가": "${:,.0f}",
                "BTC 종가": "${:,.0f}",
                "BTC 보유량": "{:,.0f}",
                "FV 손익": "${:,.0f}",
                "구 기준 EPS": "${:.2f}",
                "ASC 350-60 EPS": "${:.2f}",
                "EPS 차이": "${:+.2f}",
            }
        ),
        width='stretch',
    )

# ══════════════════════════════════════════════════════════════════════════════
# TAB COMPARE: 전후 비교
# ══════════════════════════════════════════════════════════════════════════════
with tab_compare:
    st.markdown(
        '<div class="section-header"><h2>⚖️ 전후 비교 — 소급 시뮬레이션 vs 실제 적용</h2></div>',
        unsafe_allow_html=True,
    )

    from modules.earnings_simulator import (
        chart_pre_post_comparison,
        chart_eps_volatility_comparison,
        chart_simulation_accuracy,
    )

    holdings = load_holdings()
    eps_df = compute_eps(holdings, btc_prices)

    st.info(
        "**방법론**: 2024년 이전(is_actual=False) — 구기준 = 실제 공시, ASC350-60 = 소급 시뮬레이션 / "
        "2025년 이후(is_actual=True) — ASC350-60 = 실제 공시, 구기준 = 역산 추정",
        icon="📌",
    )

    pre = eps_df[~eps_df["is_actual_asc360"]]
    post = eps_df[eps_df["is_actual_asc360"]]

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("소급 적용 기간", f"{len(pre)} 분기")
    with col2:
        st.metric("실제 적용 기간", f"{len(post)} 분기")
    with col3:
        if not pre.empty and pre["old_eps"].std() > 0:
            ratio = pre["new_eps"].std() / pre["old_eps"].std()
            st.metric("소급 EPS 변동성 비율", f"{ratio:.2f}x")
    with col4:
        if not post.empty and post["old_eps"].std() > 0:
            ratio2 = post["new_eps"].std() / post["old_eps"].std()
            st.metric("실제 EPS 변동성 비율", f"{ratio2:.2f}x")

    st.plotly_chart(chart_pre_post_comparison(eps_df), width='stretch')
    st.plotly_chart(chart_eps_volatility_comparison(eps_df), width='stretch')

    if not post.empty:
        st.plotly_chart(chart_simulation_accuracy(eps_df), width='stretch')
    else:
        st.info(
            "2025년 실제 ASC 350-60 적용 데이터가 충분히 축적되면 시뮬레이션 정확도 차트가 표시됩니다."
        )

    st.divider()
    st.markdown("#### 📋 전체 분기 EPS 데이터 (소급 시뮬레이션 + 실제 적용)")
    styled_df = eps_df[
        [
            "quarter",
            "is_actual_asc360",
            "old_eps",
            "new_eps",
            "eps_delta",
            "btc_price_end",
        ]
    ].copy()
    styled_df["구분"] = styled_df["is_actual_asc360"].map(
        {True: "실제 ASC 350-60", False: "소급 시뮬레이션"}
    )
    st.dataframe(
        styled_df.drop(columns=["is_actual_asc360"])
        .rename(
            columns={
                "quarter": "분기",
                "old_eps": "구 기준 EPS",
                "new_eps": "ASC 350-60 EPS",
                "eps_delta": "EPS 차이",
                "btc_price_end": "분기말 BTC",
            }
        )
        .style.format(
            {
                "구 기준 EPS": "${:.2f}",
                "ASC 350-60 EPS": "${:.2f}",
                "EPS 차이": "${:+.2f}",
                "분기말 BTC": "${:,.0f}",
            }
        ),
        width='stretch',
    )

# ══════════════════════════════════════════════════════════════════════════════
# TAB MULTI: 멀티 기업 비교
# ══════════════════════════════════════════════════════════════════════════════
with tab_multi:
    st.markdown(
        '<div class="section-header"><h2>🏢 멀티 기업 비교 — MSTR / TSLA / MARA</h2></div>',
        unsafe_allow_html=True,
    )

    from modules.multi_company import (
        load_all_holdings,
        compute_all_eps,
        chart_btc_holdings_comparison,
        chart_eps_delta_comparison,
        chart_eps_volatility_panel,
        chart_fv_impact_heatmap,
        chart_eps_std_bar,
        summary_stats,
        COMPANY_META,
    )

    with st.spinner("멀티 기업 데이터 계산 중..."):
        all_holdings = load_all_holdings()
        all_eps = compute_all_eps(all_holdings, btc_prices)

    st.info(
        "**MSTR**: 전략적 대규모 보유 | **TSLA**: 단기 투자 후 부분 매각 | **MARA**: 채굴 후 보유 (Miner)",
        icon="🏢",
    )

    stats_df = summary_stats(all_eps)
    st.markdown("#### 📊 핵심 통계 요약")
    st.dataframe(stats_df, width='stretch')

    col_l, col_r = st.columns(2)
    with col_l:
        st.plotly_chart(
            chart_btc_holdings_comparison(all_holdings), width='stretch'
        )
    with col_r:
        st.plotly_chart(chart_eps_std_bar(all_eps), width='stretch')

    st.plotly_chart(chart_eps_delta_comparison(all_eps), width='stretch')
    st.plotly_chart(chart_eps_volatility_panel(all_eps), width='stretch')
    st.plotly_chart(chart_fv_impact_heatmap(all_eps), width='stretch')

# ══════════════════════════════════════════════════════════════════════════════
# TAB C: EDGAR NLP
# ══════════════════════════════════════════════════════════════════════════════
with tab_c:
    st.markdown(
        '<div class="section-header"><h2>🔍 EDGAR NLP 분석 — 10-K 공시 언어 변화</h2></div>',
        unsafe_allow_html=True,
    )

    from modules.edgar_nlp import (
        fetch_company_data,
        chart_keyword_heatmap,
        chart_sentiment,
        chart_disclosure_length,
        chart_lm_wordcount,
    )

    nlp_ticker = st.selectbox("기업 선택", ["MSTR", "TSLA", "COIN"], key="nlp_ticker")

    with st.spinner(f"{nlp_ticker} 10-K NLP 분석 중 (캐시 없을 시 수 분 소요)..."):
        nlp_df = fetch_company_data(nlp_ticker)

    if nlp_df is None or nlp_df.empty:
        st.error("NLP 데이터를 불러오지 못했습니다. 인터넷 연결을 확인하세요.")
    else:
        col1, col2, col3 = st.columns(3)
        with col1:
            last = nlp_df.iloc[-1]
            st.metric(
                "최근 연도 'digital asset' 언급", f"{last.get('kw_digital_asset', 0)}회"
            )
        with col2:
            st.metric(
                "최근 연도 'fair value' 언급", f"{last.get('kw_fair_value', 0)}회"
            )
        with col3:
            st.metric("최근 연도 감성 점수", f"{last.get('sentiment_compound', 0):.3f}")

        st.plotly_chart(
            chart_keyword_heatmap(nlp_df, nlp_ticker), width='stretch'
        )
        st.plotly_chart(chart_sentiment(nlp_df, nlp_ticker), width='stretch')
        st.plotly_chart(
            chart_disclosure_length(nlp_df, nlp_ticker), width='stretch'
        )

        st.divider()
        st.markdown("#### 📋 연도별 NLP 데이터")
        st.dataframe(
            nlp_df[
                [
                    c
                    for c in [
                        "year",
                        "kw_digital_asset",
                        "kw_fair_value",
                        "kw_impairment",
                        "kw_cryptocurrency",
                        "sentiment_compound",
                        "section_length",
                    ]
                    if c in nlp_df.columns
                ]
            ].rename(
                columns={
                    "year": "연도",
                    "kw_digital_asset": "digital asset",
                    "kw_fair_value": "fair value",
                    "kw_impairment": "impairment",
                    "kw_cryptocurrency": "cryptocurrency",
                    "sentiment_compound": "감성 점수",
                    "section_length": "섹션 길이(자)",
                }
            ),
            width='stretch',
        )


# ══════════════════════════════════════════════════════════════════════════════
# TAB EVENT: 이벤트 연구
# ══════════════════════════════════════════════════════════════════════════════
with tab_event:
    st.markdown(
        '<div class="section-header"><h2>📈 이벤트 연구 — ASC 350-60 발표 주가 영향 분석</h2></div>',
        unsafe_allow_html=True,
    )

    from modules.event_study import (
        fetch_event_study_data,
        compute_model_results,
        chart_daily_returns,
        chart_car,
        chart_ar_bar,
        chart_actual_vs_expected,
        build_kpi_dict,
        MODEL_CONFIGS,
        TICKER_INFO,
    )

    # ── 기업 선택 ─────────────────────────────────────────────────────────────
    ev_col_sel, ev_col_desc = st.columns([1, 3])
    with ev_col_sel:
        ev_ticker = st.selectbox(
            "분석 대상 기업",
            options=list(TICKER_INFO.keys()),
            format_func=lambda t: TICKER_INFO[t]["label"],
            key="ev_ticker_select",
        )
    with ev_col_desc:
        ti = TICKER_INFO[ev_ticker]
        st.info(
            f"**이벤트**: FASB ASC 350-60 확정 발표 (2023-12-13)  |  "
            f"**대상**: {ti['label']}  |  **방법**: OLS 시장모형 AR/CAR 분석  \n"
            f"_{ti['description']}_",
            icon="📌",
        )

    with st.spinner("이벤트 연구 데이터 로딩 중 (yfinance)..."):
        ev_returns = fetch_event_study_data()

    if ev_returns is None or ev_returns.empty:
        st.error("yfinance 데이터를 불러오지 못했습니다. 네트워크 연결을 확인하세요.")
    elif ev_ticker not in ev_returns.columns:
        st.error(f"{ev_ticker} 주가 데이터를 불러오지 못했습니다.")
    else:
        # ── 공통 차트: 일별 수익률 비교 ─────────────────────────────────────────
        st.markdown(f"#### 📊 이벤트 윈도우 일별 수익률 비교 ({ti['label']} vs BTC vs S&P 500)")
        st.plotly_chart(chart_daily_returns(ev_returns, ticker=ev_ticker), width='stretch')

        st.divider()

        # ── 모델별 서브탭 ─────────────────────────────────────────────────────────
        ev_model_tabs = st.tabs([
            "📉 S&P 500 시장모형",
            "₿ 비트코인 벤치마크 모형",
            "📊 다요인 모형 (S&P 500 + BTC)",
        ])

        for tab_widget, model_key in zip(ev_model_tabs, ["sp500", "btc", "multi"]):
            with tab_widget:
                cfg = MODEL_CONFIGS[model_key]
                with st.spinner(f"{cfg['label']} 계산 중..."):
                    results = compute_model_results(ev_returns, model_key, ticker=ev_ticker)
                kpi = build_kpi_dict(results)
                n_beta = len(cfg["beta_labels"])

                # ── KPI 행 1: 모델 파라미터 ──────────────────────────────────
                param_cols = st.columns(2 + n_beta)
                with param_cols[0]:
                    st.metric("Alpha (일별)", kpi["alpha_pct"])
                for i, (lbl, val) in enumerate(zip(kpi["beta_labels"], kpi["beta_values"])):
                    with param_cols[1 + i]:
                        st.metric(lbl, val)
                with param_cols[1 + n_beta]:
                    st.metric("R²", kpi["r_squared_pct"])

                # ── KPI 행 2: 이벤트 당일 통계 ──────────────────────────────
                stat_cols = st.columns(4)
                with stat_cols[0]:
                    st.metric("이벤트 당일 AR", kpi["ar_event_pct"])
                with stat_cols[1]:
                    st.metric("T-통계량", kpi["t_stat_str"])
                with stat_cols[2]:
                    st.metric("P-value", kpi["p_value_str"])
                with stat_cols[3]:
                    sig_icon = "🟢" if kpi["significant"] else "🔴"
                    st.metric(
                        "통계적 유의성 (p<0.05)",
                        f"{sig_icon} {'유의' if kpi['significant'] else '비유의'}",
                    )

                # ── 차트 ─────────────────────────────────────────────────────
                st.plotly_chart(
                    chart_actual_vs_expected(results),
                    width='stretch',
                    key=f"ev_actual_exp_{model_key}_{ev_ticker}",
                )

                col_car, col_ar = st.columns(2)
                with col_car:
                    st.plotly_chart(
                        chart_car(results),
                        width='stretch',
                        key=f"ev_car_{model_key}_{ev_ticker}",
                    )
                with col_ar:
                    st.plotly_chart(
                        chart_ar_bar(results),
                        width='stretch',
                        key=f"ev_ar_bar_{model_key}_{ev_ticker}",
                    )

                # ── 결론 ─────────────────────────────────────────────────────
                if kpi["significant"]:
                    conclusion = (
                        f"**결론**: 95% 신뢰수준에서 통계적으로 유의미한 이상 수익률이 확인되었습니다. "
                        f"ASC 350-60 발표가 {ti['label']} 주가에 의미 있는 충격을 미쳤다고 판단됩니다."
                    )
                else:
                    conclusion = (
                        f"**결론**: 통계적으로 유의미한 이상 수익률이 발견되지 않았습니다. "
                        f"시장이 해당 발표를 이미 선반영했거나, BTC 가격 변동이 지배적 변수일 가능성이 있습니다."
                    )
                st.info(conclusion, icon="📋")


# ── 인사이트 렌더러 ────────────────────────────────────────────────────────────
def _render_ai_result(text: str):
    """
    인사이트 텍스트를 재무회계 관점에서 시각적으로 강조하여 렌더링.
    - H1/H2/H3 섹션: 색상·배경 구분
    - 수치($, %, 배): 오렌지 강조
    - 핵심 용어(**bold**): 골드 강조
    - 불릿: 아이콘 스타일
    """
    import re as _re

    if not text:
        st.warning("분석 결과가 없습니다.")
        return

    num_pat = _re.compile(
        r"(\$[\d,]+\.?\d*[BMbmKk]?|[+\-]?\d+\.?\d*%|[+\-]?\d+\.?\d*배|[+\-]?\d+\.?\d*x\b)"
    )
    bold_pat = _re.compile(r"\*\*(.*?)\*\*")

    def _hl(s: str) -> str:
        s = num_pat.sub(r'<span style="color:#F4845F;font-weight:700">\1</span>', s)
        s = bold_pat.sub(
            r'<strong style="color:#FFD700;background:#FFD70018;padding:0 3px;border-radius:3px">\1</strong>',
            s,
        )
        return s

    lines = text.split("\n")
    parts = []
    in_ul = False

    for line in lines:
        raw = line.strip()
        if not raw:
            if in_ul:
                parts.append("</ul>")
                in_ul = False
            parts.append('<div style="height:6px"></div>')
            continue

        if raw.startswith("# ") and not raw.startswith("## "):
            if in_ul:
                parts.append("</ul>")
                in_ul = False
            parts.append(
                f'<div style="background:linear-gradient(90deg,#F4845F28,#F4845F08);'
                f'border-left:4px solid #F4845F;padding:12px 16px;margin:22px 0 6px;border-radius:0 6px 6px 0">'
                f'<span style="color:#F4845F;font-size:1.1rem;font-weight:700">{_hl(raw[2:])}</span></div>'
            )
        elif raw.startswith("## "):
            if in_ul:
                parts.append("</ul>")
                in_ul = False
            parts.append(
                f'<div style="background:#141e30;border-left:3px solid #6EA8D0;'
                f'padding:9px 14px;margin:16px 0 5px;border-radius:0 5px 5px 0">'
                f'<span style="color:#6EA8D0;font-size:1.0rem;font-weight:600">{_hl(raw[3:])}</span></div>'
            )
        elif raw.startswith("### "):
            if in_ul:
                parts.append("</ul>")
                in_ul = False
            parts.append(
                f'<div style="color:#2ECC71;font-weight:600;margin:12px 0 3px;font-size:0.93rem">'
                f"▶ {_hl(raw[4:])}</div>"
            )
        elif raw.startswith("- ") or raw.startswith("• ") or raw.startswith("* "):
            if not in_ul:
                parts.append(
                    '<ul style="list-style:none;padding-left:10px;margin:3px 0">'
                )
                in_ul = True
            parts.append(
                f'<li style="padding:4px 0;color:#d0d0d0;line-height:1.65">◆ {_hl(raw[2:])}</li>'
            )
        else:
            if in_ul:
                parts.append("</ul>")
                in_ul = False
            parts.append(
                f'<p style="color:#d0d0d0;margin:5px 0;line-height:1.8;font-size:0.93rem">{_hl(raw)}</p>'
            )

    if in_ul:
        parts.append("</ul>")

    st.markdown(
        f'<div style="background:#0d1117;border:1px solid #2a3050;border-radius:10px;'
        f"padding:22px 26px;font-family:'Noto Sans KR',sans-serif\">"
        + "\n".join(parts)
        + "</div>",
        unsafe_allow_html=True,
    )


# ══════════════════════════════════════════════════════════════════════════════
# TAB AI: 인사이트 (규칙 기반)
# ══════════════════════════════════════════════════════════════════════════════
with tab_ai:
    st.markdown(
        '<div class="section-header"><h2>💡 인사이트 — 데이터 기반 심층 분석</h2></div>',
        unsafe_allow_html=True,
    )

    from modules.insights import (
        generate_eps_insights,
        generate_multi_insights,
        generate_nlp_insights,
        generate_integrated_insights,
    )
    from modules.earnings_simulator import load_holdings, compute_eps
    from modules.multi_company import (
        load_all_holdings,
        compute_all_eps,
        summary_stats,
        chart_btc_holdings_comparison,
        chart_eps_delta_comparison,
        chart_eps_volatility_panel,
        chart_fv_impact_heatmap,
        chart_eps_std_bar,
    )
    from modules.earnings_simulator import (
        chart_eps_comparison,
        chart_fv_gain_loss,
        chart_pre_post_comparison,
        chart_eps_volatility_comparison,
    )

    ai_tabs = st.tabs(
        ["📈 EPS 분석", "🏢 멀티 기업", "📄 공시 언어", "📑 통합 인사이트"]
    )

    # ── EPS 분석 ──────────────────────────────────────────────────────────────
    with ai_tabs[0]:
        st.markdown("#### MSTR EPS 변화 — 분기별 ASC 350-60 영향 분석")
        _holdings_i = load_holdings()
        _eps_i = compute_eps(_holdings_i, btc_prices)

        col_l, col_r = st.columns(2)
        with col_l:
            st.plotly_chart(
                chart_eps_comparison(_eps_i),
                width='stretch',
                key="ins_eps_cmp",
            )
        with col_r:
            st.plotly_chart(
                chart_fv_gain_loss(_eps_i), width='stretch', key="ins_eps_fv"
            )

        st.divider()
        _render_ai_result(generate_eps_insights(_eps_i))

    # ── 멀티 기업 ──────────────────────────────────────────────────────────────
    with ai_tabs[1]:
        st.markdown("#### MSTR / TSLA / MARA — 보유 전략별 ASC 350-60 영향 비교")
        with st.spinner("멀티 기업 데이터 계산 중..."):
            _all_h_i = load_all_holdings()
            _all_e_i = compute_all_eps(_all_h_i, btc_prices)
            _stats_i = summary_stats(_all_e_i)

        col_l, col_r = st.columns(2)
        with col_l:
            st.plotly_chart(
                chart_eps_std_bar(_all_e_i),
                width='stretch',
                key="ins_multi_std",
            )
        with col_r:
            st.plotly_chart(
                chart_btc_holdings_comparison(_all_h_i),
                width='stretch',
                key="ins_multi_holdings",
            )
        st.plotly_chart(
            chart_eps_delta_comparison(_all_e_i),
            width='stretch',
            key="ins_multi_delta",
        )
        st.plotly_chart(
            chart_fv_impact_heatmap(_all_e_i),
            width='stretch',
            key="ins_multi_heatmap",
        )

        st.divider()
        _render_ai_result(generate_multi_insights(_all_e_i, _stats_i))

    # ── 공시 언어 ──────────────────────────────────────────────────────────────
    with ai_tabs[2]:
        st.markdown("#### EDGAR 10-K 공시 언어 분석")
        from modules.edgar_nlp import (
            fetch_company_data as _fetch_nlp_i,
            chart_keyword_heatmap as _chart_kh_i,
            chart_sentiment as _chart_cs_i,
            chart_disclosure_length as _chart_dl_i,
            chart_lm_wordcount as _chart_lm_i,
        )

        nlp_ins_ticker = st.selectbox(
            "기업 선택", ["MSTR", "TSLA", "COIN"], key="ins_nlp_ticker"
        )

        if st.button("공시 언어 분석 실행", key="ins_nlp_btn"):
            with st.spinner(
                f"{nlp_ins_ticker} 10-K NLP 분석 중 (캐시 없을 시 수 분 소요)..."
            ):
                _nlp_i = _fetch_nlp_i(nlp_ins_ticker)
            if _nlp_i is not None and not _nlp_i.empty:
                st.session_state["ins_nlp_df"] = _nlp_i
                st.session_state["ins_nlp_ticker_saved"] = nlp_ins_ticker
            else:
                st.error("NLP 데이터를 불러오지 못했습니다. 인터넷 연결을 확인하세요.")

        if "ins_nlp_df" not in st.session_state:
            st.session_state["ins_nlp_df"] = None
            st.session_state["ins_nlp_ticker_saved"] = None

        if st.session_state["ins_nlp_df"] is not None:
            _nlp_df_i = st.session_state["ins_nlp_df"]
            _nlp_tick_i = st.session_state["ins_nlp_ticker_saved"]

            col_l, col_r = st.columns(2)
            with col_l:
                st.plotly_chart(
                    _chart_kh_i(_nlp_df_i, _nlp_tick_i),
                    width='stretch',
                    key="ins_nlp_heatmap",
                )
            with col_r:
                st.plotly_chart(
                    _chart_cs_i(_nlp_df_i, _nlp_tick_i),
                    width='stretch',
                    key="ins_nlp_sentiment",
                )

            col_l2, col_r2 = st.columns(2)
            with col_l2:
                st.plotly_chart(
                    _chart_dl_i(_nlp_df_i, _nlp_tick_i),
                    width='stretch',
                    key="ins_nlp_length",
                )
            with col_r2:
                st.plotly_chart(
                    _chart_lm_i(_nlp_df_i, _nlp_tick_i),
                    width='stretch',
                    key="ins_nlp_lm",
                )

            st.divider()
            _render_ai_result(generate_nlp_insights(_nlp_df_i, _nlp_tick_i))

    # ── 통합 인사이트 ───────────────────────────────────────────────────────────
    with ai_tabs[3]:
        st.markdown("#### 전체 분석 종합 — 연구 가설 검증 및 핵심 결론")
        with st.spinner("통합 데이터 계산 중..."):
            _holdings_r = load_holdings()
            _eps_r = compute_eps(_holdings_r, btc_prices)
            _all_h_r = load_all_holdings()
            _all_e_r = compute_all_eps(_all_h_r, btc_prices)
            _stats_r = summary_stats(_all_e_r)

        col_l, col_r = st.columns(2)
        with col_l:
            st.plotly_chart(
                chart_pre_post_comparison(_eps_r),
                width='stretch',
                key="ins_full_prepost",
            )
        with col_r:
            st.plotly_chart(
                chart_eps_volatility_comparison(_eps_r),
                width='stretch',
                key="ins_full_vol",
            )

        st.plotly_chart(
            chart_eps_delta_comparison(_all_e_r),
            width='stretch',
            key="ins_full_delta",
        )

        st.divider()
        _nlp_for_full = st.session_state.get("ins_nlp_df")
        _nlp_tick_full = st.session_state.get("ins_nlp_ticker_saved", "MSTR")
        _render_ai_result(
            generate_integrated_insights(
                _eps_r, _all_e_r, _stats_r, _nlp_for_full, _nlp_tick_full
            )
        )

# ══════════════════════════════════════════════════════════════════════════════
# TAB ABOUT: 연구 배경
# ══════════════════════════════════════════════════════════════════════════════
with tab_about:
    st.markdown(
        '<div class="section-header"><h2>ℹ️ 연구 배경 및 방법론</h2></div>',
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(
            """
### 📌 연구 개요
**주제**: ASC 350-60 가상자산 회계 기준이 기업 이익(EPS) 및 공시(Disclosure)에 미치는 영향


**분석 기업**:
- **MicroStrategy (MSTR)**: 전략적 대규모 BTC 보유
- **Tesla (TSLA)**: 단기 투자 후 부분 매각
- **Marathon Digital (MARA)**: BTC 채굴사

---

### 🔄 ASC 350-60 핵심 변화

| 구분 | 구 기준 (원가법) | 신 기준 (ASC 350-60) |
|------|--------------|-------------------|
| 인식 | 취득원가 고정 | 분기말 공정가치 |
| 손익 | 손상만 인식 | 미실현 손익 전액 반영 |
| 적용 | ~2024년 | 2025년 1월 1일~ |
| 변동성 | 낮음 | BTC 가격에 연동 |
"""
        )
    with col2:
        st.markdown(
            """
### 🔬 분석 방법론

**Module B: Earnings Simulator**
- Counterfactual 시뮬레이션: 2020Q4~2024Q4 구간에 ASC 350-60을 소급 적용
- 2025년 실제 적용 결과와 비교 검증
- 3개 기업 패널 분석 (MSTR / TSLA / MARA)

**Module C: EDGAR NLP**
- SEC EDGAR Full-Text Search API로 10-K 수집
- 2019~2024년 공시 언어 정량 분석
- VADER 감성 분석 + 키워드 빈도 추적

---

### 📊 핵심 가설

**H1**: BTC 가격 변동 → EPS 변동 연동 (변동성 증가)

**H2**: 'digital asset', 'fair value' 등 키워드 빈도 증가

**H3**: 강세장 연도(2021, 2024)에서 긍정적 감성 점수

---

### 🛠️ 기술 스택
`Python` · `Streamlit` · `yfinance` · `Plotly` · `NLTK VADER` · `SEC EDGAR API` · `Loughran-McDonald`
"""
        )

    st.divider()
    st.markdown(
        """
### 📁 데이터 출처
- **BTC 가격**: Yahoo Finance (yfinance) — 일별 역사 데이터
- **실시간 BTC**: CoinGecko Simple Price API
- **기업 재무**: yfinance + 수동 수집 분기별 BTC 보유량 공시
- **10-K 공시**: SEC EDGAR Full-Text Search API

### ⚠️ 분석 한계
- 2025년 이후 실제 적용 데이터는 공시 시점에 따라 추정치 포함
- MARA/TSLA 데이터는 공개 자료 기반 수동 수집
- NLP 분석은 EDGAR 캐시 데이터에 의존 (인터넷 필요)
"""
    )
