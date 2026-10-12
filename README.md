# 🏇 AI 기반 경마 예측 및 가치 베팅 대시보드

공공데이터를 자동 수집하고 듀얼 인공지능(LightGBM, Random Forest)을 활용하여 경마 입상 확률과 가치 베팅(Expected Value) 구간을 시각화하는 Full-Stack 시스템입니다.

## 🛠 Tech Stack
* **Backend:** Python, FastAPI
* **Frontend:** HTML5, Bootstrap 5, Chart.js, Vanilla JS
* **Database:** PostgreSQL (UPSERT 기반 충돌 방지 로직 적용)
* **Machine Learning:** Scikit-Learn, LightGBM (12개 파생 변수 특성 공학)

## 📌 Key Features
* **자동화된 데이터 파이프라인:** KRA 공공데이터 API를 호출하여 날씨, 마장 상태, S1F/G3F(구간 속도), 출전 주기 등을 일일 단위로 자동 적재합니다.
* **Dual AI 교차 검증:** 선행/추입 각질을 스스로 판별하도록 훈련된 두 개의 모델(LightGBM, RF)이 실시간으로 입상 확률을 예측합니다.
* **가치 베팅(Value Betting) 탐색기:** 실시간 배당률 API와 연동하여 기대 수익률(EV) 120% 이상의 숨겨진 복병마를 자동으로 필터링 및 하이라이트 처리합니다.
* **마권 조합 추천:** 예측 확률 최상위 마필들을 조합하여 단승/복승/삼복승 추천 번호를 직관적으로 제공합니다.