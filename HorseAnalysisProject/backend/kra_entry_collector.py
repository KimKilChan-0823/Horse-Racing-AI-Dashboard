import requests
from bs4 import BeautifulSoup
import psycopg2
from datetime import date, timedelta
import time


# ==========================================
# 1. 설정값 입력 (기존과 동일)
# ==========================================
API_KEY = 'd4bc5acb01deb4042e53bc152059c9fa6b4dfde4f6fa4b882e1565ccc4738a54'
DB_USER = 'postgres'
DB_PASS = '!kckim817'
DB_HOST = 'localhost'
DB_PORT = '5432'
DB_NAME = 'postgres'

# 출전정보 API 엔드포인트 (경주성적 API와 다름)
url = 'http://apis.data.go.kr/B551015/API26_2/entrySheet_2'

# ==========================================
# 2. 다가오는 주말(출전일) 날짜 자동 계산
# ==========================================
# 출전표는 보통 목요일/금요일에 확정되므로, 오늘을 기준으로 다가오는 금, 토, 일 날짜를 구합니다.
def get_upcoming_weekend_dates():
    upcoming_dates = []
    today = date.today()
    # 오늘부터 7일 이내의 금(4), 토(5), 일(6) 날짜 추출
    for i in range(7):
        check_date = today + timedelta(days=i)
        if check_date.weekday() in [4, 5, 6]:
            upcoming_dates.append(check_date.strftime("%Y%m%d"))
    return upcoming_dates

target_dates = get_upcoming_weekend_dates()
# target_dates = ['20261009','20261010','20261011','20261012']
# target_dates = ['20231029'] # 기존에 수집해둔 데이터가 있는 과거 날짜로 임시 세팅
print(f"수집 대상 예정일: {target_dates}")

# ==========================================
# 3. 데이터 안전 변환 함수
# ==========================================
def safe_float(tag):
    if tag and tag.text.strip():
        try:
            return float(tag.text)
        except ValueError:
            return 0.0
    return 0.0

# ==========================================
# 4. DB 테이블 생성 및 출전정보 API 호출
# ==========================================
try:
    conn = psycopg2.connect(
        dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST, port=DB_PORT
    )
    cur = conn.cursor()

    # 분석용 출전표 테이블 생성 (없을 경우)
    create_table_query = """
    CREATE TABLE IF NOT EXISTS race_entry (
        meet_date VARCHAR(10),
        meet_loc VARCHAR(10),
        race_no INTEGER,
        horse_no INTEGER,
        horse_name VARCHAR(50),
        jockey_name VARCHAR(50),
        trainer_name VARCHAR(50),
        wg_budam NUMERIC(4,1),
        PRIMARY KEY (meet_date, meet_loc, race_no, horse_no)
    );
    """
    cur.execute(create_table_query)
    conn.commit()

    for target_date in target_dates:
        print(f"[{target_date}] 출전정보 확인 중...")
        
        params = {
            'ServiceKey': API_KEY,
            'pageNo': '1',
            'numOfRows': '999',
            'rc_date': target_date 
        }

        response = requests.get(url, params=params)
        response.encoding = 'utf-8'
        print(f"요청 URL: {response.url}")
        print(f"API 응답결과: {response.text[:300]}")
        soup = BeautifulSoup(response.text, 'xml')
        items = soup.find_all('item')
        
        if not items:
            print(f"  -> [{target_date}] 출전표 데이터 없음. (아직 확정 전이거나 휴장일)")
            time.sleep(1)
            continue
            
        inserted_count = 0
        for item in items:
            meet_loc = item.find('meet').text if item.find('meet') else '서울'
            race_no = int(item.find('rcNo').text) if item.find('rcNo') else 1
            horse_no = int(item.find('chulNo').text) if item.find('chulNo') else 0
            horse_name = item.find('hrName').text if item.find('hrName') else ''
            jockey_name = item.find('jkName').text if item.find('jkName') else ''
            trainer_name = item.find('trName').text if item.find('trName') else ''
            wg_budam = safe_float(item.find('wgBudam'))
            
            formatted_date = f"{target_date[:4]}-{target_date[4:6]}-{target_date[6:]}"
            
            # 출전표 Insert (이미 있으면 업데이트)
            entry_insert_query = """
                INSERT INTO race_entry (meet_date, meet_loc, race_no, horse_no, horse_name, jockey_name, trainer_name, wg_budam)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (meet_date, meet_loc, race_no, horse_no) 
                DO UPDATE SET 
                    horse_name = EXCLUDED.horse_name,
                    jockey_name = EXCLUDED.jockey_name,
                    trainer_name = EXCLUDED.trainer_name,
                    wg_budam = EXCLUDED.wg_budam;
            """
            cur.execute(entry_insert_query, (
                formatted_date, meet_loc, race_no, horse_no, 
                horse_name, jockey_name, trainer_name, wg_budam
            ))
            inserted_count += 1
            
        conn.commit()
        print(f"  -> [{target_date}] 총 {inserted_count}건의 출전마 정보 적재 완료")
        time.sleep(1)

except Exception as e:
    print(f"DB 작업 중 오류 발생: {e}")
finally:
    if 'conn' in locals() and conn:
        cur.close()
        conn.close()
        print("DB 연결을 안전하게 종료했습니다.")