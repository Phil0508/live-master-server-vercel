"""
Vercel Serverless Function Entry Point
- Flask 앱을 WSGI 어댑터로 감싸서 Vercel에서 실행
- 서울 리전(icn1)에서 Supabase 서울 DB로 저지연 연결
"""
import os
import sys

# Vercel 서버리스 환경 플래그 설정 (server.py에서 GUI/스레딩 코드 비활성화용)
os.environ['VERCEL'] = '1'
os.environ['HEADLESS'] = '1'

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server import app, init_db

# Vercel 서버리스에서는 모듈 로드 시 DB 초기화
init_db()

# Vercel Python Runtime이 인식하는 WSGI 앱 객체
# @vercel/python은 'app' 이름으로 export된 WSGI callable을 자동 감지
app = app
