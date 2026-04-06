"""
ai_analyst.py — OpenAI GPT 기반 회계 인사이트 분석
모델/파라미터는 config.py에서 관리합니다.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import OPENAI_MODEL, OPENAI_MAX_TOKENS, OPENAI_TEMPERATURE


def get_openai_client(api_key: str):
    try:
        from openai import OpenAI

        return OpenAI(api_key=api_key)
    except ImportError:
        return None


def _chat(
    client, prompt: str, max_tokens: int = None, temperature: float = None
) -> str:
    kwargs = dict(
        model=OPENAI_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=temperature if temperature is not None else OPENAI_TEMPERATURE,
    )
    tokens = max_tokens or OPENAI_MAX_TOKENS
    try:
        resp = client.chat.completions.create(**kwargs, max_completion_tokens=tokens)
    except Exception:
        resp = client.chat.completions.create(**kwargs, max_tokens=tokens)
    return resp.choices[0].message.content


# ── 상세 통합 리포트 (PDF용) ────────────────────────────────────────────────────


def generate_full_report(api_key: str, context: dict) -> str:
    """
    모든 분석 결과를 종합한 상세 학술 리포트 생성.
    context 키:
      eps_rows      : MSTR EPS 분기별 데이터 리스트
      multi_stats   : 멀티 기업 통계 (MSTR/TSLA/MARA)
      nlp_rows      : EDGAR NLP 키워드/감성 데이터
      btc_volatility: BTC 연환산 변동성 (%)
      sim_eps_std   : 소급 시뮬레이션 EPS 표준편차
      actual_eps_std: 실제 ASC 350-60 EPS 표준편차
    """
    client = get_openai_client(api_key)
    if not client:
        return "openai 패키지가 설치되지 않았습니다."

    eps_rows = "\n".join(
        [
            f"  {r['quarter']}: 구기준 ${r['old_eps']:.1f} / ASC350-60 ${r['new_eps']:.1f} "
            f"(Δ${r['eps_delta']:+.1f}, FV손익 ${r['fair_value_gain_loss']/1e6:.0f}M)"
            for r in context.get("eps_rows", [])
        ]
    )

    multi = context.get("multi_stats", {})
    multi_rows = "\n".join(
        [
            f"  {t}: BTC {multi.get(t,{}).get('btc_max','N/A')}, "
            f"EPS변동성증가 {multi.get(t,{}).get('vol_inc','N/A')}, "
            f"누적FV손익 {multi.get(t,{}).get('total_fv','N/A')}"
            for t in ["MSTR", "TSLA", "MARA"]
        ]
    )

    nlp_rows = "\n".join(
        [
            f"  {r['year']}: 'digital asset' {r.get('kw_digital_asset',0)}회, "
            f"'fair value' {r.get('kw_fair_value',0)}회, "
            f"sentiment {r.get('sentiment_compound',0):.3f}, 길이 {r.get('section_length',0):,}자"
            for r in context.get("nlp_rows", [])
        ]
    )

    prompt = f"""당신은 미국 GAAP 및 가상자산 회계 전문가입니다.

## 주제
ASC 350-60 가상자산 회계 기준이 기업 이익(EPS) 및 공시(Disclosure)에 미치는 영향

## 분석 방법론
- **Counterfactual 시뮬레이션**: 2020Q4~2024Q4 구간에 ASC 350-60을 소급 적용해 EPS 변화 역산
- **실제 적용 비교**: 2025년 의무 적용 후 실제 공시 EPS와 비교 검증
- **멀티 기업 패널 분석**: MSTR(대규모 보유) / TSLA(단기 투자) / MARA(채굴사) 비교
- **EDGAR NLP**: 2019~2024 10-K 공시 언어 정량 분석

## 핵심 데이터

### [1] MSTR EPS 분기별 데이터
{eps_rows}

### [2] 멀티 기업 비교 (MSTR / TSLA / MARA)
{multi_rows}

### [3] MSTR 10-K 공시 NLP 분석 (2019~2024)
{nlp_rows}

### [4] 시장 환경
- BTC 연환산 변동성: {context.get('btc_volatility', 70):.1f}%
- 소급 시뮬레이션 EPS 표준편차(MSTR): ${context.get('sim_eps_std', 0):.1f}
- 실제 ASC 350-60 EPS 표준편차(MSTR): ${context.get('actual_eps_std', 0):.1f}

---

## 보고서 형식 (반드시 아래 구조 준수, 마크다운 사용)

# 1. 연구 개요
(연구 목적, 배경, 방법론 요약 — 3~4문장)

## 1.1 ASC 350-60 기준 변화의 핵심
(구 기준 원가법 vs 신 기준 공정가치법 차이를 구체적으로 설명)

# 2. 연구 가설 및 검증

## H1: EPS 변동성 가설
(BTC 가격 변동 → EPS 변동 연동 여부, 구체적 수치로 검증)

## H2: 공시 언어 변화 가설
(키워드 빈도 증가 추이를 수치로 검증)

## H3: 감성 점수 가설
(강세장 연도의 sentiment 변화 검증)

# 3. 멀티 기업 비교 분석
(MSTR / TSLA / MARA 세 기업의 BTC 보유 전략 차이와 ASC 350-60 영향 크기 비교.
보유량 규모, 사업 목적, EPS 변동성 증가폭의 차이를 분석)

# 4. Counterfactual 시뮬레이션 vs 실제 적용 비교
(소급 시뮬레이션 예측과 2025년 실제 적용 결과가 얼마나 일치했는지 평가)

# 5. 회계적·투자적 함의

## 5.1 재무제표 비교가능성
## 5.2 투자자 의사결정에 미치는 영향
## 5.3 경영진 성과 평가 왜곡 가능성

# 6. 연구의 한계 및 향후 과제

# 7. 결론
(핵심 발견 3가지를 bullet point로, 마지막 종합 결론 2문장)

---
각 섹션은 충분히 상세하게 (전체 2,500자 이상), 학술 보고서 수준의 한국어로 작성하세요.
수치를 적극 활용하고, 가능하면 구체적인 EPS 수치나 키워드 빈도를 인용하세요."""

    try:
        return _chat(client, prompt, max_tokens=4000, temperature=0.3)
    except Exception as e:
        return f"GPT 분석 실패: {e}"


# ── 개별 분석 함수 (탭별 빠른 분석용) ─────────────────────────────────────────


def analyze_eps_impact(api_key: str, eps_data: list) -> str:
    client = get_openai_client(api_key)
    if not client:
        return "openai 패키지가 설치되지 않았습니다."

    rows = "\n".join(
        [
            f"- {r['quarter']}: 구기준 ${r['old_eps']:.2f} / ASC350-60 ${r['new_eps']:.2f} "
            f"(Δ${r['eps_delta']:+.2f}, FV손익 ${r['fair_value_gain_loss']/1e6:.1f}M, BTC ${r['btc_price_end']:,.0f})"
            for r in eps_data
        ]
    )
    prompt = f"""당신은 미국 GAAP 회계 전문가입니다.
[방법론] 2024년 이전: 구기준 = 실제공시, ASC350-60 = 소급시뮬레이션 / 2025년 이후: ASC350-60 = 실제공시

[MSTR 분기별 EPS]
{rows}

다음을 구체적 수치와 함께 한국어로 분석해주세요 (5~6문단):
1. EPS 변동성과 BTC 가격 연동 패턴 (특히 급등/급락 분기)
2. 구 기준 vs ASC 350-60의 이익 측정 철학 차이
3. 소급 시뮬레이션과 2025 실제 적용 결과 비교
4. 투자자·채권자·경영진 각 관점의 시사점
5. 비교가능성(comparability) 훼손 가능성"""
    try:
        return _chat(client, prompt, max_tokens=1500)
    except Exception as e:
        return f"GPT 분석 실패: {e}"


def analyze_multi_company(api_key: str, stats: list) -> str:
    client = get_openai_client(api_key)
    if not client:
        return "openai 패키지가 설치되지 않았습니다."

    rows = "\n".join(
        [
            f"- {r['기업']}: BTC {r['최대 BTC 보유']}, "
            f"구기준 EPS σ={r['구기준 EPS 표준편차']}, "
            f"ASC350-60 EPS σ={r['ASC350-60 EPS 표준편차']}, "
            f"변동성증가={r['변동성 증가율']}, 누적FV={r['누적 공정가치 손익']}"
            for r in stats
        ]
    )
    prompt = f"""당신은 기업 재무 비교 분석 전문가입니다.
다음은 BTC를 보유한 3개 기업의 ASC 350-60 영향 비교 데이터입니다.

[데이터]
{rows}

다음을 한국어로 분석하세요 (5~6문단):
1. 세 기업의 BTC 보유 전략 차이 (대규모 보유 / 단기 투자 / 채굴)
2. 보유량 규모에 따른 EPS 변동성 차이가 왜 발생하는지
3. TSLA처럼 BTC를 매각한 기업과 MSTR처럼 계속 보유한 기업의 회계처리 결과 차이
4. ASC 350-60이 세 기업 중 어느 기업에 가장 큰 영향을 미쳤고 그 이유
5. 이 비교가 ASC 350-60의 보편적 영향을 실증하는 데 어떤 의의가 있는지"""
    try:
        return _chat(client, prompt, max_tokens=1500)
    except Exception as e:
        return f"GPT 분석 실패: {e}"


def analyze_disclosure_trend(api_key: str, ticker: str, nlp_data: list) -> str:
    client = get_openai_client(api_key)
    if not client:
        return "openai 패키지가 설치되지 않았습니다."

    rows = "\n".join(
        [
            f"- {r['year']}: digital asset {r.get('kw_digital_asset',0)}회, "
            f"fair value {r.get('kw_fair_value',0)}회, "
            f"impairment {r.get('kw_impairment',0)}회, "
            f"감성={r.get('sentiment_compound',0):.3f}, 길이={r.get('section_length',0):,}자"
            for r in nlp_data
        ]
    )
    prompt = f"""당신은 SEC 공시 분석 전문가입니다.
다음은 {ticker}의 연도별 10-K NLP 분석 데이터입니다.

[데이터]
{rows}

다음을 학술적 한국어로 분석하세요 (5~6문단):
1. 키워드 빈도 연도별 증가 추이와 FASB ASC 350-60 논의 타임라인과의 연관성
2. 'fair value'와 'impairment' 비율 변화가 의미하는 회계 패러다임 전환
3. 감성 점수와 BTC 시장 강세장(2021, 2024) 관계
4. 공시 분량 증가가 투자자 정보비대칭 해소에 기여했는지 평가
5. 이 기업의 공시 품질이 ASC 350-60 도입 전후로 어떻게 변했을지 전망"""
    try:
        return _chat(client, prompt, max_tokens=1500)
    except Exception as e:
        return f"GPT 분석 실패: {e}"
