import psycopg2
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
import joblib
import lightgbm as lgb

DB_CONFIG = {
    "dbname": "postgres", "user": "postgres", "password": "!kckim817", "host": "localhost", "port": "5432"
}

def train_ml_models():
    print("DB에서 [구간 속도]가 포함된 데이터를 불러오는 중...")
    conn = psycopg2.connect(**DB_CONFIG)
    
    query = """
        WITH JockeyStats AS (
            SELECT jockey_name, COUNT(*) AS jk_total, SUM(CASE WHEN ord <= 3 THEN 1 ELSE 0 END) AS jk_top3 FROM race_dtl GROUP BY jockey_name
        ),
        HorseStats AS (
            SELECT horse_name, COUNT(*) AS hr_total, SUM(CASE WHEN ord <= 3 THEN 1 ELSE 0 END) AS hr_top3, AVG(ord) AS hr_avg_ord, 
                   SUM(CASE WHEN track_cond IN ('포화', '불량') THEN 1 ELSE 0 END) as wet_total, 
                   SUM(CASE WHEN track_cond IN ('포화', '불량') AND ord <= 3 THEN 1 ELSE 0 END) as wet_top3,
                   AVG(NULLIF(s1f_time, 0)) AS avg_s1f, -- 🌟 초반 200m 평균 (작을수록 선행마)
                   AVG(NULLIF(g3f_time, 0)) AS avg_g3f  -- 🌟 후반 600m 평균 (작을수록 추입마)
            FROM race_dtl GROUP BY horse_name
        ),
        TrainerStats AS (
            SELECT trainer_name, COUNT(*) AS tr_total, SUM(CASE WHEN ord <= 3 THEN 1 ELSE 0 END) AS tr_top3 FROM race_dtl GROUP BY trainer_name
        ),
        ComboStats AS (
            SELECT jockey_name, trainer_name, COUNT(*) AS jt_total, SUM(CASE WHEN ord <= 3 THEN 1 ELSE 0 END) AS jt_top3 FROM race_dtl GROUP BY jockey_name, trainer_name
        )
        SELECT d.wg_budam, COALESCE(j.jk_top3::float / NULLIF(j.jk_total, 0), 0) AS jk_win_rate, COALESCE(h.hr_top3::float / NULLIF(h.hr_total, 0), 0) AS hr_win_rate, COALESCE(h.hr_total, 0) AS hr_total_races, COALESCE(h.hr_avg_ord, 8.0) AS hr_avg_rank, COALESCE(t.tr_top3::float / NULLIF(t.tr_total, 0), 0) AS tr_win_rate, COALESCE(c.jt_top3::float / NULLIF(c.jt_total, 0), 0) AS jt_win_rate, COALESCE(h.wet_top3::float / NULLIF(h.wet_total, 0), 0) AS hr_wet_win_rate, COALESCE(d.weather, '맑음') AS weather, COALESCE(d.track_cond, '건조') AS track_cond,
               COALESCE(h.avg_s1f, 15.0) AS avg_s1f, -- 🌟 결측치 방어(평균 15초)
               COALESCE(h.avg_g3f, 40.0) AS avg_g3f, -- 🌟 결측치 방어(평균 40초)
               CASE WHEN d.ord <= 3 THEN 1 ELSE 0 END AS target_top3
        FROM race_dtl d 
        LEFT JOIN JockeyStats j ON d.jockey_name = j.jockey_name LEFT JOIN HorseStats h ON d.horse_name = h.horse_name LEFT JOIN TrainerStats t ON d.trainer_name = t.trainer_name LEFT JOIN ComboStats c ON d.jockey_name = c.jockey_name AND d.trainer_name = c.trainer_name
        WHERE d.ord IS NOT NULL AND d.wg_budam IS NOT NULL
    """
    df = pd.read_sql(query, conn)
    conn.close()

    weather_map = {'맑음': 0, '흐림': 1, '비': 2, '눈': 3}
    track_map = {'건조': 0, '다습': 1, '포화': 2, '불량': 3}
    df['weather_code'] = df['weather'].map(weather_map).fillna(0)
    df['track_code'] = df['track_cond'].map(track_map).fillna(0)

    # 🌟 변수 12개로 확장
    X = df[['wg_budam', 'jk_win_rate', 'hr_win_rate', 'hr_total_races', 'hr_avg_rank', 'tr_win_rate', 'jt_win_rate', 'hr_wet_win_rate', 'weather_code', 'track_code', 'avg_s1f', 'avg_g3f']] 
    y = df['target_top3']                              
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    print("\n🤖 1번 뇌: Random Forest 학습 중...")
    rf_model = RandomForestClassifier(n_estimators=300, max_depth=15, random_state=42)
    rf_model.fit(X_train, y_train)
    joblib.dump(rf_model, 'rf_model.pkl')
    print(f"✅ RF 정확도: {accuracy_score(y_test, rf_model.predict(X_test)) * 100:.2f}%")

    print("\n🚀 2번 뇌: LightGBM 학습 중...")
    lgb_model = lgb.LGBMClassifier(n_estimators=300, max_depth=15, random_state=42, force_row_wise=True)
    lgb_model.fit(X_train, y_train)
    joblib.dump(lgb_model, 'lgb_model.pkl')
    print(f"✅ LightGBM 정확도: {accuracy_score(y_test, lgb_model.predict(X_test)) * 100:.2f}%")

if __name__ == "__main__":
    train_ml_models()