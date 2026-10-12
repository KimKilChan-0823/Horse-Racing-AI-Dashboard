@echo off
chcp 65001 > nul
echo ========================================
echo 경마 빅데이터 자동 수집을 시작합니다...
echo ========================================

:: 시스템 기본 python 대신 패키지가 설치된 정확한 경로의 파이썬을 지정하여 실행합니다.
"C:\Users\KIM\AppData\Local\Python\pythoncore-3.14-64\python.exe" kra_entry_collector.py

echo.
echo 수집이 모두 완료되었습니다.
pause