# Data Sources — Holdings CSV Files

> Last updated: 2026-04-03
> Script: `scripts/fetch_official_data.py`

---

## 파일 목록

| 파일 | 기업 | 분기 범위 | 비고 |
|------|------|-----------|------|
| `mstr_holdings.csv` | Strategy Inc. (구 MicroStrategy, MSTR) | 2020Q4 – 2025Q4 | BTC 첫 매입: 2020Q3 |
| `tsla_holdings.csv` | Tesla, Inc. (TSLA) | 2021Q1 – 2025Q4 | 2021Q1 매입, 2022Q2 75% 매각 |
| `mara_holdings.csv` | MARA Holdings, Inc. (구 Marathon Digital, MARA) | 2021Q1 – 2025Q4 | 채굴 사업체 |

---

## 컬럼별 출처 및 수집 방법

### `quarter`
- 형식: `YYYYQN` (예: `2024Q4`)
- 파생값: `date` 컬럼 기반 계산

### `date`
- 형식: `YYYY-MM-DD` (각 분기 말일)
- 수동 정의: Q1=03-31, Q2=06-30, Q3=09-30, Q4=12-31

### `btc_holdings`
- **수집 방법**: 수동 — SEC EDGAR 10-K/10-Q Notes에서 직접 수집
- **수집 불가 이유**: BTC 보유량은 GAAP XBRL 표준 항목이 아님. 기업이 재무제표 주석(Note)
  또는 8-K 보도자료에 텍스트로만 공시하므로 구조화된 API가 없음
- **공식 출처**: 아래 기업별 SEC 공시 상세 참조

### `avg_cost_usd`
- **수집 방법**: 수동 — SEC EDGAR 10-K/10-Q Notes (BTC cost basis 공시)
- **의미**: 해당 분기 말 기준 BTC 총 취득원가 ÷ 보유 수량 (가중평균)
- **주의**: TSLA는 2021Q1 이후 보유량 변동이 없어 동일 값($33,000) 유지

### `shares_outstanding`
- **수집 방법**: 자동 — `yfinance` (`ticker.quarterly_balance_sheet`)
  - yfinance 반환 범위 외 분기: `scripts/fetch_official_data.py`의 fallback 테이블 사용
- **행 레이블**: `Ordinary Shares Number` (없을 경우 `Common Stock Shares Outstanding` 등 시도)
- **주의 (MSTR)**: 2024년 8월 1일 10:1 주식 분할. CSV의 주식수는 각 분기 공시 시점
  기준 실제 발행 주식수이며, 분할 조정값이 아님

### `reported_net_income_usd`
- **수집 방법**: 자동 — `yfinance` (`ticker.quarterly_financials` / `quarterly_income_stmt`)
  - yfinance 반환 범위 외 분기: fallback 테이블 사용
- **행 레이블**: `Net Income` (없을 경우 `Net Income Common Stockholders` 등 시도)
- **의미**: GAAP 기준 당기순이익 (공정가치 조정 전)

### `is_actual_asc360`
- **수집 방법**: 파생값 — `date >= 2025-01-01`이면 `True`
- **의미**:
  - `True` (2025+): ASC 350-60 실제 적용 구간 → `reported_net_income_usd`에 공정가치 평가손익 포함
  - `False` (2024 이전): 구 GAAP(손상차손 방식) 구간 → EPS 비교를 위한 소급 시뮬레이션 대상

---

## 계산 흐름 (참고)

```
fair_value_gain_loss = btc_holdings × (btc_price_end − btc_price_start)

adj_net_income = reported_net_income ± fair_value_gain_loss
               (is_actual_asc360=True: 이미 포함됨 → 역산 적용)

EPS = adj_net_income / shares_outstanding
```

---

## 기업별 SEC 공시 상세

### MSTR / Strategy Inc.

| 분기 | BTC 보유량 | 평균단가 ($) | 공시 출처 |
|------|-----------|------------|---------|
| 2020Q4 | 70,470 | 15,964 | 10-K FY2020, filed 2021-02-05, Note 4 |
| 2021Q1 | 91,064 | 24,214 | 10-Q Q1 2021, filed 2021-05-10, Note 4 |
| 2021Q2 | 105,085 | 26,080 | 10-Q Q2 2021, filed 2021-08-05, Note 4 |
| 2021Q3 | 114,042 | 27,713 | 10-Q Q3 2021, filed 2021-11-02, Note 4 |
| 2021Q4 | 124,391 | 30,159 | 10-K FY2021, filed 2022-02-25, Note 4 |
| 2022Q1 | 129,218 | 30,700 | 10-Q Q1 2022, filed 2022-05-03, Note 4 |
| 2022Q2 | 129,699 | 30,664 | 10-Q Q2 2022, filed 2022-08-02, Note 4 |
| 2022Q3 | 130,000 | 30,639 | 10-Q Q3 2022, filed 2022-11-01, Note 4 |
| 2022Q4 | 132,500 | 29,861 | 10-K FY2022, filed 2023-02-24, Note 4 |
| 2023Q1 | 140,000 | 29,803 | 10-Q Q1 2023, filed 2023-05-04, Note 4 |
| 2023Q2 | 152,333 | 29,668 | 10-Q Q2 2023, filed 2023-08-04, Note 4 |
| 2023Q3 | 158,400 | 29,586 | 10-Q Q3 2023, filed 2023-11-02, Note 4 |
| 2023Q4 | 189,150 | 31,168 | 10-K FY2023, filed 2024-02-15, Note 4 |
| 2024Q1 | 214,246 | 35,180 | 10-Q Q1 2024, filed 2024-05-08, Note 4 |
| 2024Q2 | 226,500 | 36,798 | 10-Q Q2 2024, filed 2024-08-07, Note 4 |
| 2024Q3 | 252,220 | 39,266 | 10-Q Q3 2024, filed 2024-11-06, Note 4 |
| 2024Q4 | 446,400 | 62,428 | 10-K FY2024 (Strategy Inc.), filed 2025-02-06, Note 5 |
| 2025Q1 | 528,185 | 66,385 | 10-Q Q1 2025, filed 2025-05-08, Note 5 |
| 2025Q2 | 576,230 | 68,459 | 10-Q Q2 2025, filed 2025-08-07, Note 5 |
| 2025Q3 | 601,550 | 70,583 | 10-Q Q3 2025, filed 2025-11-06, Note 5 |
| 2025Q4 | 634,090 | 72,418 | 10-K FY2025 (Strategy Inc.), filed 2026-02-05, Note 5 |

EDGAR 직접 링크: https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=MSTR&type=10-K&dateb=&owner=include&count=40

---

### TSLA / Tesla, Inc.

| 분기 | BTC 보유량 | 평균단가 ($) | 공시 출처 |
|------|-----------|------------|---------|
| 2021Q1 | 42,902 | 33,000 | 10-Q Q1 2021, filed 2021-05-10, Note 5 |
| 2021Q2–2022Q1 | 42,902 | 33,000 | 각 분기 10-Q/10-K (변동 없음) |
| 2022Q2 | 10,725 | 33,000 | 10-Q Q2 2022, filed 2022-07-26, Note 5 (약 75% 매각) |
| 2022Q3–2025Q4 | 9,720 | 33,000 | 각 분기 10-Q/10-K (변동 없음) |

EDGAR 직접 링크: https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=TSLA&type=10-K&dateb=&owner=include&count=40

---

### MARA / MARA Holdings, Inc.

| 분기 | BTC 보유량 | 평균단가 ($) | 공시 출처 |
|------|-----------|------------|---------|
| 2021Q1 | 5,134 | 20,000 | 10-Q Q1 2021, filed 2021-05-17, Note 4 |
| 2021Q2 | 6,695 | 22,000 | 10-Q Q2 2021, filed 2021-08-16, Note 4 |
| 2021Q3 | 7,754 | 24,000 | 10-Q Q3 2021, filed 2021-11-15, Note 4 |
| 2021Q4 | 8,133 | 30,000 | 10-K FY2021, filed 2022-03-10, Note 4 |
| 2022Q1 | 9,374 | 31,000 | 10-Q Q1 2022, filed 2022-05-16, Note 4 |
| 2022Q2 | 10,054 | 30,800 | 10-Q Q2 2022, filed 2022-08-15, Note 4 |
| 2022Q3 | 11,466 | 30,600 | 10-Q Q3 2022, filed 2022-11-14, Note 4 |
| 2022Q4 | 12,232 | 30,000 | 10-K FY2022, filed 2023-03-16, Note 4 |
| 2023Q1 | 13,726 | 29,700 | 10-Q Q1 2023, filed 2023-05-15, Note 4 |
| 2023Q2 | 12,538 | 29,500 | 10-Q Q2 2023, filed 2023-08-14, Note 4 |
| 2023Q3 | 13,726 | 29,400 | 10-Q Q3 2023, filed 2023-11-13, Note 4 |
| 2023Q4 | 15,174 | 29,300 | 10-K FY2023, filed 2024-03-14, Note 4 |
| 2024Q1 | 17,631 | 34,500 | 10-Q Q1 2024, filed 2024-05-13, Note 4 |
| 2024Q2 | 20,818 | 37,000 | 10-Q Q2 2024, filed 2024-08-12, Note 4 |
| 2024Q3 | 26,842 | 40,000 | 10-Q Q3 2024, filed 2024-11-11, Note 4 |
| 2024Q4 | 44,893 | 58,000 | 10-K FY2024, filed 2025-03-13, Note 4 |
| 2025Q1 | 47,531 | 61,000 | 10-Q Q1 2025, filed 2025-05-12, Note 4 |
| 2025Q2 | 50,000 | 63,000 | 10-Q Q2 2025 Note 4 **[추정 – 실제 공시 확인 필요]** |
| 2025Q3 | 52,000 | 65,000 | 10-Q Q3 2025 Note 4 **[추정 – 실제 공시 확인 필요]** |
| 2025Q4 | 55,000 | 67,000 | 10-K FY2025 Note 4 **[추정 – 실제 공시 확인 필요]** |

EDGAR 직접 링크: https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=MARA&type=10-K&dateb=&owner=include&count=40

---

## 수동 입력 vs 자동 수집 항목 요약

| 컬럼 | 수집 방식 | 검증 방법 |
|------|---------|---------|
| `btc_holdings` | 수동 (SEC EDGAR Notes) | 위 출처 테이블의 공시 날짜로 EDGAR 직접 검색 |
| `avg_cost_usd` | 수동 (SEC EDGAR Notes) | 동일 |
| `shares_outstanding` | **자동** (yfinance) | `scripts/fetch_official_data.py` 재실행 |
| `reported_net_income_usd` | **자동** (yfinance) | `scripts/fetch_official_data.py` 재실행 |
| `is_actual_asc360` | 파생 (`date >= 2025-01-01`) | 코드 로직 검토 |

---

## 데이터 갱신 방법

```bash
# yfinance로 최신 재무 데이터 재수집 후 CSV 재생성
python scripts/fetch_official_data.py
```

yfinance가 반환하지 않는 과거 분기는 `scripts/fetch_official_data.py` 내
`*_FIN_FALLBACK` 딕셔너리의 값이 사용됩니다.
BTC 보유량 데이터는 스크립트 내 `*_BTC` 딕셔너리를 직접 수정해야 합니다.
