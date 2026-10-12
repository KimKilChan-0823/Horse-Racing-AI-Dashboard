from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import psycopg2
import pandas as pd
import joblib

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_CONFIG = {
    "dbname": "postgres",
    "user": "postgres",
    "password": "!kckim817",
    "host": "localhost",
    "port": "5432"
}

try:
    rf_model = joblib.load('rf_model.pkl')
    lgb_model = joblib.load('lgb_model.pkl')
    print("✅ 듀얼 AI 예측 모델(RF, LightGBM) 로드 성공!")
except Exception as e:
    print("⚠️ AI 모델 로드 실패 (기존 통계 방식으로 대체됩니다):", e)
    rf_model, lgb_model = None, None

@app.get("/api/analysis")
def get_race_analysis(
    meet_date: str = Query(...), 
    meet_loc: str = Query(...), 
    race_no: str = Query(...),
    weather: str = Query('맑음'),
    track_cond: str = Query('건조')
):
    clean_race_no = ''.join(filter(str.isdigit, race_no))
    r_no = int(clean_race_no) if clean_race_no else 1

    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    query = """
        WITH JockeyStats AS (
            SELECT jockey_name, COUNT(*) AS jk_total, SUM(CASE WHEN ord <= 3 THEN 1 ELSE 0 END) AS jk_top3_cnt FROM race_dtl GROUP BY jockey_name
        ),
        TrainerStats AS (
            SELECT trainer_name, COUNT(*) AS tr_total, SUM(CASE WHEN ord <= 3 THEN 1 ELSE 0 END) AS tr_top3_cnt FROM race_dtl GROUP BY trainer_name
        ),
        HorseStats AS (
            SELECT horse_name, COUNT(*) AS hr_total, SUM(CASE WHEN ord <= 3 THEN 1 ELSE 0 END) AS hr_top3_cnt, AVG(ord) AS hr_avg_ord, MIN(rc_time) AS best_time,
                   SUM(CASE WHEN track_cond IN ('포화', '불량') THEN 1 ELSE 0 END) as wet_total,
                   SUM(CASE WHEN track_cond IN ('포화', '불량') AND ord <= 3 THEN 1 ELSE 0 END) as wet_top3,
                   AVG(NULLIF(s1f_time, 0)) AS avg_s1f,
                   AVG(NULLIF(g3f_time, 0)) AS avg_g3f
            FROM race_dtl GROUP BY horse_name
        ),
        ComboStats AS (
            SELECT jockey_name, trainer_name, COUNT(*) AS jt_total, SUM(CASE WHEN ord <= 3 THEN 1 ELSE 0 END) AS jt_top3_cnt FROM race_dtl GROUP BY jockey_name, trainer_name
        )
        SELECT e.horse_no, e.horse_name, e.jockey_name, e.wg_budam,
               COALESCE(h.hr_total, 0) AS total_races,
               CASE WHEN COALESCE(h.hr_total, 0) > 0 THEN (h.hr_top3_cnt::decimal / h.hr_total) * 100 ELSE 0.0 END AS horse_top3_rate,
               COALESCE(h.best_time, 0) AS best_time,
               COALESCE(j.jk_total, 0) AS jk_total,
               CASE WHEN COALESCE(j.jk_total, 0) > 0 THEN (j.jk_top3_cnt::decimal / j.jk_total) * 100 ELSE 0.0 END AS jk_top3_rate,
               CASE WHEN COALESCE(t.tr_total, 0) > 0 THEN (t.tr_top3_cnt::decimal / t.tr_total) * 100 ELSE 0.0 END AS tr_top3_rate,
               COALESCE(h.hr_avg_ord, 8.0) AS avg_rank,
               CASE WHEN COALESCE(c.jt_total, 0) > 0 THEN (c.jt_top3_cnt::decimal / c.jt_total) * 100 ELSE 0.0 END AS jt_top3_rate,
               CASE WHEN COALESCE(h.wet_total, 0) > 0 THEN (h.wet_top3::decimal / h.wet_total) * 100 ELSE 0.0 END AS hr_wet_top3_rate,
               rd.ord AS actual_rank,
               COALESCE(h.avg_s1f, 15.0) AS avg_s1f,
               COALESCE(h.avg_g3f, 40.0) AS avg_g3f
        FROM race_entry e
        LEFT JOIN HorseStats h ON e.horse_name = h.horse_name
        LEFT JOIN JockeyStats j ON e.jockey_name = j.jockey_name
        LEFT JOIN TrainerStats t ON e.trainer_name = t.trainer_name
        LEFT JOIN ComboStats c ON e.jockey_name = c.jockey_name AND e.trainer_name = c.trainer_name
        LEFT JOIN race_dtl rd ON e.meet_date::text = rd.meet_date::text AND e.horse_name = rd.horse_name
        WHERE e.meet_date = %s AND e.meet_loc = %s AND e.race_no = %s
    """
    
    try:
        cur.execute(query, (meet_date, meet_loc, r_no))
        rows = cur.fetchall()
        
        weather_map = {'맑음': 0, '흐림': 1, '비': 2, '눈': 3}
        track_map = {'건조': 0, '다습': 1, '포화': 2, '불량': 3}
        w_code = weather_map.get(weather, 0)
        t_code = track_map.get(track_cond, 0)
        
        result = []
        for row in rows:
            wg_budam = float(row[3]) if row[3] else 0.0
            total_races = row[4]
            horse_rate = float(row[5]) if row[5] else 0.0
            best_time = float(row[6]) if row[6] else 0.0
            jk_rate = float(row[8]) if row[8] else 0.0
            tr_rate = float(row[9]) if row[9] else 0.0
            avg_rank = float(row[10]) if row[10] else 8.0
            jt_rate = float(row[11]) if row[11] else 0.0
            wet_rate = float(row[12]) if row[12] else 0.0
            actual_rank = row[13] if row[13] is not None else None
            avg_s1f = float(row[14]) if row[14] else 15.0
            avg_g3f = float(row[15]) if row[15] else 40.0
            
            pred_score_lgbm = 0.0
            pred_score_rf = 0.0
            
            input_df = pd.DataFrame(
                [[wg_budam, jk_rate/100.0, horse_rate/100.0, total_races, avg_rank, tr_rate/100.0, jt_rate/100.0, wet_rate/100.0, w_code, t_code, avg_s1f, avg_g3f]], 
                columns=['wg_budam', 'jk_win_rate', 'hr_win_rate', 'hr_total_races', 'hr_avg_rank', 'tr_win_rate', 'jt_win_rate', 'hr_wet_win_rate', 'weather_code', 'track_code', 'avg_s1f', 'avg_g3f']
            )

            if lgb_model:
                prob_lgb = lgb_model.predict_proba(input_df)[0][1] 
                pred_score_lgbm = round(prob_lgb * 100, 1)
                
            if rf_model:
                prob_rf = rf_model.predict_proba(input_df)[0][1] 
                pred_score_rf = round(prob_rf * 100, 1)
            
            result.append({
                "horse_no": row[0], "horse_name": row[1], "jockey_name": row[2], "wg_budam": wg_budam,
                "total_races": total_races, "top3_rate": horse_rate, "best_time": best_time,
                "jk_top3_rate": jk_rate, "tr_top3_rate": tr_rate, "jt_top3_rate": jt_rate,
                "hr_wet_top3_rate": wet_rate, "actual_rank": actual_rank,
                "pred_score_lgbm": pred_score_lgbm, 
                "pred_score_rf": pred_score_rf
            })
            
        result = sorted(result, key=lambda x: int(x['horse_no']))
        return {"data": result}
    except Exception as e:
        print(f"SQL/분석 오류: {e}")
        return {"data": []}
    finally:
        cur.close()
        conn.close()

import requests
from bs4 import BeautifulSoup

@app.get("/api/odds")
def get_realtime_odds(meet_loc: str = Query(...), race_no: str = Query(...)):
    # 예시: KRA 실시간 배당률 페이지 파싱 (실제 URL 및 파라미터 규격에 맞춰 조정 필요)
    # 영천(4), 서울(1), 부경(3), 제주(2) 코드를 변환하여 해당 경주의 단승식 배당을 가져옴
    loc_code = "1" if meet_loc == "서울" else "3" if meet_loc == "부경" else "2"
    url = f"http://race.kra.co.kr/realtime_odds_endpoint?loc={loc_code}&race={race_no}"
    
    try:
        # requests.get(url) 후 배당판 테이블 스크래핑
        # 아래는 리턴 규격 예시 (마번을 키값으로, 단승식 배당률을 밸류로 매핑)
        mock_odds_data = {
            "1": 3.4, "2": 15.2, "3": 8.5, "4": 1.9, "8": 26.4, "9": 3.8
        }
        return {"status": "success", "odds": mock_odds_data}
    except Exception as e:
        return {"status": "error", "odds": {}}