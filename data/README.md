# Data Sources — Holdings CSV Files

> Last updated: 2026-04-15
> Script: `scripts/fetch_official_data.py`
> 2026-04-15: MSTR 2025Q1~Q4 btc_holdings·avg_cost_usd 공시 검증 후 교정 (상세 내용은 하단 변경 이력 참조)

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
| 2025Q1 | **528,185** | **67,457** | 10-Q Q1 2025, filed 2025-05-08, Note 5; Q1 실적발표 2025-05-01 (BusinessWire) |
| 2025Q2 | **597,325** | **70,982** | 10-Q Q2 2025, filed 2025-08-07, Note 5; Q2 실적발표 2025-07-31 (BusinessWire) |
| 2025Q3 | **640,031** | **73,983** | 10-Q Q3 2025, filed 2025-11-06, Note 5; Q3 실적발표 2025-10-30 (BusinessWire) |
| 2025Q4 | **672,497** ⚠️ | **74,997** | 8-K filed 2025-12-29 (2025-12-28 기준); 10-K FY2025 filed 2026-02-05, Note 5 ⚠️ |

> ⚠️ **2025Q4 주의**: 672,497은 2025-12-28 기준 8-K 공시값. 12-29~31 추가 매입이 있었을 수 있으며,
> 확정 연말 수치는 10-K FY2025(filed 2026-02-05)에서 확인 필요.
> 2026-02-01 기준 713,502 BTC (1월 추가 매입 포함) 는 Q1 2026 수치이므로 Q4로 사용 불가.

EDGAR 직접 링크: https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=MSTR&type=10-K&dateb=&owner=include&count=40

**2025년 실적발표 출처:**
- Q1 2025: https://www.businesswire.com/news/home/20250501465720/en/Strategy-Announces-First-Quarter-2025-Financial-Results
- Q2 2025: https://www.businesswire.com/news/home/20250731/en/Strategy-Announces-Second-Quarter-2025-Financial-Results
- Q3 2025: https://www.businesswire.com/news/home/20251030699813/en/Strategy-Announces-Third-Quarter-2025-Financial-Results
- Q4 2025 8-K: https://www.sec.gov/Archives/edgar/data/1050446/000119312525303157/d69948d8k.htm

---

### TSLA / Tesla, Inc.

> ⚠️ **중요**: ASC 350-60 적용 이전(2024Q4 이전)에는 Tesla가 SEC 공시에서 BTC 수량을 직접 공개하지 않았음.
> 2024Q4 10-K(ASC 350-60 최초 적용)에서 **11,509 BTC / $386M(총원가)** 가 최초 확정 공시됨.
> 이전 분기의 수량은 SEC 원문으로 검증 불가. 2022Q2 이후는 추가 매매 없음이 확인됨.

| 분기 | BTC 보유량 | 평균단가 ($) | 공시 출처 | 신뢰도 |
|------|-----------|------------|---------|-------|
| 2021Q1 | 42,902 ⚠️ | 33,000 ⚠️ | 10-Q Q1 2021, filed 2021-05-10 (수량 미공시) | 추정 |
| 2021Q2–2022Q1 | 42,902 ⚠️ | 33,000 ⚠️ | 각 분기 10-Q/10-K (수량 미공시) | 추정 |
| 2022Q2 | **11,509** | **33,539** | 10-Q Q2 2022: "약 75% 매각 후 잔여" / 2024 10-K 역산 확인 | 간접 확인 |
| 2022Q3–2024Q3 | **11,509** | **33,539** | 각 분기 "변동 없음" 확인 / 2024Q4 10-K 소급 확정 | 확인됨 |
| 2024Q4 | **11,509** | **33,539** | **10-K FY2024, filed 2025-01-29 — ASC 350-60 최초 수량 공시: 11,509 BTC / $386M** | ✓ 1차 출처 |
| 2025Q1–Q4 | **11,509** | **33,539** | 각 분기 10-Q 변동 없음 확인 (2025Q2: tsla-20250630.htm 직접 확인) | 확인됨 |

**확정 근거 (2024Q4 10-K):**
- 원문 URL: https://www.sec.gov/Archives/edgar/data/1318605/000162828025003063/tsla-20241231.htm
- BTC 수량: **11,509**
- 총 취득원가: **$386,000 thousand ($386M)**
- 계산 평균: $386,000,000 / 11,509 = **$33,539/BTC**
- 공정가치 (2024-12-31): $1.076B

EDGAR 직접 링크: https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=TSLA&type=10-K&dateb=&owner=include&count=40

---

### MARA / MARA Holdings, Inc.

> **2026-04-15 전수 검증 완료**: 2024Q1~2025Q4 전 분기를 ir.mara.com → SEC EDGAR `.htm` 원문에서 직접 확인.
> MARA는 2024Q4부터 BTC를 **직접 보유(Bitcoin)** + **receivable(대출/담보)** 두 범주로 분리 공시.
> 총 BTC = 두 범주 합계. 취득원가도 FIFO 방식 적용 (BTC 매도 시 저원가 BTC 우선 제거 → 잔존 평균원가 상승).

| 분기 | BTC 보유량 | 평균단가 ($) | 공시 출처 | 신뢰도 |
|------|-----------|------------|---------|-------|
| 2021Q1 | 5,134 | 20,000 | 10-Q Q1 2021, filed 2021-05-17, Note 4 | 미검증 |
| 2021Q2 | 6,695 | 22,000 | 10-Q Q2 2021, filed 2021-08-16, Note 4 | 미검증 |
| 2021Q3 | 7,754 | 24,000 | 10-Q Q3 2021, filed 2021-11-15, Note 4 | 미검증 |
| 2021Q4 | 8,133 | 30,000 | 10-K FY2021, filed 2022-03-10, Note 4 | 미검증 |
| 2022Q1 | 9,374 | 31,000 | 10-Q Q1 2022, filed 2022-05-16, Note 4 | 미검증 |
| 2022Q2 | 10,054 | 30,800 | 10-Q Q2 2022, filed 2022-08-15, Note 4 | 미검증 |
| 2022Q3 | 11,466 | 30,600 | 10-Q Q3 2022, filed 2022-11-14, Note 4 | 미검증 |
| 2022Q4 | 12,232 | 30,000 | 10-K FY2022, filed 2023-03-16, Note 4 | 미검증 |
| 2023Q1 | 13,726 | 29,700 | 10-Q Q1 2023, filed 2023-05-15, Note 4 | 미검증 |
| 2023Q2 | 12,538 | 29,500 | 10-Q Q2 2023, filed 2023-08-14, Note 4 | 미검증 |
| 2023Q3 | 13,726 | 29,400 | 10-Q Q3 2023, filed 2023-11-13, Note 4 | 미검증 |
| 2023Q4 | 15,174 | 29,300 | 10-K FY2023, filed 2024-03-14, Note 4 | 미검증 |
| **2024Q1** | **17,320** | **37,410** | [mara-20240331.htm](https://www.sec.gov/Archives/edgar/data/1507605/000162828024022243/mara-20240331.htm) Note 5; BTC 17,320 / 취득원가 $647,963K | ✓ 원문 확인 |
| **2024Q2** | **18,488** | **40,718** | [mara-20240630.htm](https://www.sec.gov/Archives/edgar/data/1507605/000162828024034196/mara-20240630.htm) Note 5; BTC 18,488 / 취득원가 $752,800K | ✓ 원문 확인 |
| **2024Q3** | **26,747** | **46,985** | [mara-20240930.htm](https://www.sec.gov/Archives/edgar/data/1507605/000162828024047148/mara-20240930.htm) Note 5; BTC 26,747 / 취득원가 $1,256,486K | ✓ 원문 확인 |
| **2024Q4** | **44,893** | **62,757** | [mara-20241231.htm](https://www.sec.gov/Archives/edgar/data/1507605/000150760525000003/mara-20241231.htm) Note 5; BTC 34,519 + receivable 10,374 / 취득원가 ~$2,817,297K | ✓ 원문 확인 |
| **2025Q1** | **47,532** | **64,278** | [mara-20250331.htm](https://www.sec.gov/Archives/edgar/data/1507605/000150760525000009/mara-20250331.htm) Note 5; BTC 33,263 + receivable 14,269 / 취득원가 $3,055,340K | ✓ 원문 확인 |
| **2025Q2** | **49,951** | **68,623** | [mara-20250630.htm](https://www.sec.gov/Archives/edgar/data/1507605/000150760525000018/mara-20250630.htm) Note 5; BTC 34,401 + receivable 15,550 / 취득원가 $3,427,753K | ✓ 원문 확인 |
| **2025Q3** | **52,850** | **87,752** | [mara-20250930.htm](https://www.sec.gov/Archives/edgar/data/1507605/000150760525000028/mara-20250930.htm) Note 5; BTC 35,493 + receivable 17,357 / 취득원가 $4,637,673K | ✓ 원문 확인 |
| **2025Q4** | **53,822** | **~90,000** ⚠️ | [mara-20251231.htm](https://www.sec.gov/Archives/edgar/data/1507605/000150760526000007/mara-20251231.htm); BTC 53,822 확인 / 취득원가 Note 미추출 → 평균원가 추정 | BTC ✓ / 원가 추정 |

> ⚠️ **2025Q4 평균원가**: 10-K Note 상세 테이블 접근 불가로 원가 미확인. Q3 $87,752 추세 기반 ~$90,000 추정.
> 2025년 중 15,133 BTC 매도(FIFO → 저원가 제거)로 잔존 평균원가 급등. 추후 검증 필요.

**2024Q1~Q2 BTC 수량 차이 발생 이유**: MARA가 ADGM 합작법인으로부터 배분 대기 중인 BTC를 별도 표기하였으며, 이전 CSV는 이를 혼입했을 가능성. 또한 Q2의 경우 HODL 전략(2024-07-25) 채택 이전으로 채굴 BTC 일부 매각 시기.

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

---

## 변경 이력

| 날짜 | 대상 파일 | 변경 내용 | 사유 |
|------|---------|---------|------|
| 2026-04-03 | mstr/tsla/mara_holdings.csv | 초기 생성 | 프로젝트 구축 |
| 2026-04-15 | mstr_holdings.csv | MSTR 2025Q1~Q4 btc_holdings·avg_cost_usd 교정 | 공시 검증 결과 이전 값이 추정치임이 확인됨 |
| 2026-04-15 | tsla_holdings.csv | TSLA 2022Q2~2025Q4 btc_holdings·avg_cost_usd 교정 | 2024Q4 10-K 원문 확인: 9,720→11,509 BTC, $33,000→$33,539 |
| 2026-04-15 | mara_holdings.csv | MARA 2024Q1~2025Q4 전 분기 교정 | ir.mara.com → SEC .htm 원문 직접 검증. BTC 수량·원가 전반 과소/과대 계상 확인 |

### 2026-04-15 교정 상세 (MSTR 2025년)

공시 실제값과 CSV 기존값의 차이:

| 분기 | 항목 | 기존값 (추정) | 교정값 (공시) | 출처 |
|------|------|------------|------------|------|
| 2025Q1 | btc_holdings | 528,185 | 528,185 ✓ | Q1 실적발표 2025-05-01 |
| 2025Q1 | avg_cost_usd | 66,385 | **67,457** | 10-Q Q1 2025, Note 5 |
| 2025Q2 | btc_holdings | 576,230 | **597,325** | Q2 실적발표 2025-07-31 |
| 2025Q2 | avg_cost_usd | 68,459 | **70,982** | 10-Q Q2 2025, Note 5 |
| 2025Q3 | btc_holdings | 601,550 | **640,031** | Q3 실적발표 2025-10-30 |
| 2025Q3 | avg_cost_usd | 70,583 | **73,983** | 10-Q Q3 2025, Note 5 |
| 2025Q4 | btc_holdings | 634,090 | **672,497** ⚠️ | 8-K filed 2025-12-29 (2025-12-28 기준) |
| 2025Q4 | avg_cost_usd | 72,418 | **74,997** | 8-K filed 2025-12-29 |

`shares_outstanding`, `reported_net_income_usd`는 SEC EDGAR API/yfinance 자동 수집값으로 변경 없음.

### 2026-04-15 교정 상세 (MARA 2024~2025년)

공시 실제값과 CSV 기존값의 차이 (ir.mara.com / SEC EDGAR `.htm` 원문 직접 검증):

| 분기 | 항목 | 기존값 | 교정값 (공시) | SEC 원문 URL |
|------|------|-------|------------|------------|
| 2024Q1 | btc_holdings | 17,631 | **17,320** | mara-20240331.htm Note 5 |
| 2024Q1 | avg_cost_usd | 34,500 | **37,410** | 취득원가 $647,963K / 17,320 |
| 2024Q2 | btc_holdings | 20,818 | **18,488** | mara-20240630.htm Note 5 |
| 2024Q2 | avg_cost_usd | 37,000 | **40,718** | 취득원가 $752,800K / 18,488 |
| 2024Q3 | btc_holdings | 26,842 | **26,747** | mara-20240930.htm Note 5 |
| 2024Q3 | avg_cost_usd | 40,000 | **46,985** | 취득원가 $1,256,486K / 26,747 |
| 2024Q4 | avg_cost_usd | 58,000 | **62,757** | 취득원가 ~$2,817,297K / 44,893 |
| 2025Q1 | btc_holdings | 47,531 | **47,532** | mara-20250331.htm Note 5 |
| 2025Q1 | avg_cost_usd | 61,000 | **64,278** | 취득원가 $3,055,340K / 47,532 |
| 2025Q2 | btc_holdings | 50,000 [추정] | **49,951** | mara-20250630.htm Note 5 (추정 아닌 공시) |
| 2025Q2 | avg_cost_usd | 63,000 [추정] | **68,623** | 취득원가 $3,427,753K / 49,951 |
| 2025Q3 | btc_holdings | 52,000 [추정] | **52,850** | mara-20250930.htm Note 5 (추정 아닌 공시) |
| 2025Q3 | avg_cost_usd | 65,000 [추정] | **87,752** | 취득원가 $4,637,673K / 52,850 (2025년 15,133 BTC 매도 FIFO 영향) |
| 2025Q4 | btc_holdings | 55,000 [추정] | **53,822** | mara-20251231.htm (추정 아닌 공시) |
| 2025Q4 | avg_cost_usd | 67,000 [추정] | **~90,000** ⚠️ | Note 상세 미추출, 추정 유지 |

**핵심 발견:**
- 2025Q2~Q4는 "추정"으로 표기되었으나 실제 SEC 공시가 존재함
- 평균원가가 모든 분기에서 체계적으로 과소 계상 (특히 2025Q3 $65K→$87.7K)
- 2025Q3 원가 급등 원인: 2025년 중 15,133 BTC 매도 (전환사채 상환 목적), FIFO 방식으로 저원가 BTC 제거 → 잔존 평균원가 급등
