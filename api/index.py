import sys
import os

# 💡 현재 폴더(api)의 상위 폴더(Root)를 파이썬 탐색 경로에 강제로 주입
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server import app

# Vercel WSGI 어댑터 연결
app = app