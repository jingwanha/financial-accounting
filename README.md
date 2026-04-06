# ASC 350-60 가상자산 회계 기준 영향 분석 대시보드

> KAIST 디지털금융 MBA | 재무회계 | Spring 2026

ASC 350-60(가상자산 공정가치 회계 기준)이 비트코인 보유 기업의 **EPS(주당순이익)** 및 **공시 언어**에 미치는 영향을 정량 분석하는 인터랙티브 대시보드입니다.

---

## 연구 배경

미국 FASB는 2025년 1월 1일부터 **ASC 350-60**을 의무 적용했습니다.

| 구분 | 구 기준 (원가법, ~2024) | 신 기준 (ASC 350-60, 2025~) |
|------|----------------------|--------------------------|
| 이익 인식 | 손상(가격 하락)만 인식 | 분기말 공정가치 변동 전액 반영 |
| BTC 상승 시 | 이익 미인식 (팔아야 인식) | 미실현 평가이익 즉시 반영 |
| BTC 하락 시 | 손상차손 인식 | 미실현 평가손실 즉시 반영 |
| EPS 변동성 | 낮음 | BTC 가격에 직접 연동 |

이 변화가 실제로 기업 이익에 얼마나 영향을 주는지 **Counterfactual 시뮬레이션**으로 측정합니다.

---

## 분석 대상 기업

| 기업 | 전략 | 특징 |
|------|------|------|
| **MSTR** (Strategy Inc.) | 전략적 대규모 보유 | 최대 634,090 BTC 보유, ASC 350-60 영향 가장 큼 |
| **TSLA** (Tesla) | 단기 투자 후 부분 매각 | 2022Q2에 보유량 75% 매각, 이후 9,720 BTC 유지 |
| **MARA** (MARA Holdings) | 채굴 후 보유 (Miner) | 채굴 사업자, BTC 보유량 꾸준히 증가 |

---

## 연구 가설

- **H1**: BTC 가격 변동 → EPS 변동성 증가 (변동성 비례 가설)
- **H2**: 'digital asset', 'fair value' 등 키워드 빈도 증가 (공시 언어 변화 가설)
- **H3**: BTC 강세장 연도(2021, 2024)에서 긍정적 감성 점수 (감성 점수 가설)

---

## 프로젝트 구조

```
financial_accounting/
│
├── app.py                          # Streamlit 메인 앱
├── config.py                       # 전역 설정 (분석 파라미터)
├── requirements.txt
│
├── data/
│   ├── mstr_holdings.csv           # MSTR 분기별 BTC 보유 데이터
│   ├── tsla_holdings.csv           # TSLA 분기별 BTC 보유 데이터
│   ├── mara_holdings.csv           # MARA 분기별 BTC 보유 데이터
│   └── README.md                   # 데이터 출처 및 컬럼 상세 설명
│
├── modules/
│   ├── data_fetcher.py             # BTC/주가 API 수집 (yfinance, CoinGecko)
│   ├── earnings_simulator.py       # EPS 계산 엔진 + 시각화
│   ├── multi_company.py            # 3개 기업 비교 분석
│   ├── edgar_nlp.py                # SEC EDGAR 10-K NLP 분석
│   ├── insights.py                 # 규칙 기반 인사이트 텍스트 생성
│   └── __init__.py
│
└── scripts/
    └── fetch_official_data.py      # CSV 데이터 재생성 스크립트
```

---

## 데이터 설계 원칙

### CSV에 저장하는 데이터 vs API에서 가져오는 데이터

| 데이터 종류 | 저장 위치 | 이유 |
|-----------|---------|------|
| BTC 보유량, 취득원가 | CSV (정적) | SEC 공시 확정값 — 변하지 않음, 자동 수집 불가 |
| 발행 주식 수, 순이익 | CSV (정적) | SEC 공시 확정값 |
| BTC 일별 가격 | yfinance API (런타임) | 매일 갱신, 무료 API로 자동 수집 가능 |
| 주가 (MSTR/TSLA 등) | yfinance API (런타임) | 동일 이유 |
| 현재 BTC 가격 | CoinGecko API (실시간) | 5분 캐시, 실시간 조회 |

> **핵심 원칙**: 바뀌지 않는 공시 데이터(CSV)와 항상 최신이어야 하는 시장 데이터(API)를 명확하게 분리합니다.

### CSV 컬럼 설명

| 컬럼 | 단위 | 출처 | 설명 |
|------|------|------|------|
| `quarter` | - | 파생 | 분기 식별자 (예: `2024Q3`) |
| `date` | YYYY-MM-DD | 파생 | 분기 말일 (Q1=03-31, Q2=06-30, Q3=09-30, Q4=12-31) |
| `btc_holdings` | BTC 개수 | SEC EDGAR 수동 수집 | 해당 분기 말 보유 BTC 수량 |
| `avg_cost_usd` | USD/BTC | SEC EDGAR 수동 수집 | 가중평균 취득원가 (cost basis) |
| `shares_outstanding` | 주 | yfinance 자동 수집 | 분기 말 발행 주식 수 |
| `reported_net_income_usd` | USD | yfinance 자동 수집 | GAAP 당기순이익 |
| `is_actual_asc360` | True/False | 파생 | 2025Q1 이후 True (실제 적용 구간) |

### `is_actual_asc360` 플래그의 역할

이 컬럼이 EPS 계산 엔진의 핵심 분기점입니다.

```
is_actual_asc360 = False (~2024Q4)
  → reported_net_income = 구 기준(원가법) 실제 공시값
  → ASC 350-60 EPS = (순이익 + BTC 공정가치 변동) ÷ 주식 수  [소급 시뮬레이션]

is_actual_asc360 = True (2025Q1~)
  → reported_net_income = ASC 350-60 실제 공시값
  → 구 기준 EPS = (순이익 − BTC 공정가치 변동) ÷ 주식 수   [역산 추정]
```

### EPS 계산 흐름

```
[CSV] btc_holdings
         ×
[API]  BTC 분기말 가격 차이 (yfinance)
         ↓
  공정가치 손익 = 보유량 × (이번 분기말 가격 − 전분기말 가격)
         ↓
  ASC 350-60 순이익 = 공시 순이익 ± 공정가치 손익
         ÷
[CSV] shares_outstanding
         ↓
  EPS (구 기준 / ASC 350-60)
```

---

## 실행 방법

### 1. 의존성 설치

```bash
pip install -r requirements.txt
```

### 2. NLTK 리소스 다운로드 (최초 1회)

```bash
python -c "import nltk; nltk.download('vader_lexicon')"
```

### 3. Streamlit 실행

```bash
streamlit run app.py
```

브라우저에서 `http://localhost:8501` 접속

### 4. (선택) CSV 데이터 재생성

yfinance에서 최신 재무 데이터를 다시 수집하려면:

```bash
python scripts/fetch_official_data.py
```

> BTC 보유량(`btc_holdings`)과 취득원가(`avg_cost_usd`)는 SEC EDGAR 수동 수집 항목으로, 스크립트 내 딕셔너리를 직접 수정해야 합니다.

---

## 화면 구성 (6개 탭)

### 📊 탭 1: EPS 시뮬레이터

MSTR의 분기별 EPS를 두 기준(구 기준 vs ASC 350-60)으로 비교합니다.

| 구성 요소 | 설명 |
|---------|------|
| KPI 카드 | 평균/최대 EPS 차이, 변동성 증가율, 현재 BTC 가격 |
| EPS 비교 차트 | 구 기준(파랑) vs ASC 350-60(주황) 막대 + EPS 차이 색상 막대 |
| 공정가치 손익 | 분기별 BTC 평가 이익(초록)/손실(빨강), 금액 직접 표시 |
| Sensitivity 슬라이더 | BTC -80%~+200% 변동 시 EPS 실시간 시뮬레이션 |
| 변동성 차트 | BTC 30일/90일 롤링 연환산 변동성 추이 |
| 상관관계 산점도 | BTC 수익률 vs MSTR 주가 수익률, 회귀선 및 상관계수(r) |
| 분기별 상세 테이블 | BTC 시가/종가, 보유량, FV 손익, 구기준/신기준 EPS |

---

### ⚖️ 탭 2: 전후 비교 (핵심)

소급 시뮬레이션(~2024)과 실제 적용(2025~)의 결과를 비교 검증합니다.

| 구성 요소 | 설명 |
|---------|------|
| KPI 카드 | 소급/실제 적용 기간(분기 수), 각 구간 EPS 변동성 비율 |
| 핵심 비교 차트 | 3가지 선(구기준/시뮬레이션/실제) + 2025Q1 경계선 수직 표시, 하단에 FV 손익 |
| EPS 분포 박스플롯 | 구기준/시뮬레이션/실제 3개 박스 — 높이가 변동성 크기 |
| 시뮬레이션 검증 차트 | 2025 실제 EPS vs 구기준 역산 EPS 나란히 비교 |
| 전체 분기 테이블 | 소급/실제 구분 컬럼 포함 전 분기 EPS 데이터 |

---

### 🏢 탭 3: 멀티 기업 비교

MSTR / TSLA / MARA 세 기업의 BTC 보유 전략별 ASC 350-60 영향 크기를 비교합니다.

| 구성 요소 | 설명 |
|---------|------|
| 핵심 통계 테이블 | 최대 BTC 보유량, 구기준/ASC 기준 EPS 표준편차, 변동성 증가율, 누적 FV 손익 |
| BTC 보유량 추이 | 3개 기업 선 그래프 — 전략 차이가 시각적으로 드러남 |
| EPS 표준편차 비교 | 구기준 vs ASC 기준 표준편차를 기업별로 나란히 비교 |
| EPS 차이 비교 | 3개 기업의 분기별 EPS 차이를 그룹 막대로 비교 |
| EPS 박스플롯 | 기업별 구기준/ASC 기준 EPS 분포 비교 |
| 공정가치 히트맵 | 기업(행) × 분기(열) 공정가치 손익, 색상 강도로 금액 표현 |

---

### 🔍 탭 4: EDGAR NLP 분석

SEC EDGAR에서 10-K 연간 보고서를 직접 다운로드해 공시 언어 변화를 정량 분석합니다.  
분석 대상: MSTR / TSLA / COIN (Coinbase), 2019~2024년

| 구성 요소 | 설명 |
|---------|------|
| KPI 카드 | 최근 연도 'digital asset'·'fair value' 언급 횟수, LM 감성 점수 |
| 키워드 히트맵 | 연도(열) × 키워드(행), 10,000단어당 빈도, 진할수록 많이 언급 |
| 감성 분석 차트 | LM Compound 점수(주황 실선) + 긍/부정 비율 막대 + VADER 보조선 |
| 공시 분량 차트 | 암호화폐 섹션 총 글자수(막대) + 관련 단락 수(선), 이중 Y축 |
| LM 단어 수 차트 | 긍정어/부정어 절대 개수 연도별 추이 |
| NLP 데이터 테이블 | 연도별 키워드 빈도, 감성 점수, 섹션 길이 수치 |

> **LM 사전을 사용하는 이유**: 일반용 VADER는 'liability(부채)'를 중립으로 분류하지만, Loughran-McDonald 금융 사전은 재무 공시에 최적화되어 있습니다.

---

### 💡 탭 5: 인사이트

데이터에서 직접 계산한 규칙 기반 인사이트를 차트와 함께 표시합니다. (GPT 불필요)

| 서브탭 | 차트 | 인사이트 내용 |
|--------|------|-------------|
| 📈 EPS 분석 | EPS 비교 + FV 손익 | BTC-EPS 상관계수, 변동성 비율, 소급 vs 실제 비교, 투자자 시사점 |
| 🏢 멀티 기업 | EPS 표준편차·보유량·델타·히트맵 | 3사 전략 비교표, 보유 규모별 영향 크기 |
| 📄 공시 언어 | 키워드 히트맵·감성·분량·LM 차트 | 키워드 증가율, 감성 추이, H2 가설 검증 |
| 📑 통합 인사이트 | 전후비교·변동성·델타 | H1/H2/H3 가설 검증 종합, 핵심 결론 |

**인사이트 텍스트 렌더링 규칙**:
- 주황색: `$`, `%`, `x`가 붙은 수치 자동 강조
- 금색 배경: `**굵은 텍스트**` 핵심 용어 강조
- 섹션 헤더별 색상 계층 (주황 H1 / 파랑 H2 / 초록 H3)

---

### ℹ️ 탭 6: 연구 배경

연구 목적, 방법론, 가설, 데이터 출처, 분석 한계를 설명합니다.

---

## 모듈별 역할

### `data_fetcher.py`

```python
fetch_btc_price_history()      # yfinance BTC 일별 종가 (전체 이력, 1시간 캐시)
fetch_btc_current_price()      # CoinGecko 실시간 BTC 가격 (5분 캐시)
fetch_stock_history(ticker)    # yfinance 주가 (MSTR/TSLA/COIN 등)
get_quarter_end_price(df, date)# 분기말 날짜에 가장 가까운 BTC 가격 반환
compute_daily_eps_series(...)  # 일별 BTC 가격 기반 EPS 변동 시계열
compute_rolling_volatility(...)# BTC 롤링 변동성 (30일/90일)
```

### `earnings_simulator.py`

```python
load_holdings()                # mstr_holdings.csv 로드
compute_eps(df, btc_prices)    # 구 기준 / ASC 350-60 EPS 계산
apply_sensitivity(df, pct)     # BTC 가격 X% 변동 시 EPS 시뮬레이션
chart_eps_comparison()         # EPS 비교 막대 차트
chart_fv_gain_loss()           # 공정가치 손익 차트
chart_sensitivity()            # Sensitivity 차트
chart_volatility()             # BTC 변동성 차트
chart_btc_stock_correlation()  # BTC-주가 상관관계 산점도
chart_pre_post_comparison()    # 소급 시뮬레이션 vs 실제 비교 (핵심 차트)
chart_eps_volatility_comparison() # EPS 변동성 박스플롯
chart_simulation_accuracy()    # 시뮬레이션 정확도 검증
```

### `multi_company.py`

```python
load_all_holdings()            # 3개 기업 CSV 일괄 로드
compute_all_eps()              # 3개 기업 EPS 계산 후 합산
summary_stats()                # 핵심 통계 요약 테이블 생성
chart_btc_holdings_comparison()# 보유량 추이 비교 선 그래프
chart_eps_delta_comparison()   # EPS 차이 비교 그룹 막대
chart_eps_volatility_panel()   # EPS 분포 박스플롯
chart_fv_impact_heatmap()      # 공정가치 손익 히트맵
chart_eps_std_bar()            # EPS 표준편차 비교 막대
```

### `edgar_nlp.py`

```python
fetch_company_data(ticker)     # EDGAR 10-K 다운로드 + NLP 분석 (24시간 캐시)
chart_keyword_heatmap()        # 키워드 빈도 히트맵
chart_sentiment()              # LM 감성 분석 차트
chart_disclosure_length()      # 공시 분량 차트
chart_lm_wordcount()           # LM 긍/부정어 개수 차트
```

### `insights.py`

```python
generate_eps_insights(eps_df)               # MSTR EPS 인사이트 텍스트
generate_multi_insights(all_eps, stats_df)  # 3사 비교 인사이트 텍스트
generate_nlp_insights(nlp_df, ticker)       # 공시 언어 인사이트 텍스트
generate_integrated_insights(...)           # 통합 연구 결론 텍스트
```

---

## 데이터 출처

| 데이터 | 출처 | 수집 방법 |
|--------|------|---------|
| BTC 일별 가격 | Yahoo Finance (yfinance) | 자동 (API) |
| BTC 실시간 가격 | CoinGecko | 자동 (API) |
| 주가 (MSTR/TSLA/MARA) | Yahoo Finance (yfinance) | 자동 (API) |
| BTC 보유량, 취득원가 | SEC EDGAR 10-K/10-Q Notes | 수동 수집 |
| 발행 주식 수, 순이익 | Yahoo Finance (yfinance) | 자동 (API, fallback 테이블 병행) |
| 10-K 공시 텍스트 | SEC EDGAR Full-Text API | 자동 (API, 24시간 캐시) |

> BTC 보유량은 GAAP XBRL 표준 항목이 아니라 주석(Note)에 텍스트로만 공시되므로 자동 수집이 불가합니다.  
> 각 데이터의 SEC 공시 출처(파일 날짜, Note 번호)는 `data/README.md`를 참조하세요.

---

## 알려진 데이터 주의사항

| 항목 | 내용 |
|------|------|
| MSTR 주식 분할 | 2024년 8월 1일 10:1 분할 — CSV의 `shares_outstanding`은 각 시점 실제 발행주식수 (분할 조정값 아님) |
| MARA 2025Q2~Q4 BTC 보유량 | 실제 공시 미확정 — 추정치 사용, 실제 공시 확인 후 수동 교체 필요 |
| TSLA 주식 분할 | 2022년 8월 25일 3:1 분할 — CSV는 각 시점 실제 발행주식수 적용 |

---

## 기술 스택

`Python 3.10+` · `Streamlit` · `Pandas` · `NumPy` · `Plotly` · `yfinance` · `BeautifulSoup4` · `NLTK VADER` · `Loughran-McDonald 금융 사전` · `SEC EDGAR API` · `CoinGecko API`
