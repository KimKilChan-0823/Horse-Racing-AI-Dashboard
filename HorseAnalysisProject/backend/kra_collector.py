import requests
from bs4 import BeautifulSoup
import psycopg2
from datetime import datetime, timedelta
import time
import xml.etree.ElementTree as ET

# ==========================================
# 1. 설정값 입력
# ==========================================
API_KEY = 'd4bc5acb01deb4042e53bc152059c9fa6b4dfde4f6fa4b882e1565ccc4738a54'
DB_USER = 'postgres'
DB_PASS = '!kckim817'
DB_HOST = 'localhost'
DB_PORT = '5432'
DB_NAME = 'postgres'

url = 'http://apis.data.go.kr/B551015/API214_1/RaceDetailResult_1'

try:
    conn = psycopg2.connect(
        dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST, port=DB_PORT
    )
    cur = conn.cursor()

    start_date = datetime(2026, 1, 1)
    end_date = datetime.today()
    
    current_date = start_date
    while current_date <= end_date:
        # 요일 확인 (0:월, 1:화, 2:수, 3:목, 4:금, 5:토, 6:일)
        # 경마가 없는 월~목요일은 API를 호출하지 않고 건너뜁니다 (일일 한도 절약)
        if current_date.weekday() < 4: 
            current_date += timedelta(days=1)
            continue

        date_str = current_date.strftime("%Y%m%d")          
        formatted_date = current_date.strftime("%Y-%m-%d")  
        
        cur.execute("SELECT COUNT(*) FROM race_dtl WHERE meet_date = %s", (formatted_date,))
        exists_count = cur.fetchone()[0]
        
        if exists_count > 0:
            print(f"[{formatted_date}] 데이터 존재함 (수집 생략)")
            current_date += timedelta(days=1)
            continue
            
        print(f"[{formatted_date}] 새로운 데이터 수집 시작...")
        
        params = {
            'ServiceKey': API_KEY,
            'pageNo': '1',
            'numOfRows': '999',
            'rc_date': date_str 
        }

        response = requests.get(url, params=params)
        response.encoding = 'utf-8'
        
        # 일일 한도 초과 에러 방어
        if 'LIMITED_NUMBER_OF_SERVICE_REQUESTS_EXCEEDS_ERROR' in response.text:
            print("🚨 일일 API 요청 한도를 초과했습니다. 자정 이후에 다시 실행해주세요.")
            break
            
        root = ET.fromstring(response.content)
        items = root.findall('.//item')
        
        if not items:
            print("데이터 없음, 다음 날짜로 이동 중...")
            current_date += timedelta(days=1)
            time.sleep(0.5)
            continue

        inserted_count = 0
        for item in items:
            # 🌟 1. 기본 정보 파싱 (결측치 방어)
            meet_date = item.find('rcDate').text if item.find('rcDate') is not None else ''
            horse_name = item.find('hrName').text if item.find('hrName') is not None else ''
            jockey_name = item.find('jkName').text if item.find('jkName') is not None else ''
            trainer_name = item.find('trName').text if item.find('trName') is not None else ''
            wg_budam = item.find('wgBudam').text if item.find('wgBudam') is not None else '0'
            
            # 🌟 2. 경마장(meet_loc) 코드 파싱
            meet_code = item.find('meet').text if item.find('meet') is not None else ''
            if meet_code == '1': meet_loc = '서울'
            elif meet_code == '2': meet_loc = '제주'
            elif meet_code == '3': meet_loc = '부경'
            elif meet_code == '4': meet_loc = '영천'
            else: meet_loc = '서울' 

            # 🌟 3. 경주 번호, 마번(horse_no), 순위, 기록 파싱
            rc_no_text = item.find('rcNo').text if item.find('rcNo') is not None else '1'
            race_no = int(''.join(filter(str.isdigit, rc_no_text))) if rc_no_text else 1
            
            # (추가됨) 마번 파싱
            chul_no_text = item.find('chulNo').text if item.find('chulNo') is not None else '0'
            horse_no = int(''.join(filter(str.isdigit, chul_no_text))) if chul_no_text else 0
            
            ord_rank_text = item.find('ord').text if item.find('ord') is not None else '0'
            ord_rank = int(''.join(filter(str.isdigit, ord_rank_text))) if ord_rank_text else 0
            
            rc_time_text = item.find('rcTime').text if item.find('rcTime') is not None else '0'
            rc_time = float(rc_time_text) if rc_time_text else 0.0
            
            # 🌟 4. 날씨 및 마장 상태 파싱
            weather = item.find('weather').text if item.find('weather') is not None else '맑음'
            track_cond = item.find('track').text if item.find('track') is not None else '건조'
            
            # 🌟 5. 구간 속도 (S1F, G3F) 파싱
            s1f_text = item.find('s1fTime').text if item.find('s1fTime') is not None else '0'
            g3f_text = item.find('g3fTime').text if item.find('g3fTime') is not None else '0'
            s1f_time = float(s1f_text) if s1f_text else 0.0
            g3f_time = float(g3f_text) if g3f_text else 0.0

            # 🌟 6. 출전 주기(휴양 일수) 자동 계산 로직
            cur.execute("""
                SELECT meet_date FROM race_dtl 
                WHERE horse_name = %s AND meet_date < %s 
                ORDER BY meet_date DESC LIMIT 1
            """, (horse_name, meet_date))
            last_race = cur.fetchone()
            
            if last_race:
                # 최근 경주가 있으면 날짜 차이 계산
                last_date = datetime.strptime(last_race[0], "%Y-%m-%d")
                curr_date = datetime.strptime(meet_date, "%Y-%m-%d")
                rest_days = (curr_date - last_date).days
            else:
                # 데뷔전이거나 기록이 없으면 기본값(30일) 적용
                rest_days = 30
            
            # DB INSERT
            if horse_name and meet_date:
                cur.execute("""
                    INSERT INTO race_dtl 
                    (meet_date, meet_loc, race_no, horse_no, horse_name, jockey_name, trainer_name, wg_budam, ord, rc_time, weather, track_cond, s1f_time, g3f_time, rest_days)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (meet_date, meet_loc, race_no, horse_no) 
                    DO UPDATE SET 
                        s1f_time = EXCLUDED.s1f_time,
                        g3f_time = EXCLUDED.g3f_time,
                        weather = EXCLUDED.weather,
                        track_cond = EXCLUDED.track_cond,
                        ord = EXCLUDED.ord,
                        rc_time = EXCLUDED.rc_time,
                        rest_days = EXCLUDED.rest_days
                """, (meet_date, meet_loc, race_no, horse_no, horse_name, jockey_name, trainer_name, wg_budam, ord_rank, rc_time, weather, track_cond, s1f_time, g3f_time, rest_days))
                inserted_count += 1
                
        conn.commit()
        print(f"  -> [{formatted_date}] {inserted_count}건 신규 수집 완료 (날씨/마장 포함)")
        
        current_date += timedelta(days=1)
        time.sleep(0.5)

except Exception as e:
    print(f"수집 중 오류 발생: {e}")
finally:
    if 'conn' in locals() and conn:
        cur.close()
        conn.close()
        print("DB 연결을 종료했습니다.")