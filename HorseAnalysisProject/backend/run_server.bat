@echo off
chcp 65001 > nul
echo ========================================
echo 경마 분석 웹 서버(FastAPI)를 시작합니다...
echo ========================================

:: 정확한 파이썬 경로를 지정하여 uvicorn 실행
"C:\Users\KIM\AppData\Local\Python\pythoncore-3.14-64\python.exe" -m uvicorn main:app --reload

pause