import psycopg2
import pandas as pd
from sqlalchemy import create_engine

# 1. 내 PC의 로컬 PostgreSQL 연결 정보
local_conn = psycopg2.connect(
    dbname="postgres",
    user="postgres",
    password="!kckim817",
    host="localhost",
    port="5432"
)

# 2. Render 클라우드 PostgreSQL 연결 주소 (External Database URL)
CLOUD_DB_URL = "postgresql://horse_racing_db_um3j_user:3IEmPgb9F3gKTGWeHw0kmFFBz1XDKz77@dpg-db85u8gm7kps73d6sfgg-a.singapore-postgres.render.com/horse_racing_db_um3j"

try:
    print("📥 로컬 DB에서 출전표 및 경기 기록 읽는 중...")
    df_entry = pd.read_sql("SELECT * FROM race_entry", local_conn)
    df_dtl = pd.read_sql("SELECT * FROM race_dtl", local_conn)
    
    print(f"📊 읽어온 데이터: race_entry ({len(df_entry)}행), race_dtl ({len(df_dtl)}행)")

    # 3. SQLAlchemy 엔진 생성 및 클라우드 DB로 전송
    engine = create_engine(CLOUD_DB_URL.replace("postgresql://", "postgresql+psycopg2://"))
    
    print("🚀 클라우드 DB로 데이터 전송 중 (잠시만 기다려주세요)...")
    df_entry.to_sql('race_entry', engine, if_exists='replace', index=False)
    df_dtl.to_sql('race_dtl', engine, if_exists='replace', index=False)
    
    print("✅ 클라우드 DB 데이터 동기화 완료!")

except Exception as e:
    print("❌ 동기화 중 오류 발생:", e)
finally:
    local_conn.close()