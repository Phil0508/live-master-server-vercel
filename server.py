import sys
import os
import io

# 🖥️ 로컬 전용 모드 (서버리스/Postgres 관련 기능 완전 비활성화)
IS_VERCEL = False

# GUI 모드(console=False)에서 발생하는 모든 에러를 파일로 로깅하여 크래시 분석
if getattr(sys, 'frozen', False):
    try:
        exe_dir = os.path.dirname(sys.executable)
        log_file = open(os.path.join(exe_dir, 'server_error.log'), 'w', encoding='utf-8', buffering=1)
        sys.stderr = log_file
        sys.stdout = log_file
    except Exception:
        pass
else:
    # 윈도우 콘솔 UTF-8 출력 강제 (cp949 이모지 에러 방지)
    try:
        if sys.stdout is not None and hasattr(sys.stdout, 'buffer'):
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        if sys.stderr is not None and hasattr(sys.stderr, 'buffer'):
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
    except Exception:
        pass

import json
import threading
import logging

import time
import csv
import queue
import shutil
import socket
import sqlite3
from contextlib import contextmanager
import ssl
import urllib.request
import urllib.parse

# 🖥️ 로컬 SQLite 전용 (Postgres/Vercel 관련 분기는 항상 False로 고정되어 비활성화됨)
DATABASE_URL = None
IS_POSTGRES = False
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MEDIA_CACHE_DIR = os.path.join(BASE_DIR, 'media_cache')
if not os.path.exists(MEDIA_CACHE_DIR):
    os.makedirs(MEDIA_CACHE_DIR, exist_ok=True)

def db_query(query):
    return query

def _pg_binary(data):
    """로컬 SQLite 전용: 바이너리 데이터 그대로 반환"""
    return data

@contextmanager
def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
from flask import Flask, jsonify, request, send_from_directory, redirect, url_for, session, send_file, make_response
from flask_cors import CORS
try:
    import tkinter as tk
    from tkinter import messagebox
except ImportError:
    tk = None
    messagebox = None
import webbrowser

if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
    BUNDLE_DIR = getattr(sys, '_MEIPASS', BASE_DIR)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    BUNDLE_DIR = BASE_DIR

# Vercel 서버리스: 쓰기 가능한 임시 디렉토리
TMP_DIR = '/tmp' if IS_VERCEL else BASE_DIR

DB_FILE = os.path.join(BASE_DIR, 'live_master.db')
LAYOUT_FILE = os.path.join(BASE_DIR, 'layout.json')

# ==========================================
# 🤫 서버 로그 제어
# ==========================================
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)
log.disabled = True 

app = Flask(__name__)
app.secret_key = 'isacbin_master_key_0508'
CORS(app)
file_lock = threading.Lock()

# 🚫 [강력 차단] 웹 브라우저 및 OBS CEF 캐싱 방지 헤더 이식
@app.after_request
def add_header(r):
    r.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    r.headers["Pragma"] = "no-cache"
    r.headers["Expires"] = "0"
    return r

# 🔓 로컬 전용 모드: 로그인/인증 없이 모든 페이지 및 API에 자유롭게 접근 가능

# 📡 실시간 SSE 클라이언트 관리 시스템
sse_clients = []
sse_lock = threading.Lock()

def broadcast_event(event_name, data):
    if isinstance(data, dict):
        data = data.copy()
        data['server_time'] = int(time.time() * 1000)
    with sse_lock:
        message = f"event: {event_name}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
        for client_q in sse_clients:
            try:
                client_q.put_nowait(message)
            except queue.Full:
                pass

def create_snapshot_record(label, state=None):
    if state is None:
        state = load_data()
    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            db_query("INSERT INTO snapshots (timestamp, state_json, summary) VALUES (?, ?, ?)"),
            (timestamp, json.dumps(state, ensure_ascii=False), label)
        )
    return timestamp

def serve_html_file(filename):
    local_path = os.path.join(BASE_DIR, filename)
    if os.path.exists(local_path):
        res = make_response(send_from_directory(BASE_DIR, filename))
    else:
        res = make_response(send_from_directory(BUNDLE_DIR, filename))
    res.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    res.headers['Pragma'] = 'no-cache'
    res.headers['Expires'] = '0'
    return res

DEFAULT_STATE = {
    "bjs": [],
    "bottom_fixed": {"name": "운영비", "score": 0},
    "target_goal": 50000,
    "goal_event_pending": False,
    "goal_event_approved": False,
    "theme": "default",
    "reaction_mode": False,
    "reaction_queue": [],
    "reaction_volume": 0.5,
    "popup_enabled": True,
    "takeover_enabled": True,
    "ticker_enabled": True,
    "ticker_speed": 70,
    "ticker_text": "📢 환영합니다! 후원은 방송에 큰 힘이 됩니다!",
    "match_data": {"active": False, "players": [], "time_left_ms": 180000, "is_running": False},
    "account": {"bank": "기업은행", "acc_num": "464-068673-04-016", "name": "드래곤엔터"},
    "pending_donations": [],
    "latest_donation": {"name": "", "amount": 0, "message": "", "time": 0},
    "slot_machine": {
        "active": False,
        "started_at": 0,
        "duration_ms": 1200000,
        "trigger_amount": 20000,
        "selected_reaction_ids": []
    },
    "pending_slot_spins": [],
    "extra_game_active": False,
    "extra_bjs": [],
    "roulette_enabled": False,
    "home_race_enabled": False,
    "home_goals": {},
    "broadcast_active": False,
    "saved_colors": ['#ff0055', '#00e5ff', '#ff9100', '#d500f9', '#00ff00', '#ffff00', '#ff0000', '#0000ff', '#ffffff'],
    "version": 1,
    "roulette": {
        "command": None,
        "command_time": 0,
        "weight_type": "equal",
        "select_name": "",
        "select_index": -1,
        "winner_name": None,
        "is_spinning": False,
        "item_source": "bj",
        "custom_items": ["벌칙 1", "벌칙 2", "벌칙 3", "벌칙 4", "벌칙 5"]
    },
    "card_game": {
        "active": True,
        "is_running": False,
        "time_left_ms": 300000,
        "selected_reaction_ids": [],
        "cards": [],
        "finalized": False,
        "final_card_ids": [],
        "final_reaction_ids": []
    }
}

MEMORY_STATE = None

# ==========================================
# 🗄️ 데이터베이스 핵심 로직
# ==========================================
def init_db():
    if not IS_POSTGRES:
        if not os.path.exists(DB_FILE) and os.path.exists(DB_FILE + '.bak'):
            try:
                shutil.copy2(DB_FILE + '.bak', DB_FILE)
                print("[DB 자동 복구] 백업 본으로 DB 복구 성공!")
            except Exception as e:
                print(f"[DB 자동 복구 실패] {e}")

    with get_db_connection() as conn:
        cursor = conn.cursor()
        if not IS_POSTGRES:
            try:
                cursor.execute("PRAGMA journal_mode=WAL;")
            except Exception:
                pass
        
        cursor.execute("CREATE TABLE IF NOT EXISTS kv_store (key TEXT PRIMARY KEY, value TEXT)")
        cursor.execute("CREATE TABLE IF NOT EXISTS players (name TEXT PRIMARY KEY, score INTEGER, contribution INTEGER)")
        
        if IS_POSTGRES:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS bank_ledger (
                    id SERIAL PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    player_name TEXT NOT NULL,
                    tx_type TEXT NOT NULL,
                    score_change INTEGER NOT NULL,
                    score_balance INTEGER NOT NULL,
                    contrib_change INTEGER NOT NULL,
                    contrib_balance INTEGER NOT NULL,
                    description TEXT
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS donation_history (
                    id SERIAL PRIMARY KEY,
                    timestamp TEXT,
                    name TEXT,
                    amount INTEGER,
                    current_total INTEGER, 
                    message TEXT,
                    source TEXT,
                    tx_id TEXT
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS snapshots (
                    id SERIAL PRIMARY KEY,
                    timestamp TEXT,
                    state_json TEXT,
                    summary TEXT
                )
            """)
        else:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS bank_ledger (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    player_name TEXT NOT NULL,
                    tx_type TEXT NOT NULL,
                    score_change INTEGER NOT NULL,
                    score_balance INTEGER NOT NULL,
                    contrib_change INTEGER NOT NULL,
                    contrib_balance INTEGER NOT NULL,
                    description TEXT
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS donation_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    name TEXT,
                    amount INTEGER,
                    current_total INTEGER, 
                    message TEXT,
                    source TEXT,
                    tx_id TEXT
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    state_json TEXT,
                    summary TEXT
                )
            """)
        
        # 리액션 파일 및 아이템 테이블 생성 (PostgreSQL/SQLite 공용)
        if IS_POSTGRES:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS reaction_files (
                    id TEXT PRIMARY KEY,
                    filename TEXT,
                    content_type TEXT,
                    file_data BYTEA
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS reaction_items (
                    id SERIAL PRIMARY KEY,
                    title TEXT,
                    amount INTEGER DEFAULT 0,
                    audio_file_id TEXT,
                    image_file_id TEXT,
                    is_enabled BOOLEAN DEFAULT TRUE
                )
            """)
        else:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS reaction_files (
                    id TEXT PRIMARY KEY,
                    filename TEXT,
                    content_type TEXT,
                    file_data BLOB
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS reaction_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT,
                    amount INTEGER DEFAULT 0,
                    audio_file_id TEXT,
                    image_file_id TEXT,
                    is_enabled INTEGER DEFAULT 1
                )
            """)
        
        # 💡 [추가] 특별 후원자(VIP) 테이블 생성 (PostgreSQL / SQLite 공용)
        if IS_POSTGRES:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS vip_donators (
                    name TEXT PRIMARY KEY,
                    grade TEXT NOT NULL,
                    custom_color TEXT DEFAULT '#ffd700',
                    badge TEXT DEFAULT '👑'
                )
            """)
        else:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS vip_donators (
                    name TEXT PRIMARY KEY,
                    grade TEXT NOT NULL,
                    custom_color TEXT DEFAULT '#ffd700',
                    badge TEXT DEFAULT '👑'
                )
            """)
        
        # 💡 [스키마 마이그레이션 패치] 기존 테이블 스키마 동적 추가 및 안전성 유지
        # PostgreSQL에서는 IF NOT EXISTS로 이미 컬럼이 생성되어 있으므로 ALTER는 건너뜀
        if not IS_POSTGRES:
            try:
                cursor.execute("ALTER TABLE snapshots ADD COLUMN summary TEXT")
            except Exception:
                pass
            try:
                cursor.execute("ALTER TABLE donation_history ADD COLUMN tx_id TEXT")
            except Exception:
                pass
            try:
                cursor.execute("ALTER TABLE reaction_items ADD COLUMN is_enabled BOOLEAN DEFAULT TRUE")
            except Exception:
                pass
        else:
            # PostgreSQL/Supabase 전용: 운영 데이터 보존을 최우선으로 두고 누락 컬럼만 추가합니다.
            # 절대 테이블을 DROP하지 않습니다. Supabase에서 created_at 같은 추가 컬럼이 있어도 정상입니다.
            pg_column_defaults = {
                'players': {
                    'score': 'INTEGER DEFAULT 0',
                    'contribution': 'INTEGER DEFAULT 0',
                },
                'reaction_files': {
                    'filename': 'TEXT',
                    'content_type': 'TEXT',
                    'file_data': 'BYTEA',
                },
                'reaction_items': {
                    'title': 'TEXT',
                    'amount': 'INTEGER DEFAULT 0',
                    'audio_file_id': 'TEXT',
                    'image_file_id': 'TEXT',
                    'is_enabled': 'BOOLEAN DEFAULT TRUE',
                },
            }

            for table_name, optional_columns in pg_column_defaults.items():
                try:
                    cursor.execute("""
                        SELECT column_name FROM information_schema.columns 
                        WHERE table_schema = 'public' AND table_name = %s
                    """, (table_name,))
                    existing_cols = {row[0] for row in cursor.fetchall()}
                    for col_name, col_def in optional_columns.items():
                        if col_name not in existing_cols:
                            print(f"⚠️ [PostgreSQL 스키마 보정] {table_name}.{col_name} 컬럼 추가")
                            cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {col_name} {col_def}")
                except Exception as e:
                    print(f"⚠️ [PostgreSQL 스키마 보정] {table_name} 보정 실패: {e}")
            
            # donation_history tx_id 컬럼 확인 및 추가
            try:
                cursor.execute("""
                    SELECT column_name FROM information_schema.columns 
                    WHERE table_schema = 'public' AND table_name = 'donation_history' AND column_name = 'tx_id'
                """)
                if not cursor.fetchone():
                    cursor.execute("ALTER TABLE donation_history ADD COLUMN tx_id TEXT")
            except Exception:
                pass
            
            # snapshots summary 컬럼 확인 및 추가
            try:
                cursor.execute("""
                    SELECT column_name FROM information_schema.columns 
                    WHERE table_schema = 'public' AND table_name = 'snapshots' AND column_name = 'summary'
                """)
                if not cursor.fetchone():
                    cursor.execute("ALTER TABLE snapshots ADD COLUMN summary TEXT")
            except Exception:
                pass

def load_data():
    global MEMORY_STATE
    # Vercel/Supabase에서는 여러 서버리스 인스턴스가 동시에 뜰 수 있으므로
    # 메모리 캐시를 신뢰하면 오래된 초기 상태가 라이브 데이터를 덮어쓸 수 있습니다.
    if MEMORY_STATE is not None and not IS_POSTGRES:
        return MEMORY_STATE
    init_db()
    
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(db_query("SELECT key, value FROM kv_store"))
            kv_data = {row[0]: json.loads(row[1]) for row in cursor.fetchall()}
            cursor.execute(db_query("SELECT name, score, contribution FROM players ORDER BY contribution DESC"))
            bjs = [{"name": row[0], "score": row[1], "contribution": row[2]} for row in cursor.fetchall()]
    except Exception as e:
        print(f"⚠️ [DB 로드 오류] {e}")
        # DB 로드 실패 시 데이터를 덮어써서 날려버리는 것을 막기 위해 예외를 상위로 전파합니다.
        raise e

    if len(kv_data) == 0 and len(bjs) == 0:
        MEMORY_STATE = DEFAULT_STATE.copy()
        if not IS_POSTGRES:
            save_data(MEMORY_STATE, is_initial=True)
        return MEMORY_STATE

    state = {}
    for key, default_val in DEFAULT_STATE.items():
        if key == "bjs": 
            state["bjs"] = bjs
        elif key in kv_data: 
            state[key] = kv_data[key]
        else: 
            state[key] = default_val
            
    # saved_colors 보정 (6개 -> 9개로 확장 및 하위 호환 마이그레이션)
    default_colors = ['#ff0055', '#00e5ff', '#ff9100', '#d500f9', '#00ff00', '#ffff00', '#ff0000', '#0000ff', '#ffffff']
    if 'saved_colors' in state:
        if not isinstance(state['saved_colors'], list):
            state['saved_colors'] = default_colors
        elif len(state['saved_colors']) < 9:
            for i in range(len(state['saved_colors']), 9):
                state['saved_colors'].append(default_colors[i])
    else:
        state['saved_colors'] = default_colors
    
    # 🎴 [카드 뒤집기] 카드 데이터 키 보정 (자동으로 무작위 채우지 않음 - 운영자가 명시적으로 채워야 함)
    if 'card_game' not in state or not isinstance(state.get('card_game'), dict):
        state['card_game'] = {"active": False, "is_running": False, "time_left_ms": 300000, "selected_reaction_ids": [], "cards": [], "finalized": False, "final_card_ids": []}
    else:
        state['card_game'].setdefault('finalized', False)
        state['card_game'].setdefault('final_card_ids', [])
        state['card_game'].setdefault('final_reaction_ids', [])
    
    MEMORY_STATE = state
    return MEMORY_STATE

def normalize_slot_machine_state(state):
    slot = state.get('slot_machine')
    if not isinstance(slot, dict):
        slot = DEFAULT_STATE['slot_machine'].copy()
        state['slot_machine'] = slot

    slot.setdefault('active', False)
    slot.setdefault('started_at', 0)
    slot.setdefault('duration_ms', 1200000)
    slot.setdefault('trigger_amount', 20000)
    slot.setdefault('selected_reaction_ids', [])

    if slot.get('active'):
        started_at = int(slot.get('started_at') or 0)
        duration_ms = int(slot.get('duration_ms') or 1200000)
        if started_at and int(time.time() * 1000) - started_at >= duration_ms:
            slot['active'] = False
    return slot

def get_slot_reaction_candidate(selected_ids):
    if not selected_ids:
        return None

    ids = []
    for item_id in selected_ids:
        try:
            parsed_id = int(item_id)
        except (TypeError, ValueError):
            continue
        if parsed_id not in ids:
            ids.append(parsed_id)

    if not ids:
        return None

    placeholders = ','.join(['?'] * len(ids))
    query = f"""
        SELECT id, title, audio_file_id, image_file_id, amount
        FROM reaction_items
        WHERE is_enabled = TRUE AND id IN ({placeholders})
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(db_query(query), tuple(ids))
        rows = cursor.fetchall()

    if not rows:
        return None

    import random
    row = random.choice(rows)
    return {
        'id': row[0],
        'title': row[1],
        'audio_file_id': row[2],
        'image_file_id': row[3],
        'amount': int(row[4] or 0)
    }

def apply_slot_score(state, target_list_key, player_name, score_delta, contribution_delta):
    target_list = state.get(target_list_key, [])
    for bj in target_list:
        if bj.get('name') == player_name:
            bj['score'] = int(bj.get('score') or 0) + score_delta
            bj['contribution'] = int(bj.get('contribution') or 0) + contribution_delta
            target_list.sort(key=lambda a: int(a.get('contribution') or 0), reverse=True)
            state[target_list_key] = target_list
            return bj
    return None

db_write_queue = queue.Queue()

def db_worker():
    while True:
        try:
            new_data, is_initial = db_write_queue.get()
            save_data_sync(new_data, is_initial)
            db_write_queue.task_done()
        except Exception as e:
            print(f"❌ [비동기 DB 저장 백그라운드 오류] {e}")
            time.sleep(1)

threading.Thread(target=db_worker, daemon=True).start()

# 🏦 은행 입출금 통장 거래내역 기록 및 수학적 잔액 검증 엔진
def record_bank_transaction(player_name, score_change, contrib_change=0, tx_type="CHANGE", description=""):
    try:
        now_str = time.strftime('%Y-%m-%d %H:%M:%S')
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # 1. 현재 잔액 조회
            cursor.execute(db_query("SELECT score, contribution FROM players WHERE name = ?"), (player_name,))
            row = cursor.fetchone()
            current_score = row[0] if row else 0
            current_contrib = row[1] if row else 0
            
            # 2. 거래 후 잔액 산출
            new_score_balance = current_score + score_change
            new_contrib_balance = current_contrib + contrib_change
            
            # 3. 은행 장부에 영구 통장 내역 작성 (INSERT)
            if IS_POSTGRES:
                cursor.execute(
                    """INSERT INTO bank_ledger 
                       (timestamp, player_name, tx_type, score_change, score_balance, contrib_change, contrib_balance, description)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                    (now_str, player_name, tx_type, score_change, new_score_balance, contrib_change, new_contrib_balance, description)
                )
            else:
                cursor.execute(
                    """INSERT INTO bank_ledger 
                       (timestamp, player_name, tx_type, score_change, score_balance, contrib_change, contrib_balance, description)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (now_str, player_name, tx_type, score_change, new_score_balance, contrib_change, new_contrib_balance, description)
                )
                
            # 4. 플레이어 실시간 잔액 테이블 갱신 (UPSERT)
            if IS_POSTGRES:
                cursor.execute(
                    "INSERT INTO players (name, score, contribution) VALUES (%s, %s, %s) ON CONFLICT (name) DO UPDATE SET score = EXCLUDED.score, contribution = EXCLUDED.contribution",
                    (player_name, new_score_balance, new_contrib_balance)
                )
            else:
                cursor.execute(
                    "INSERT INTO players (name, score, contribution) VALUES (?, ?, ?) ON CONFLICT(name) DO UPDATE SET score = excluded.score, contribution = excluded.contribution",
                    (player_name, new_score_balance, new_contrib_balance)
                )
                
            return {
                "player_name": player_name,
                "score_change": score_change,
                "score_balance": new_score_balance,
                "contrib_change": contrib_change,
                "contrib_balance": new_contrib_balance,
                "timestamp": now_str
            }
    except Exception as e:
        print(f"❌ [은행 통장 거래 기록 실패] {e}")
        return None

def save_data_sync(new_data, is_initial=False):
    global MEMORY_STATE
    
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            old_scores = {}
            old_contribs = {}
            existing_names = set()
            if not is_initial:
                cursor.execute(db_query("SELECT name, score, contribution FROM players"))
                for row in cursor.fetchall():
                    old_scores[row[0]] = row[1]
                    old_contribs[row[0]] = row[2]
                    existing_names.add(row[0])
            
            # 🏦 [은행 계좌 방식으로 전환] 절대값을 그대로 덮어쓰지 않고,
            # 변화량(diff)만 계산하여 bank_ledger(거래 내역)에 누적하고,
            # players 테이블은 "현재 잔액 - 오직 거래 누적을 통해서만" 갱신되도록 처리합니다.
            # 이렇게 하면 클라이언트가 실수로 잘못된 절대값을 보내더라도 실제 누적 합계 자체는 훼손되지 않습니다.
            if not is_initial:
                for new_p in new_data.get("bjs", []):
                    p_name = new_p["name"]
                    p_score = int(new_p.get("score") or 0)
                    p_contrib = int(new_p.get("contribution") or 0)
                    
                    if p_name in existing_names:
                        o_score = old_scores.get(p_name, 0)
                        o_contrib = old_contribs.get(p_name, 0)
                        score_diff = p_score - o_score
                        contrib_diff = p_contrib - o_contrib
                        
                        if score_diff != 0 or contrib_diff != 0:
                            if score_diff != 0:
                                cursor.execute(
                                    db_query("INSERT INTO donation_history (timestamp, name, amount, current_total, message, source) VALUES (?, ?, ?, ?, ?, ?)"),
                                    (time.strftime('%Y-%m-%d %H:%M:%S'), p_name, score_diff, p_score, "점수 변동 (은행 통장 기록)", "system")
                                )
                            record_bank_transaction(p_name, score_diff, contrib_diff, "MANUAL_CHANGE", f"점수 변동 ({score_diff:+}점) / 기여도 변동 ({contrib_diff:+}점)")
            
            # 2. 플레이어 점수 및 기여도 저장 (항상 최신 점수로 DB에 즉각 UPSERT)
            for bj in new_data.get("bjs", []):
                p_name = bj["name"]
                p_score = int(bj.get("score") or 0)
                p_contrib = int(bj.get("contribution") or 0)
                if IS_POSTGRES:
                    cursor.execute(
                        "INSERT INTO players (name, score, contribution) VALUES (%s, %s, %s) ON CONFLICT (name) DO UPDATE SET score = EXCLUDED.score, contribution = EXCLUDED.contribution",
                        (p_name, p_score, p_contrib)
                    )
                else:
                    cursor.execute(
                        "INSERT INTO players (name, score, contribution) VALUES (?, ?, ?) ON CONFLICT(name) DO UPDATE SET score = excluded.score, contribution = excluded.contribution",
                        (p_name, p_score, p_contrib)
                    )
            
            # 3. 설정 상태 키-값 저장 (kv_store)
            for key, value in new_data.items():
                if key != "bjs":
                    new_val_str = json.dumps(value, ensure_ascii=False)
                    if IS_POSTGRES:
                        cursor.execute(
                            "INSERT INTO kv_store (key, value) VALUES (%s, %s) ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value",
                            (key, new_val_str)
                        )
                    else:
                        cursor.execute(
                            "INSERT OR REPLACE INTO kv_store (key, value) VALUES (?, ?)",
                            (key, new_val_str)
                        )
                            
    except Exception as e:
        print(f"❌ [DB 동기화 저장 실패] {e}")
        raise

LAST_CHECKED_CONTRIB = 0

def check_goal_achievement_status(state):
    global LAST_CHECKED_CONTRIB
    try:
        target_goal = state.get('target_goal', 50000)
        if target_goal <= 0:
            return
            
        bjs = state.get('bjs', [])
        total_contrib = sum(b.get('contribution', 0) for b in bjs)
        
        # 기여도가 100% 이상이고, 기여도가 더 증가하거나 알림이 비활성화 상태면 알림 팝업 재트리거
        if total_contrib >= target_goal:
            if total_contrib > LAST_CHECKED_CONTRIB and not state.get('goal_event_pending', False):
                state['goal_event_pending'] = True
                state['goal_event_approved'] = False
            LAST_CHECKED_CONTRIB = total_contrib
        else:
            LAST_CHECKED_CONTRIB = total_contrib
            state['goal_event_pending'] = False
            state['goal_event_approved'] = False
    except Exception as e:
        print(f"Goal check error: {e}")

def save_data(new_data, is_initial=False):
    global MEMORY_STATE
    check_goal_achievement_status(new_data)
    MEMORY_STATE = new_data
    
    # Vercel 서버리스 환경일 때는 백그라운드 큐를 거치지 않고 즉시 DB에 직접 저장합니다.
    if IS_VERCEL:
        save_data_sync(new_data, is_initial)
    else:
        # 일반 PC나 Render 서버 환경에서는 기존처럼 비동기 큐를 사용합니다.
        db_write_queue.put((new_data, is_initial))

def time_machine_recovery():
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(db_query("DELETE FROM players"))
            cursor.execute(db_query("""
                INSERT INTO players (name, score, contribution)
                SELECT name, current_total, current_total 
                FROM donation_history 
                WHERE id IN (
                    SELECT MAX(id) FROM donation_history GROUP BY name
                )
            """))
            
        global MEMORY_STATE
        MEMORY_STATE = None 
        load_data()
        return True
    except Exception as e:
        print(f"❌ [복구 실패] {e}")
        return False

# ==========================================
# 📡 실시간 SSE 라우트 및 제네레이터
# ==========================================
@app.route('/api/stream')
def sse_stream():
    q = queue.Queue()
    with sse_lock:
        sse_clients.append(q)
        
    def event_generator():
        initial_state = load_data()
        yield f"event: init\ndata: {json.dumps(initial_state, ensure_ascii=False)}\n\n"
        
        if os.path.exists(LAYOUT_FILE):
            try:
                with open(LAYOUT_FILE, 'r', encoding='utf-8') as f:
                    layout_data = json.load(f)
                yield f"event: layout\ndata: {json.dumps(layout_data, ensure_ascii=False)}\n\n"
            except Exception:
                pass
                
        while True:
            try:
                msg = q.get(timeout=15.0)
                yield msg
            except queue.Empty:
                yield "event: ping\ndata: {}\n\n"
            except GeneratorExit:
                break
                
        with sse_lock:
            if q in sse_clients:
                sse_clients.remove(q)
                
    resp = app.response_class(event_generator(), mimetype='text/event-stream')
    resp.headers['X-Accel-Buffering'] = 'no'
    resp.headers['Cache-Control'] = 'no-cache'
    resp.headers['Connection'] = 'keep-alive'
    return resp

@app.route('/api/ping')
def api_ping():
    return jsonify({'status': 'pong'})

@app.route('/api/debug')
def api_debug():
    """Vercel/Supabase 연결 디버그 엔드포인트"""
    import traceback
    result = {
        'is_vercel': IS_VERCEL,
        'is_postgres': IS_POSTGRES,
        'has_database_url': bool(DATABASE_URL),
        'database_url_prefix': DATABASE_URL[:20] + '...' if DATABASE_URL else None,
        'has_psycopg2': psycopg2 is not None,
        'python_version': sys.version,
    }
    # DB 연결 테스트
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            result['db_connect'] = 'success'
            # 테이블 목록 확인
            try:
                cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public'")
                tables = [row[0] for row in cursor.fetchall()]
                result['tables'] = tables
            except Exception as e:
                result['tables_error'] = str(e)
            # kv_store 데이터 확인
            try:
                cursor.execute("SELECT key FROM kv_store")
                kv_keys = [row[0] for row in cursor.fetchall()]
                result['kv_keys'] = kv_keys
                result['kv_count'] = len(kv_keys)
            except Exception as e:
                result['kv_error'] = str(e)
            # players 데이터 확인
            try:
                cursor.execute("SELECT COUNT(*) FROM players")
                result['player_count'] = cursor.fetchone()[0]
            except Exception as e:
                result['players_error'] = str(e)
            # 각 테이블의 실제 컬럼 구조 확인
            try:
                cursor.execute("""
                    SELECT table_name, column_name, data_type 
                    FROM information_schema.columns 
                    WHERE table_schema = 'public' 
                    ORDER BY table_name, ordinal_position
                """)
                schema_info = {}
                for row in cursor.fetchall():
                    tbl = row[0]
                    if tbl not in schema_info:
                        schema_info[tbl] = []
                    schema_info[tbl].append({'col': row[1], 'type': row[2]})
                result['schema'] = schema_info
            except Exception as e:
                result['schema_error'] = str(e)
    except Exception as e:
        result['db_connect'] = 'failed'
        result['db_error'] = str(e)
    # load_data() 테스트
    try:
        global MEMORY_STATE
        old_state = MEMORY_STATE
        MEMORY_STATE = None  # 강제 리로드
        data = load_data()
        result['load_data'] = 'success'
        result['load_data_keys'] = list(data.keys()) if isinstance(data, dict) else str(type(data))
        result['bjs_count'] = len(data.get('bjs', [])) if isinstance(data, dict) else 0
    except Exception as e:
        result['load_data'] = 'failed'
        result['load_data_error'] = str(e)
        result['load_data_traceback'] = traceback.format_exc()
    finally:
        MEMORY_STATE = old_state  # 디버그 조회가 라이브 메모리 상태를 바꾸지 않도록 복구
    return jsonify(result)

# ==========================================
# 👥 BJ 일괄 등록 API
# ==========================================
@app.route('/api/bjs/import', methods=['POST'])
def import_bjs():
    try:
        req = request.json
        names = req.get('names', [])
        if not names:
            return jsonify({'status': 'error', 'message': '등록할 이름이 없습니다.'}), 400
            
        with file_lock:
            state = load_data()
            overwrite = req.get('overwrite', False)
            new_bjs = []
            
            for name in names:
                name = name.strip()
                if not name:
                    continue
                new_bjs.append({"name": name, "score": 0, "contribution": 0})
                
            if overwrite:
                state['bjs'] = new_bjs
            else:
                existing_names = {bj['name'] for bj in state.get('bjs', [])}
                for new_bj in new_bjs:
                    if new_bj['name'] not in existing_names:
                        state['bjs'].append(new_bj)
                        
            save_data(state)
            broadcast_event('update', state)
            
        return jsonify({'status': 'success', 'count': len(new_bjs)})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

# ==========================================
# 🌐 페이지 라우팅
# ==========================================
@app.route('/')
def serve_root():
    return serve_html_file('overlay.html')

@app.route('/overlay')
@app.route('/overlay.html')
def serve_overlay():
    return serve_html_file('overlay.html')

@app.route('/alertbox')
@app.route('/alertbox.html')
def serve_alertbox():
    return serve_html_file('alertbox.html')

@app.route('/streamdeck')
@app.route('/streamdeck.html')
def serve_streamdeck():
    return serve_html_file('streamdeck.html')

@app.route('/controller')
def serve_controller():
    # 1. 쿼리 매개변수로 명시적 모드가 지정된 경우 우선 처리
    mode = request.args.get('mode', '').lower()
    if mode == 'mobile':
        return serve_html_file('mobile.html')
    elif mode == 'desktop':
        return serve_html_file('controller.html')
        
    # 2. 자동으로 User-Agent 판별
    ua = request.headers.get('User-Agent', '').lower()
    mobile_keywords = ['mobile', 'android', 'iphone', 'ipad', 'ipod', 'webos', 'blackberry', 'opera mini', 'opera mobi', 'windows phone']
    is_mobile = any(kw in ua for kw in mobile_keywords)
    if is_mobile:
        return serve_html_file('mobile.html')
    return serve_html_file('controller.html')

@app.route('/mobile')
def serve_mobile():
    return serve_html_file('mobile.html')

@app.route('/admin')
@app.route('/admin.html')
def serve_admin():
    return serve_html_file('admin.html')

@app.route('/upload')
@app.route('/노래등록')
def serve_upload():
    return serve_html_file('upload.html')

@app.route('/<path:filename>')
def serve_dynamic_file(filename):
    for root in [BASE_DIR, BUNDLE_DIR]:
        if os.path.exists(os.path.join(root, filename)):
            return send_from_directory(root, filename)
    return jsonify({"error": "File not found"}), 404

# ==========================================
# 🛡️ 투네이션 후원 안전 접수 및 파서
# ==========================================
@app.route('/api/donation', methods=['POST'])
def receive_donation():
    try:
        new_don = request.json or {}
        amount = int(new_don.get('amount', 0))
        tx_id = new_don.get('tx_id')
        
        # 1. 음수(0원 미만) 후원 금액 차단 (0원 시그니처 후원 등 허용)
        if amount < 0:
            return jsonify({"status": "error", "message": "Invalid amount"}), 400
            
        # 2. tx_id 중복 검사로 중복 처리 차단
        if tx_id:
            try:
                with get_db_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(db_query("SELECT id FROM donation_history WHERE tx_id = ?"), (tx_id,))
                    if cursor.fetchone():
                        return jsonify({"status": "success", "message": "Duplicate donation ignored."})
            except Exception as dbe:
                print(f"⚠️ [tx_id 중복 확인 오류] {dbe}")

        with file_lock:
            state = load_data()
            don_id = f"don_{int(time.time() * 1000)}"
            name = new_don.get('name', '익명')
            msg = new_don.get('message', '')
            
            parsed_name = name.strip()
            cleaned_msg = msg.strip()
            
            # 💡 [핵심] 메시지 내 콜론(:)을 감지하여 이름과 메시지를 분리해주는 오토 파서 (시그니처 신청 태그는 제외)
            cleaned_msg_for_split = cleaned_msg.replace('：', ':')
            if cleaned_msg_for_split and ':' in cleaned_msg_for_split and not cleaned_msg.startswith("[시그니처 신청:"):
                split_char = ':' if ':' in cleaned_msg else '：'
                parts = cleaned_msg.split(split_char, 1)
                potential_name = parts[0].strip()
                if 0 < len(potential_name) <= 15:
                    parsed_name = potential_name
                    cleaned_msg = parts[1].strip()
                    
            if parsed_name.endswith('님') and len(parsed_name) > 1:
                parsed_name = parsed_name[:-1]
                
            parsed_don_entry = {
                'id': don_id,
                'name': parsed_name,
                'amount': amount,
                'message': cleaned_msg,
                'time': time.strftime('%H:%M:%S')
            }
            state['pending_donations'].append(parsed_don_entry)
            state['reaction_mode'] = True
            
            # BJ 점수판 업데이트
            current_total = amount
            target_list_key = 'extra_bjs' if state.get('extra_game_active', False) else 'bjs'
            
            if target_list_key == 'extra_bjs' and not state.get('extra_bjs'):
                state['extra_bjs'] = [{"name": bj['name'], "score": 0, "contribution": 0} for bj in state.get('bjs', [])]

            slot_result = None
            slot = normalize_slot_machine_state(state)
            if amount == int(slot.get('trigger_amount') or 20000) and slot.get('active'):
                # 💡 [개편] 트리거 금액 후원이 들어와도 슬롯머신을 즉시 자동 회전시키지 않고,
                # 운영자가 "슬롯" 탭에서 직접 확인 후 "돌리기" 버튼을 눌러야 실제로 회전/당첨 처리되도록 대기열에만 등록합니다.
                # ⚠️ [버그 수정] 슬롯 대기열로 넘어가는 후원은 latest_donation을 갱신하지 않아
                # 오버레이에 "후원하셨습니다" 팝업이 먼저 뜨는 것을 방지합니다. (돌리기를 누를 때만 1회 노출)
                slot_result = True  # 아래 근사치 매칭 자동 리액션 블록 진입을 막기 위한 플래그
                if 'pending_slot_spins' not in state or not isinstance(state.get('pending_slot_spins'), list):
                    state['pending_slot_spins'] = []
                spin_id = f"spin_{uuid.uuid4().hex}"
                state['pending_slot_spins'].append({
                    "id": spin_id,
                    "don_id": don_id,
                    "name": parsed_name,
                    "amount": amount,
                    "message": cleaned_msg,
                    "time": time.strftime('%H:%M:%S'),
                    "target_list_key": target_list_key
                })
                print(f"  🎰 [슬롯머신 대기 등록] {parsed_name} {amount}원 -> 슬롯 탭에서 수동으로 돌려주세요. (spin_id={spin_id})")
            else:
                # 슬롯 대기열로 넘어가지 않는 일반 후원인 경우에만 오버레이 팝업을 즉시 노출
                state['latest_donation'] = {
                    'id': don_id,
                    'name': parsed_name,
                    'amount': amount,
                    'message': cleaned_msg,
                    'time': time.time()
                }
            # [비활성화] 닉네임 직접 매칭 자동 점수 가산 기능 해제 (모든 후원이 승인 대기함으로 모이도록 설정)
            # for bj in state.get(target_list_key, []):
            #     if bj['name'] == parsed_name:
            #         add_point = int(amount / 10000 + 0.5)
            #         bj['score'] += add_point
            #         bj['contribution'] = bj.get('contribution', 0) + add_point
            #         current_total = bj['score']
            #         break
            try:
                with get_db_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        db_query("INSERT INTO donation_history (timestamp, name, amount, current_total, message, source, tx_id) VALUES (?, ?, ?, ?, ?, ?, ?)"),
                        (time.strftime('%Y-%m-%d %H:%M:%S'), parsed_name, amount, current_total, cleaned_msg, "toonation", tx_id)
                    )
            except Exception as dbe:
                print(f"[장부 기록 오류] {dbe}")
                
            # 🎵 자동 리액션 송 연동 감지 (근사치 매칭: 후원금액 이하 중 가장 가까운 리액션)
            if amount > 0 and not slot_result:
                try:
                    with get_db_connection() as conn:
                        cursor = conn.cursor()
                        cursor.execute(db_query("""
                            SELECT i.id, i.title, fa.filename as audio_filename, fi.filename as image_filename, i.amount 
                            FROM reaction_items i
                            LEFT JOIN reaction_files fa ON i.audio_file_id = fa.id
                            LEFT JOIN reaction_files fi ON i.image_file_id = fi.id
                            WHERE i.is_enabled = TRUE AND i.amount <= ? 
                            ORDER BY i.amount DESC LIMIT 1
                        """), (amount,))
                        row = cursor.fetchone()
                        if row:
                            r_id, r_title, r_audio_fname, r_image_fname, r_amount = row
                            
                            # 실물 파일명 100% 스마트 매칭
                            final_audio_fname = r_audio_fname
                            final_image_fname = r_image_fname

                            # media_cache/ 내의 실물 파일명 직접 찾기 fallback
                            if os.path.exists(MEDIA_CACHE_DIR):
                                for f in os.listdir(MEDIA_CACHE_DIR):
                                    f_ext = os.path.splitext(f)[1].lower()
                                    if f.startswith(f"{r_title}_{r_amount}") or f.startswith(f"{r_amount}_{r_amount}"):
                                        if f_ext in ('.mp3', '.wav', '.mp4', '.m4a') and not final_audio_fname:
                                            final_audio_fname = f
                                        elif f_ext in ('.png', '.jpg', '.jpeg', '.webp', '.gif') and not final_image_fname:
                                            final_image_fname = f

                            audio_url = f"/api/reaction/file/{final_audio_fname}" if final_audio_fname else ""
                            image_url = f"/api/reaction/file/{final_image_fname}" if final_image_fname else ""
                            
                            reaction_uuid = f"rq_{uuid.uuid4().hex}"
                            state['reaction_queue'].append({
                                "id": reaction_uuid,
                                "item_id": r_id,
                                "title": r_title,
                                "audio_url": audio_url,
                                "image_url": image_url,
                                "amount": amount,
                                "donator": parsed_name,
                                "message": cleaned_msg
                            })
                            state['reaction_mode'] = True
                            print(f"  🎵 [자동 리액션 발동 성공] 후원금액 {amount}원 → 매칭 '{r_title}' ({r_amount}원) ➡️ 음원({audio_url}), 사진({image_url}) 큐 추가 완료")
                except Exception as e:
                    print(f"⚠️ [자동 리액션 감지 오류] {e}")
                
            save_data(state)
            broadcast_event('update', state)
            
            print("  🎯 [최종 처리 결과]")
            print(f"    ▶ 최종 분류된 이름  : {parsed_name}")
            print(f"    ▶ 최종 분류된 메시지: {cleaned_msg}")
            print("    ▶ 자동 승인 처리 여부: 🟡 클래식 수동 정산 모드 작동 (승인 대기함 적립)")
            print("======================================================================\n")
            
        return jsonify({'status': 'success', 'id': don_id})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

# ==========================================
# 📺 CORS 우회 유튜브 검색 API (SSL 무시)
# ==========================================
@app.route('/api/yt/search')
def yt_search():
    query = request.args.get('q', '')
    if not query:
        return jsonify([])
        
    instances = ['https://yewtu.be', 'https://invidious.flokinet.to', 'https://iv.melmac.space']
    ssl_ctx = ssl._create_unverified_context()
    
    for base in instances:
        try:
            encoded_query = urllib.parse.quote(query)
            url = f"{base}/api/v1/search?q={encoded_query}"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            
            with urllib.request.urlopen(req, context=ssl_ctx, timeout=3) as response:
                data = json.loads(response.read().decode('utf-8'))
                results = []
                for item in data:
                    if item.get('type') == 'video':
                         length = item.get('lengthSeconds', 0)
                         mins = length // 60
                         secs = length % 60
                         duration_str = f"{mins}:{secs:02d}"
                         
                         video_id = item.get('videoId', '')
                         results.append({
                             'title': item.get('title', ''),
                             'videoId': video_id,
                             'author': item.get('author', ''),
                             'duration': duration_str,
                             'thumbnail': f"https://img.youtube.com/vi/{video_id}/mqdefault.jpg"
                         })
                return jsonify(results)
        except Exception as e:
            print(f"[YT Search Exception on {base}] {e}")
            continue
            
    return jsonify([])

@app.route('/api/data', methods=['GET', 'POST'])
def api_data():
    try:
        if request.method == 'POST':
            with file_lock:
                state = request.json or {}
                force_write = request.args.get('force') == '1' or state.pop('_force', False)
                
                # [버그 패치] 조종실에서 수동 리액션 스위치를 끌 때(False) 
                # 큐에 대기열이 차 있으면 동기화 루프로 인해 즉시 다시 켜지는 현상을 원천 방지
                if 'reaction_mode' in state and state['reaction_mode'] is False:
                    state['reaction_queue'] = []
                    
                current_state = load_data()
                
                client_version = state.get('version', 0)
                server_version = current_state.get('version', 1)

                if not force_write and client_version and client_version < server_version:
                    return jsonify({
                        "status": "conflict",
                        "message": "Server state is newer. Reload before saving.",
                        "server_version": server_version,
                        "client_version": client_version
                    }), 409
                
                state['version'] = max(client_version, server_version) + 1
                save_data(state)
                broadcast_event('update', state)
            return jsonify({"status": "success", "server_version": state['version']})
            
        state = load_data()
        if isinstance(state, dict):
            state = state.copy()
            state['server_time'] = int(time.time() * 1000)
        return jsonify(state)
    except Exception as e:
        import traceback
        return jsonify({'status': 'error', 'message': str(e), 'traceback': traceback.format_exc()}), 500

@app.route('/api/roulette/winner', methods=['POST'])
def api_roulette_winner():
    try:
        req_data = request.json
        winner_name = req_data.get('name', '익명')
        with file_lock:
            state = load_data()
            if 'roulette' not in state:
                state['roulette'] = {
                    "command": None,
                    "command_time": 0,
                    "weight_type": "equal",
                    "select_name": "",
                    "select_index": -1,
                    "winner_name": None,
                    "is_spinning": False,
                    "item_source": "bj",
                    "custom_items": ["벌칙 1", "벌칙 2", "벌칙 3", "벌칙 4", "벌칙 5"]
                }
            state['roulette']['winner_name'] = winner_name
            state['roulette']['command'] = 'ended'
            state['roulette']['is_spinning'] = False
            state['roulette']['command_time'] = int(time.time() * 1000)
            state['roulette_enabled'] = False
            
            # 랭킹 로그에 기록 추가
            time_str = time.strftime('%H:%M:%S')
            if 'logs' not in state:
                state['logs'] = []
            state['logs'].insert(0, {
                'time': time_str,
                'name': f"🎡 룰렛 결과: {winner_name}",
                'val': 0
            })
            if len(state['logs']) > 200:
                state['logs'] = state['logs'][:200]
                
            save_data(state)
            broadcast_event('update', state)
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/layout', methods=['GET', 'POST'])
def api_layout():
    if request.method == 'POST':
        if IS_VERCEL:
            # Vercel 서버리스: 읽기전용 파일시스템, 메모리에서만 처리
            broadcast_event('layout', request.json)
            return jsonify({"status": "success", "message": "Layout updated in memory (Vercel read-only filesystem)"})
        with open(LAYOUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(request.json, f, ensure_ascii=False, indent=4)
        broadcast_event('layout', request.json)
        return jsonify({"status": "success"})
    if os.path.exists(LAYOUT_FILE):
        with open(LAYOUT_FILE, 'r', encoding='utf-8') as f:
            return jsonify(json.load(f))
    return jsonify({})

# ==========================================
# 🎮 번외 게임 모드 제어 API
# ==========================================
@app.route('/api/extra_game/start', methods=['POST'])
def extra_game_start():
    try:
        with file_lock:
            state = load_data()
            state["extra_game_active"] = True
            
            # Initialize extra_bjs with all players from bjs, reset scores to 0
            state["extra_bjs"] = []
            for bj in state.get("bjs", []):
                state["extra_bjs"].append({
                    "name": bj["name"],
                    "score": 0,
                    "contribution": 0
                })
                
            save_data(state)
            broadcast_event('update', state)
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/extra_game/end', methods=['POST'])
def extra_game_end():
    try:
        with file_lock:
            state = load_data()
            if not state.get("extra_game_active", False) or "extra_bjs" not in state:
                return jsonify({"status": "error", "message": "진행 중인 번외 게임이 없습니다."}), 400
                
            extra_scores = {bj["name"]: bj for bj in state.get("extra_bjs", [])}
            
            for bj in state.get("bjs", []):
                bj_name = bj["name"]
                if bj_name in extra_scores:
                    bj["score"] += extra_scores[bj_name]["score"]
                    bj["contribution"] = bj.get("contribution", 0) + extra_scores[bj_name].get("contribution", 0)
                    
            state["extra_game_active"] = False
            state["extra_bjs"] = []
            
            save_data(state)
            broadcast_event('update', state)
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/extra_game/cancel', methods=['POST'])
def extra_game_cancel():
    try:
        with file_lock:
            state = load_data()
            state["extra_game_active"] = False
            state["extra_bjs"] = []
            
            save_data(state)
            broadcast_event('update', state)
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# ==========================================
# 💾 타임머신 스냅샷 API
# ==========================================
@app.route('/api/snapshots', methods=['GET'])
def get_snapshots():
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(db_query("SELECT id, timestamp, summary FROM snapshots ORDER BY id DESC"))
            rows = cursor.fetchall()
            snapshots = [{"id": r[0], "timestamp": r[1], "summary": r[2]} for r in rows]
        return jsonify({"status": "success", "snapshots": snapshots})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/snapshots/manual', methods=['POST'])
def create_manual_snapshot():
    try:
        req_data = request.json
        label = req_data.get("label", "수동 백업")
        create_snapshot_record(label)
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/snapshots/restore', methods=['POST'])
def restore_snapshot():
    try:
        req_data = request.json
        snap_id = req_data.get("id")
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(db_query("SELECT state_json FROM snapshots WHERE id = ?"), (snap_id,))
            row = cursor.fetchone()
            if not row:
                return jsonify({"status": "error", "message": "스냅샷을 찾을 수 없습니다."}), 404
            state_json = row[0]
            
        with file_lock:
            state = json.loads(state_json)
            save_data(state)
            broadcast_event('update', state)
            
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/snapshots/delete', methods=['POST'])
def delete_snapshot():
    try:
        req_data = request.json
        snap_id = req_data.get("id")
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(db_query("DELETE FROM snapshots WHERE id = ?"), (snap_id,))
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/server/status', methods=['GET'])
def get_server_status():
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            # Get player count
            cursor.execute(db_query("SELECT COUNT(*) FROM players"))
            player_count = cursor.fetchone()[0]
            
            # Get donation history count
            cursor.execute(db_query("SELECT COUNT(*) FROM donation_history"))
            history_count = cursor.fetchone()[0]
            
            # Get snapshot count
            cursor.execute(db_query("SELECT COUNT(*) FROM snapshots"))
            snapshot_count = cursor.fetchone()[0]
            
            # Get last 30 logs from donation_history
            cursor.execute(db_query("SELECT id, timestamp, name, amount, current_total, message, source FROM donation_history ORDER BY id DESC LIMIT 30"))
            history_rows = cursor.fetchall()
            history_list = []
            for r in history_rows:
                history_list.append({
                    'id': r[0],
                    'timestamp': r[1],
                    'name': r[2],
                    'amount': r[3],
                    'current_total': r[4],
                    'message': r[5],
                    'source': r[6]
                })
                
        return jsonify({
            'status': 'success',
            'is_postgres': IS_POSTGRES,
            'player_count': player_count,
            'history_count': history_count,
            'snapshot_count': snapshot_count,
            'logs': history_list
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/server/reset', methods=['POST'])
def reset_server_database():
    try:
        global MEMORY_STATE
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(db_query("DELETE FROM players"))
            cursor.execute(db_query("DELETE FROM kv_store"))
            cursor.execute(db_query("DELETE FROM donation_history"))
            cursor.execute(db_query("DELETE FROM snapshots"))
            
        MEMORY_STATE = DEFAULT_STATE.copy()
        save_data(MEMORY_STATE, is_initial=True)
        broadcast_event('update', MEMORY_STATE)
        return jsonify({"status": "success", "message": "데이터베이스가 성공적으로 완전히 리셋되었습니다."})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/bank/statement/<player_name>', methods=['GET'])
def get_bank_statement(player_name):
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                db_query("""SELECT timestamp, tx_type, score_change, score_balance, contrib_change, contrib_balance, description 
                            FROM bank_ledger WHERE player_name = ? ORDER BY id DESC LIMIT 50"""),
                (player_name,)
            )
            rows = cursor.fetchall()
            statement = []
            for r in rows:
                statement.append({
                    "timestamp": r[0],
                    "tx_type": r[1],
                    "score_change": r[2],
                    "score_balance": r[3],
                    "contrib_change": r[4],
                    "contrib_balance": r[5],
                    "description": r[6]
                })
            
            cursor.execute(db_query("SELECT score, contribution FROM players WHERE name = ?"), (player_name,))
            p_row = cursor.fetchone()
            current_score = p_row[0] if p_row else 0
            current_contrib = p_row[1] if p_row else 0
            
            return jsonify({
                "status": "success",
                "player_name": player_name,
                "current_score_balance": current_score,
                "current_contrib_balance": current_contrib,
                "statement_history": statement
            })
    except Exception as e:
        print(f"Error fetching bank statement: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/bank/recalculate', methods=['POST'])
def recalculate_bank_balances():
    """🏦 [은행 원장 재정산] bank_ledger에 쌓인 모든 거래 내역을 처음부터 순서대로 다시 합산하여
    players 테이블의 현재 잔액(score, contribution)을 재구성합니다.
    혹시라도 players 테이블 캐시가 어떤 이유로 실제 누적 합계와 어긋났다고 의심될 때
    운영자가 이 API를 호출하면 거래 원장을 기준으로 잔액을 정확하게 다시 맞출 수 있습니다."""
    try:
        global MEMORY_STATE
        with file_lock:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(db_query("""
                    SELECT player_name, SUM(score_change), SUM(contrib_change)
                    FROM bank_ledger
                    GROUP BY player_name
                """))
                totals = {row[0]: (row[1] or 0, row[2] or 0) for row in cursor.fetchall()}
                
                # 기존 players 테이블에 있는 이름 중 원장에 거래 기록이 없는 경우(예: 최초 등록만 되고 변동 없음)는
                # 현재 값을 그대로 유지하고, 원장에 거래가 있는 이름은 원장 합계로 덮어씁니다.
                cursor.execute(db_query("SELECT name, score, contribution FROM players"))
                existing = {row[0]: (row[1], row[2]) for row in cursor.fetchall()}
                
                updated_count = 0
                for name, (score_sum, contrib_sum) in totals.items():
                    if IS_POSTGRES:
                        cursor.execute(
                            "INSERT INTO players (name, score, contribution) VALUES (%s, %s, %s) ON CONFLICT (name) DO UPDATE SET score = EXCLUDED.score, contribution = EXCLUDED.contribution",
                            (name, score_sum, contrib_sum)
                        )
                    else:
                        cursor.execute(
                            "INSERT INTO players (name, score, contribution) VALUES (?, ?, ?) ON CONFLICT(name) DO UPDATE SET score = excluded.score, contribution = excluded.contribution",
                            (name, score_sum, contrib_sum)
                        )
                    updated_count += 1
            
            MEMORY_STATE = None
            state = load_data()
            broadcast_event('update', state)
            
        return jsonify({
            "status": "success",
            "message": f"은행 원장 기준으로 {updated_count}명의 잔액을 재정산했습니다.",
            "updated_count": updated_count
        })
    except Exception as e:
        print(f"❌ [잔액 재정산 실패] {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/server/end_broadcast', methods=['POST'])
def end_broadcast():
    try:
        global MEMORY_STATE
        with file_lock:
            current_state = load_data()
            create_snapshot_record("방송 종료 전 자동 백업", current_state)

            # 1. Clear today's live state only. Keep history and snapshots for recovery/audit.
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(db_query("DELETE FROM players"))
                # Delete kv_store keys that are NOT persistent configurations
                cursor.execute(
                    db_query("DELETE FROM kv_store WHERE key NOT IN (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"), 
                    ('theme', 'neon_speed', 'saved_colors', 'target_goal', 'account', 'effect_rules', 'screen_effect', 'ticker_enabled', 'ticker_speed', 'ticker_text', 'totp_secret')
                )
            
            # 2. Get current state from database (which will have only configurations preserved)
            state = load_data()
            
            # Reset memory state and set broadcast_active to False
            state['broadcast_active'] = False
            state['bjs'] = []
            state['bottom_fixed']['score'] = 0
            state['reaction_mode'] = False
            state['match_data'] = {"active": False, "players": [], "time_left_ms": 180000, "is_running": False}
            state['pending_donations'] = []
            state['latest_donation'] = {"name": "", "amount": 0, "message": "", "time": 0}
            state['extra_game_active'] = False
            state['extra_bjs'] = []
            state['roulette_enabled'] = False
            if 'roulette' in state:
                state['roulette']['winner_name'] = None
                state['roulette']['is_spinning'] = False
                state['roulette']['select_name'] = ""
                state['roulette']['select_index'] = -1
            state['logs'] = []
            state['match_logs'] = []
            
            save_data(state)
            broadcast_event('update', state)
            
        return jsonify({"status": "success", "message": "방송이 종료되고 오늘의 데이터가 리셋되었습니다."})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/server/start_broadcast', methods=['POST'])
def start_broadcast():
    try:
        global MEMORY_STATE
        req = request.json or {}
        names = req.get('names', [])
        if not names:
            return jsonify({"status": "error", "message": "최소 한 명 이상의 플레이어를 등록해야 합니다."}), 400
        if len(names) > 10:
            return jsonify({"status": "error", "message": "플레이어는 최대 10명까지 등록할 수 있습니다."}), 400
            
        with file_lock:
            current_state = load_data()
            if current_state.get('broadcast_active') or current_state.get('bjs'):
                create_snapshot_record("방송 재시작 전 자동 백업", current_state)

            # 1. Clear live player/state tables only. Keep history and snapshots.
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(db_query("DELETE FROM players"))
                # Delete kv_store keys that are NOT persistent configurations
                cursor.execute(
                    db_query("DELETE FROM kv_store WHERE key NOT IN (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"), 
                    ('theme', 'neon_speed', 'saved_colors', 'target_goal', 'account', 'effect_rules', 'screen_effect', 'ticker_enabled', 'ticker_speed', 'ticker_text', 'totp_secret')
                )
            
            # 2. Get current state from database (which will have only configurations preserved)
            state = load_data()
            
            # 3. Set broadcast_active to True and initialize players
            state['broadcast_active'] = True
            state['bjs'] = [{"name": name.strip(), "score": 0, "contribution": 0} for name in names if name.strip()]
            state['bottom_fixed']['score'] = 0
            state['reaction_mode'] = False
            state['match_data'] = {"active": False, "players": [], "time_left_ms": 180000, "is_running": False}
            state['pending_donations'] = []
            state['latest_donation'] = {"name": "", "amount": 0, "message": "", "time": 0}
            state['extra_game_active'] = False
            state['extra_bjs'] = []
            state['roulette_enabled'] = False
            if 'roulette' in state:
                state['roulette']['winner_name'] = None
                state['roulette']['is_spinning'] = False
                state['roulette']['select_name'] = ""
                state['roulette']['select_index'] = -1
            state['logs'] = []
            state['match_logs'] = []
            
            save_data(state)
            broadcast_event('update', state)
            
        return jsonify({"status": "success", "message": "방송이 활성화되었습니다."})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# ==========================================
# 📋 수동 조작 이력 조회 API
# ==========================================
@app.route('/api/manual_logs', methods=['GET'])
def get_manual_logs():
    try:
        source_filter = request.args.get('source', 'all')  # all, mobile, toonation
        name_filter = request.args.get('name', '').strip()
        page = max(1, int(request.args.get('page', 1)))
        per_page = min(200, max(10, int(request.args.get('per_page', 50))))
        export_csv = request.args.get('export', '') == 'csv'
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Build WHERE clause
            conditions = []
            params = []
            if source_filter == 'mobile':
                conditions.append("source = " + ("$1" if IS_POSTGRES else "?"))
                params.append("mobile")
            elif source_filter == 'toonation':
                conditions.append("source = " + ("$1" if IS_POSTGRES else "?"))
                params.append("toonation")
            
            if name_filter:
                param_idx = len(params) + 1
                if IS_POSTGRES:
                    conditions.append(f"name LIKE ${param_idx}")
                else:
                    conditions.append("name LIKE ?")
                params.append(f"%{name_filter}%")
            
            where_clause = (" WHERE " + " AND ".join(conditions)) if conditions else ""
            
            # Get total count
            count_q = f"SELECT COUNT(*) FROM donation_history{where_clause}"
            if IS_POSTGRES:
                # Replace $N placeholders for count query
                pg_count_q = count_q
                for i in range(len(params)):
                    pg_count_q = pg_count_q.replace(f"${i+1}", "%s", 1)
                cursor.execute(pg_count_q, params)
            else:
                cursor.execute(count_q, params)
            total_count = cursor.fetchone()[0]
            
            # CSV Export mode
            if export_csv:
                data_q = f"SELECT id, timestamp, name, amount, current_total, message, source FROM donation_history{where_clause} ORDER BY id DESC"
                if IS_POSTGRES:
                    pg_data_q = data_q
                    for i in range(len(params)):
                        pg_data_q = pg_data_q.replace(f"${i+1}", "%s", 1)
                    cursor.execute(pg_data_q, params)
                else:
                    cursor.execute(data_q, params)
                rows = cursor.fetchall()
                
                import io, csv
                output = io.StringIO()
                output.write('\ufeff')  # BOM for Excel
                writer = csv.writer(output)
                writer.writerow(['ID', '시간', '이름', '변동량', '누적점수', '메시지', '출처'])
                for r in rows:
                    writer.writerow([r[0], r[1], r[2], r[3], r[4], r[5], r[6]])
                
                from flask import Response
                return Response(
                    output.getvalue(),
                    mimetype='text/csv',
                    headers={'Content-Disposition': f'attachment; filename=score_log_{time.strftime("%Y%m%d_%H%M%S")}.csv'}
                )
            
            # Paginated fetch
            offset = (page - 1) * per_page
            if IS_POSTGRES:
                param_idx_limit = len(params) + 1
                param_idx_offset = len(params) + 2
                data_q = f"SELECT id, timestamp, name, amount, current_total, message, source FROM donation_history{where_clause} ORDER BY id DESC LIMIT ${param_idx_limit} OFFSET ${param_idx_offset}"
                pg_data_q = data_q
                all_params = params + [per_page, offset]
                for i in range(len(all_params)):
                    pg_data_q = pg_data_q.replace(f"${i+1}", "%s", 1)
                cursor.execute(pg_data_q, all_params)
            else:
                data_q = f"SELECT id, timestamp, name, amount, current_total, message, source FROM donation_history{where_clause} ORDER BY id DESC LIMIT ? OFFSET ?"
                cursor.execute(data_q, params + [per_page, offset])
            
            rows = cursor.fetchall()
            logs = []
            for r in rows:
                logs.append({
                    'id': r[0], 'timestamp': r[1], 'name': r[2],
                    'amount': r[3], 'current_total': r[4],
                    'message': r[5], 'source': r[6]
                })
        
        total_pages = max(1, (total_count + per_page - 1) // per_page)
        return jsonify({
            'status': 'success',
            'logs': logs,
            'page': page,
            'per_page': per_page,
            'total_count': total_count,
            'total_pages': total_pages
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

# ==========================================
# ⏪ 시간 여행 복원 API (오늘 지정 시간 기준)
# ==========================================
@app.route('/api/time_machine/restore_by_time', methods=['POST'])
def restore_by_time():
    try:
        req_data = request.json
        time_str = req_data.get('time', '').strip()
        if not time_str:
            return jsonify({'status': 'error', 'message': '이동할 시간을 입력해주세요.'}), 400
            
        today_str = time.strftime('%Y-%m-%d')
        target_ts = f"{today_str} {time_str}"
        if len(time_str.split(':')) == 2:
            target_ts += ':00'
            
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(db_query("""
                SELECT name, current_total 
                FROM donation_history 
                WHERE id IN (
                    SELECT MAX(id) 
                    FROM donation_history 
                    WHERE timestamp <= ? 
                    GROUP BY name
                )
            """), (target_ts,))
            history_rows = cursor.fetchall()
            
            if not history_rows:
                return jsonify({'status': 'error', 'message': f'[{target_ts}] 시점 또는 그 이전에 기록된 장부가 없습니다.'}), 404
                
            cursor.execute(db_query("SELECT key, value FROM kv_store WHERE key = 'target_goal'"))
            goal_row = cursor.fetchone()
            target_goal = json.loads(goal_row[1]) if goal_row else 50000
            
        import copy
        current_state = load_data()
        restored_state = copy.deepcopy(current_state)
        restored_state['target_goal'] = target_goal
        restored_state['bjs'] = []
        
        for name, score in history_rows:
            restored_state['bjs'].append({
                'name': name,
                'score': score,
                'contribution': score
            })
            
        restored_state['bjs'].sort(key=lambda x: x['contribution'], reverse=True)
        
        global MEMORY_STATE
        MEMORY_STATE = restored_state
        save_data(restored_state)
        broadcast_event('update', restored_state)
        
        return jsonify({
            'status': 'success',
            'message': f'⏳ [시간여행 성공]\n오늘 {time_str} 시점의 플레이어 상태로 안전하게 원복되었습니다!'
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

# ==========================================
# 🎯 목표치 달성 이펙트 이벤트 제어 API
# ==========================================
@app.route('/api/goal/approve_event', methods=['POST'])
def approve_goal_event():
    try:
        with file_lock:
            state = load_data()
            state['goal_event_pending'] = False
            state['goal_event_approved'] = True
            save_data(state)
            
            # 오버레이에 목표 100% 달성 1.5초 연출 신호 즉각 브로드캐스트
            broadcast_event('goal_celebration', {
                'timestamp': time.time(),
                'target_goal': state.get('target_goal', 50000)
            })
            broadcast_event('update', state)
            
        return jsonify({"status": "success", "message": "목표 달성 위젯 이벤트를 방송 화면에 성공적으로 송출했습니다!"})
    except Exception as e:
        print(f"Error approving goal event: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/goal/dismiss_event', methods=['POST'])
def dismiss_goal_event():
    try:
        with file_lock:
            state = load_data()
            state['goal_event_pending'] = False
            state['goal_event_approved'] = True # 동일 목표치 도배 방지
            save_data(state)
            broadcast_event('update', state)
            
        return jsonify({"status": "success", "message": "목표 달성 알림을 닫았습니다."})
    except Exception as e:
        print(f"Error dismissing goal event: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

# ==========================================
# 🎛️ 스트림덱 전용 원터치 제어 API (GET 방식)
# ==========================================
@app.route('/api/streamdeck/save', methods=['GET'])
def sd_save():
    try:
        create_snapshot_record("스트림덱 수동 백업")
        print("  💾 [스트림덱 명령] 수동 스냅샷 세이브포인트 저장 완료!")
        return jsonify({"status": "success", "message": "스냅샷 저장 완료"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/streamdeck/neon', methods=['GET'])
def sd_neon():
    try:
        color = request.args.get('color', 'RAINBOW').upper()
        # 6자리 16진수 색상 코드인 경우 #을 자동으로 붙여줌
        if len(color) == 6 and all(c in '0123456789ABCDEF' for c in color):
            color = '#' + color
            
        with file_lock:
            state = load_data()
            state['effect_trigger'] = {
                'time': int(time.time() * 1000),
                'color': color
            }
            if color != 'OFF':
                state['reaction_mode'] = True
            else:
                state['reaction_mode'] = False
                
            save_data(state)
            broadcast_event('update', state)
        print(f"  💡 [스트림덱 명령] 네온 이펙트 조명 전환: {color}")
        return jsonify({"status": "success", "color": color})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# ==========================================
# 🎵 커스텀 리액션 플랫폼 API (영구 보존형)
# ==========================================
import uuid

@app.route('/api/reaction/file/<path:file_id>', methods=['GET'])
def get_reaction_file(file_id):
    try:
        cache_dir = os.path.join(app.root_path, 'media_cache')
        os.makedirs(cache_dir, exist_ok=True)
        target = str(file_id)

        import mimetypes

        def _guess_mime(fname):
            mime, _ = mimetypes.guess_type(fname)
            if not mime:
                low = fname.lower()
                if low.endswith('.png'): mime = 'image/png'
                elif low.endswith(('.jpg', '.jpeg')): mime = 'image/jpeg'
                elif low.endswith('.gif'): mime = 'image/gif'
                elif low.endswith('.webp'): mime = 'image/webp'
                elif low.endswith('.mp3'): mime = 'audio/mpeg'
                elif low.endswith('.mp4'): mime = 'video/mp4'
                elif low.endswith('.wav'): mime = 'audio/wav'
                else: mime = 'application/octet-stream'
            return mime

        def _serve_file(fpath, content_type=None):
            mime = content_type or _guess_mime(fpath)
            response = send_file(fpath, mimetype=mime, as_attachment=False, conditional=True)
            response.headers.set('Access-Control-Allow-Origin', '*')
            return response

        # 0. DB에서 이 file_id(또는 filename)에 해당하는 실제 id, filename, content_type 조회
        db_id = None
        db_filename = None
        db_content_type = None
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(db_query("SELECT id, filename, content_type FROM reaction_files WHERE id = ? OR filename = ?"), (target, target))
                row = cursor.fetchone()
                if row:
                    db_id = row[0]
                    db_filename = row[1]
                    db_content_type = row[2]
        except Exception as db_err:
            print(f"DB lookup error for reaction file {file_id}: {db_err}")

        # 1. media_cache 폴더 안에서 실물 파일 탐색 (직접 경로 조합으로 빠르게 우선 시도)
        candidates = []
        for cand in (target, db_filename):
            if cand and cand not in candidates:
                candidates.append(cand)
        if db_id and db_filename:
            combo = f"{db_id}_{db_filename}"
            if combo not in candidates:
                candidates.append(combo)
        if db_id and db_id not in candidates:
            candidates.append(db_id)

        best_match = None

        # 1-1. 직접 경로 존재 여부로 빠르게 확인 (listdir 없이)
        for cand in candidates:
            direct_path = os.path.join(cache_dir, cand)
            if os.path.isfile(direct_path) and os.path.getsize(direct_path) > 0:
                best_match = cand
                break

        # 1-2. 직접 매칭 실패 시에만 폴더 전체 스캔 (느리지만 최후 수단)
        if not best_match:
            try:
                all_files = os.listdir(cache_dir)
            except Exception:
                all_files = []

            for fname in all_files:
                fpath = os.path.join(cache_dir, fname)
                if not (os.path.isfile(fpath) and os.path.getsize(fpath) > 0):
                    continue

                matched = False
                for cand in candidates:
                    if not cand:
                        continue
                    if (fname == cand
                            or fname.startswith(f"{cand}_")
                            or fname.endswith(f"_{cand}")
                            or os.path.splitext(fname)[0] == cand):
                        matched = True
                        break
                if matched:
                    best_match = fname
                    break

        if best_match:
            fpath = os.path.join(cache_dir, best_match)
            return _serve_file(fpath, db_content_type)

        # 2. media_cache에 실물이 전혀 없을 경우 DB의 file_data(BLOB)로 최후 서빙 + 디스크 캐싱
        if db_id:
            try:
                with get_db_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(db_query("SELECT filename, content_type, file_data FROM reaction_files WHERE id = ?"), (db_id,))
                    row = cursor.fetchone()
                    if row and row[2] is not None:
                        fname = row[0] or db_id
                        content_type = row[1]
                        raw_data = row[2]
                        if isinstance(raw_data, memoryview):
                            raw_data = raw_data.tobytes()
                        elif not isinstance(raw_data, (bytes, bytearray)):
                            raw_data = bytes(raw_data)

                        cache_fname = f"{db_id}_{fname}"
                        cache_fpath = os.path.join(cache_dir, cache_fname)
                        try:
                            with open(cache_fpath, 'wb') as f:
                                f.write(raw_data)
                        except Exception as write_err:
                            print(f"Failed to write disk cache for {cache_fname}: {write_err}")

                        import io as _io
                        response = send_file(_io.BytesIO(raw_data), mimetype=content_type or _guess_mime(fname), as_attachment=False, conditional=False, download_name=fname)
                        response.headers.set('Access-Control-Allow-Origin', '*')
                        return response
            except Exception as blob_err:
                print(f"Error serving reaction file from DB blob {file_id}: {blob_err}")

        return jsonify({"status": "error", "message": "File not found"}), 404
    except Exception as e:
        print(f"Error serving reaction file {file_id}: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/reaction/list', methods=['GET'])
def get_reactions_list():
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            query = """
                SELECT 
                    i.id, 
                    i.title, 
                    i.amount, 
                    i.audio_file_id, 
                    i.image_file_id, 
                    i.is_enabled,
                    fa.filename as audio_filename,
                    fi.filename as image_filename
                FROM reaction_items i
                LEFT JOIN reaction_files fa ON i.audio_file_id = fa.id
                LEFT JOIN reaction_files fi ON i.image_file_id = fi.id
                ORDER BY i.amount ASC, i.id ASC
            """
            cursor.execute(db_query(query))
            rows = cursor.fetchall()
            reactions = []
            for r in rows:
                audio_id = r[3]
                image_id = r[4]
                audio_fname = r[6]
                image_fname = r[7]
                
                img_url = f"/api/reaction/file/{image_fname or image_id}" if (image_fname or image_id) else ""
                aud_url = f"/api/reaction/file/{audio_fname or audio_id}" if (audio_fname or audio_id) else ""

                reactions.append({
                    "id": r[0],
                    "title": str(r[1]) if r[1] else (f"리액션 ({r[2]:,}원)" if r[2] else "리액션"),
                    "amount": r[2] or 0,
                    "audio_url": aud_url,
                    "image_url": img_url,
                    "audio_file_id": audio_id,
                    "image_file_id": image_id,
                    "is_enabled": bool(r[5]) if r[5] is not None else True
                })
            return jsonify(reactions)
    except Exception as e:
        print(f"Error listing reactions: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

def optimize_uploaded_image(file_stream, filename):
    try:
        from PIL import Image
        import io
        
        file_stream.seek(0)
        img = Image.open(file_stream)
        
        if img.mode in ('RGBA', 'LA', 'P'):
            pass
        else:
            img = img.convert('RGB')
            
        MAX_DIM = 400
        w, h = img.size
        if max(w, h) > MAX_DIM:
            if w > h:
                new_w = MAX_DIM
                new_h = int(h * (MAX_DIM / w))
            else:
                new_h = MAX_DIM
                new_w = int(w * (MAX_DIM / h))
            img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
            
        out_buf = io.BytesIO()
        img.save(out_buf, format='WEBP', quality=65)
        webp_data = out_buf.getvalue()
        
        base_name = os.path.splitext(filename)[0]
        webp_filename = f"{base_name}.webp"
        
        return webp_data, webp_filename, 'image/webp'
    except Exception as e:
        print(f"Error optimizing image in server: {e}")
        file_stream.seek(0)
        return file_stream.read(), filename, None

@app.route('/api/reaction/add', methods=['POST'])
def add_reaction():
    try:
        title = request.form.get('title', '').strip()
        amount = int(request.form.get('amount', 0))
        
        if not title:
            return jsonify({"status": "error", "message": "제목을 입력해주세요."}), 400
            
        audio_file = request.files.get('audio')
        image_file = request.files.get('image')
        
        audio_file_id = None
        image_file_id = None
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            if audio_file and audio_file.filename:
                audio_file_id = f"aud_{uuid.uuid4().hex}"
                audio_data = audio_file.read()
                cursor.execute(
                    db_query("INSERT INTO reaction_files (id, filename, content_type, file_data) VALUES (?, ?, ?, ?)"),
                    (audio_file_id, audio_file.filename, audio_file.content_type, _pg_binary(audio_data))
                )
                
            if image_file and image_file.filename:
                image_file_id = f"img_{uuid.uuid4().hex}"
                image_data, opt_filename, opt_content_type = optimize_uploaded_image(image_file, image_file.filename)
                content_type = opt_content_type or image_file.content_type
                filename = opt_filename or image_file.filename
                cursor.execute(
                    db_query("INSERT INTO reaction_files (id, filename, content_type, file_data) VALUES (?, ?, ?, ?)"),
                    (image_file_id, filename, content_type, _pg_binary(image_data))
                )
                
            cursor.execute(
                db_query("INSERT INTO reaction_items (title, amount, audio_file_id, image_file_id) VALUES (?, ?, ?, ?)"),
                (title, amount, audio_file_id, image_file_id)
            )
            conn.commit()
            
        return jsonify({"status": "success", "message": "리액션 곡 등록 완료!"})
    except Exception as e:
        print(f"Error adding reaction: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/reaction/delete/<int:item_id>', methods=['POST', 'DELETE'])
def delete_reaction(item_id):
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(db_query("SELECT audio_file_id, image_file_id FROM reaction_items WHERE id = ?"), (item_id,))
            row = cursor.fetchone()
            if not row:
                return jsonify({"status": "error", "message": "Reaction item not found"}), 404
                
            audio_file_id, image_file_id = row
            
            cursor.execute(db_query("DELETE FROM reaction_items WHERE id = ?"), (item_id,))
            
            if audio_file_id:
                cursor.execute(db_query("DELETE FROM reaction_files WHERE id = ?"), (audio_file_id,))
            if image_file_id:
                cursor.execute(db_query("DELETE FROM reaction_files WHERE id = ?"), (image_file_id,))
                
            conn.commit()
            
        return jsonify({"status": "success", "message": "리액션 곡 삭제 완료!"})
    except Exception as e:
        print(f"Error deleting reaction: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/reaction/edit/<int:item_id>', methods=['POST'])
def edit_reaction(item_id):
    try:
        title = request.form.get('title', '').strip()
        amount = int(request.form.get('amount', 0))
        
        if not title:
            return jsonify({"status": "error", "message": "제목을 입력해주세요."}), 400
            
        audio_file = request.files.get('audio')
        image_file = request.files.get('image')
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute(db_query("SELECT audio_file_id, image_file_id FROM reaction_items WHERE id = ?"), (item_id,))
            row = cursor.fetchone()
            if not row:
                return jsonify({"status": "error", "message": "Reaction item not found"}), 404
                
            old_audio_id, old_image_id = row
            audio_file_id = old_audio_id
            image_file_id = old_image_id
            
            if audio_file and audio_file.filename:
                audio_file_id = f"aud_{uuid.uuid4().hex}"
                audio_data = audio_file.read()
                cursor.execute(
                    db_query("INSERT INTO reaction_files (id, filename, content_type, file_data) VALUES (?, ?, ?, ?)"),
                    (audio_file_id, audio_file.filename, audio_file.content_type, _pg_binary(audio_data))
                )
                if old_audio_id:
                    cursor.execute(db_query("DELETE FROM reaction_files WHERE id = ?"), (old_audio_id,))
                
            if image_file and image_file.filename:
                image_file_id = f"img_{uuid.uuid4().hex}"
                image_data, opt_filename, opt_content_type = optimize_uploaded_image(image_file, image_file.filename)
                content_type = opt_content_type or image_file.content_type
                filename = opt_filename or image_file.filename
                cursor.execute(
                    db_query("INSERT INTO reaction_files (id, filename, content_type, file_data) VALUES (?, ?, ?, ?)"),
                    (image_file_id, filename, content_type, _pg_binary(image_data))
                )
                if old_image_id:
                    cursor.execute(db_query("DELETE FROM reaction_files WHERE id = ?"), (old_image_id,))
                    
            cursor.execute(
                db_query("UPDATE reaction_items SET title = ?, amount = ?, audio_file_id = ?, image_file_id = ? WHERE id = ?"),
                (title, amount, audio_file_id, image_file_id, item_id)
            )
            conn.commit()
            
        return jsonify({"status": "success", "message": "리액션 곡 수정 완료!"})
    except Exception as e:
        print(f"Error editing reaction: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/reaction/toggle/<int:item_id>', methods=['POST'])
def toggle_reaction(item_id):
    try:
        data = request.json or {}
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(db_query("SELECT is_enabled FROM reaction_items WHERE id = ?"), (item_id,))
            row = cursor.fetchone()
            if not row:
                return jsonify({"status": "error", "message": "Reaction item not found"}), 404
                
            if 'is_enabled' in data:
                new_state = bool(data['is_enabled'])
            else:
                new_state = not (bool(row[0]) if row[0] is not None else True)
                
            cursor.execute(db_query("UPDATE reaction_items SET is_enabled = ? WHERE id = ?"), (new_state, item_id))
            conn.commit()
            
        return jsonify({"status": "success", "is_enabled": new_state, "message": "리액션 활성화 상태 변경 완료!"})
    except Exception as e:
        print(f"Error toggling reaction: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/reaction/delete_batch', methods=['POST'])
def delete_reactions_batch():
    try:
        data = request.json or {}
        item_ids = data.get('item_ids', [])
        if not item_ids:
            return jsonify({"status": "error", "message": "삭제할 리액션이 선택되지 않았습니다."}), 400
            
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            placeholders = ",".join(["?"] * len(item_ids))
            query = f"SELECT audio_file_id, image_file_id FROM reaction_items WHERE id IN ({placeholders})"
            cursor.execute(db_query(query), tuple(item_ids))
            rows = cursor.fetchall()
            
            file_ids_to_delete = []
            for r in rows:
                if r[0]: file_ids_to_delete.append(r[0])
                if r[1]: file_ids_to_delete.append(r[1])
                
            del_query = f"DELETE FROM reaction_items WHERE id IN ({placeholders})"
            cursor.execute(db_query(del_query), tuple(item_ids))
            
            if file_ids_to_delete:
                cursor.execute(db_query("SELECT audio_file_id, image_file_id FROM reaction_items"))
                remaining = set()
                for rem in cursor.fetchall():
                    if rem[0]: remaining.add(rem[0])
                    if rem[1]: remaining.add(rem[1])
                    
                orphaned = [fid for fid in file_ids_to_delete if fid not in remaining]
                if orphaned:
                    file_placeholders = ",".join(["?"] * len(orphaned))
                    file_del_query = f"DELETE FROM reaction_files WHERE id IN ({file_placeholders})"
                    cursor.execute(db_query(file_del_query), tuple(orphaned))
                    
            conn.commit()
            
        return jsonify({"status": "success", "message": f"{len(item_ids)}개의 리액션 삭제 완료!"})
    except Exception as e:
        print(f"Error batch deleting reactions: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/reaction/play/<int:item_id>', methods=['POST'])
def play_reaction(item_id):
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            query = """
                SELECT 
                    i.title, 
                    i.amount,
                    fa.filename as audio_filename,
                    fi.filename as image_filename
                FROM reaction_items i
                LEFT JOIN reaction_files fa ON i.audio_file_id = fa.id
                LEFT JOIN reaction_files fi ON i.image_file_id = fi.id
                WHERE i.id = ?
            """
            cursor.execute(db_query(query), (item_id,))
            row = cursor.fetchone()
            if not row:
                return jsonify({"status": "error", "message": "Reaction item not found"}), 404
                
            title, r_amount, audio_fname, image_fname = row
            
            final_audio_fname = audio_fname
            final_image_fname = image_fname

            # media_cache/ 내의 실물 파일명 직접 찾기 fallback
            if os.path.exists(MEDIA_CACHE_DIR):
                for f in os.listdir(MEDIA_CACHE_DIR):
                    f_ext = os.path.splitext(f)[1].lower()
                    if f.startswith(f"{title}_{r_amount}") or f.startswith(f"{r_amount}_{r_amount}"):
                        if f_ext in ('.mp3', '.wav', '.mp4', '.m4a') and not final_audio_fname:
                            final_audio_fname = f
                        elif f_ext in ('.png', '.jpg', '.jpeg', '.webp', '.gif') and not final_image_fname:
                            final_image_fname = f

            audio_url = f"/api/reaction/file/{final_audio_fname}" if final_audio_fname else ""
            image_url = f"/api/reaction/file/{final_image_fname}" if final_image_fname else ""
            
            with file_lock:
                state = load_data()
                reaction_uuid = f"rq_{uuid.uuid4().hex}"
                state['reaction_queue'].append({
                    "id": reaction_uuid,
                    "item_id": item_id,
                    "title": title or "리액션",
                    "audio_url": audio_url,
                    "image_url": image_url,
                    "donator": "수동송출",
                    "message": ""
                })
                state['reaction_mode'] = True

                # 🎴 [카드 뒤집기 게임] 뒤집혀 있고 통과 안 된 카드와 매칭 시 자동 PASS 처리
                cg = state.get('card_game', {})
                if cg.get('active') and cg.get('cards'):
                    for card in cg['cards']:
                        if card.get('is_flipped') and not card.get('is_passed'):
                            if (item_id and card.get('reaction_id') == item_id) or (title and card.get('title') == title):
                                card['is_passed'] = True
                                print(f"  🎴 [카드 뒤집기 PASS!] {card.get('title')} 리액션 미션 통과 완료!")
                                break
                save_data(state)
                broadcast_event('update', state)
                
        return jsonify({"status": "success", "message": "방송 송출 완료!"})
    except Exception as e:
        print(f"Error playing reaction: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/reaction/next', methods=['POST'])
def next_reaction():
    try:
        data = request.get_json(silent=True) or {}
        pop_id = data.get('id')
        
        with file_lock:
            state = load_data()
            queue = state.get('reaction_queue', [])
            
            if queue:
                # ID가 지정된 경우: 첫 번째 아이템의 ID가 일치할 때만 pop (이중 pop 방지)
                # ID가 없는 경우: 기존 방식대로 무조건 pop (하위 호환)
                if not pop_id or queue[0].get('id') == pop_id:
                    queue.pop(0)
                
            if not queue:
                state['reaction_mode'] = False
                
            save_data(state)
            broadcast_event('update', state)
            broadcast_event('reaction_skip', {})
        return jsonify({"status": "success", "message": "Popped reaction"})
    except Exception as e:
        print(f"Error in next_reaction: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/reaction/stop', methods=['POST'])
def stop_reaction():
    try:
        with file_lock:
            state = load_data()
            state['reaction_queue'] = []
            state['reaction_mode'] = False
            save_data(state)
            broadcast_event('update', state)
            broadcast_event('reaction_stop', {})
        return jsonify({"status": "success", "message": "All reactions stopped"})
    except Exception as e:
        print(f"Error in stop_reaction: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/slot/spin/<string:spin_id>', methods=['POST'])
def spin_slot_machine(spin_id):
    """운영자가 컨트롤러의 '슬롯' 탭에서 직접 '돌리기' 버튼을 눌렀을 때 호출.
    실제 당첨 리액션을 뽑아 오버레이 슬롯 애니메이션을 재생시키고,
    점수/기여도는 즉시 반영하지 않고 '후원 결재 대기함'에 슬롯 결과 카드로 추가하여
    운영자가 승인해야 최종 반영되도록 처리합니다."""
    try:
        with file_lock:
            state = load_data()
            pending_spins = state.get('pending_slot_spins', [])
            spin_idx = next((i for i, s in enumerate(pending_spins) if s.get('id') == spin_id), -1)
            if spin_idx == -1:
                return jsonify({"status": "error", "message": "대기 중인 슬롯 스핀을 찾을 수 없습니다."}), 404

            spin_entry = pending_spins.pop(spin_idx)
            state['pending_slot_spins'] = pending_spins

            slot = normalize_slot_machine_state(state)
            candidate = get_slot_reaction_candidate(slot.get('selected_reaction_ids') or [])
            if not candidate:
                # 후보가 없으면 대기열에서 제거만 하고 실패 응답
                save_data(state)
                broadcast_event('update', state)
                return jsonify({"status": "error", "message": "선택된 슬롯 후보 리액션이 없습니다."}), 400

            result_amount = int(candidate.get('amount') or 0)
            score_delta = 2
            contribution_delta = max(0, int(result_amount / 10000 + 0.5))

            aud_target = candidate.get('audio_file_id')
            img_target = candidate.get('image_file_id')
            audio_url = f"/api/reaction/file/{aud_target}" if aud_target else ""
            image_url = f"/api/reaction/file/{img_target}" if img_target else ""

            parsed_name = spin_entry.get('name')
            if not parsed_name or parsed_name.strip() == '' or parsed_name.strip() == '익명':
                parsed_name = '슬롯머신'

            amount = spin_entry.get('amount', 0)
            cleaned_msg = spin_entry.get('message', '')
            don_id = spin_entry.get('don_id')

            # 💡 오버레이 슬롯 애니메이션 + 리액션 재생을 위해 reaction_queue에 추가
            reaction_uuid = f"rq_{uuid.uuid4().hex}"
            state['reaction_queue'].append({
                "id": reaction_uuid,
                "item_id": candidate['id'],
                "title": candidate['title'],
                "audio_url": audio_url,
                "image_url": image_url,
                "amount": amount,
                "donator": parsed_name,
                "message": cleaned_msg,
                "slot_machine": True,
                "slot_result_amount": result_amount,
                "slot_score_delta": score_delta,
                "slot_contribution_delta": contribution_delta
            })
            state['reaction_mode'] = True

            # 💡 승인 대기함(pending_donations)에 슬롯 결과 카드로 추가 (승인 눌러야 실제 반영)
            slot_result = {
                "item_id": candidate['id'],
                "title": candidate['title'],
                "result_amount": result_amount,
                "score_delta": score_delta,
                "contribution_delta": contribution_delta,
                "audio_url": audio_url,
                "image_url": image_url
            }
            if 'pending_donations' not in state or not isinstance(state.get('pending_donations'), list):
                state['pending_donations'] = []
            state['pending_donations'].append({
                'id': don_id or f"don_slot_{int(time.time() * 1000)}",
                'name': parsed_name,
                'amount': amount,
                'message': cleaned_msg,
                'time': time.strftime('%H:%M:%S'),
                'slot_result': slot_result
            })

            save_data(state)
            broadcast_event('update', state)
            print(f"  🎰 [슬롯머신 회전 확정] {parsed_name} -> '{candidate['title']}' / 점수 +{score_delta}, 기여도 +{contribution_delta} (승인 대기)")

        return jsonify({"status": "success", "message": "슬롯머신을 돌렸습니다! 승인 대기함에서 결과를 확인해주세요."})
    except Exception as e:
        print(f"Error spinning slot machine: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/slot/spin_now', methods=['POST'])
def spin_slot_machine_now():
    """운영자가 후원과 무관하게 '지금 바로 돌리기' 버튼을 눌렀을 때 호출됩니다.
    후보로 선택된 리액션 중 하나를 랜덤으로 뽑아 오버레이 슬롯 애니메이션을 재생시키고,
    점수는 +2점 고정, 기여도는 당첨 리액션 금액에 비례하여 승인 대기함에 이름 없이 등록합니다."""
    try:
        with file_lock:
            state = load_data()
            slot = normalize_slot_machine_state(state)
            candidate = get_slot_reaction_candidate(slot.get('selected_reaction_ids') or [])
            if not candidate:
                return jsonify({"status": "error", "message": "선택된 슬롯 후보 리액션이 없습니다. 리액션 탭에서 🎰 슬롯 후보를 먼저 선택해주세요."}), 400

            result_amount = int(candidate.get('amount') or 0)
            score_delta = 2
            contribution_delta = max(0, int(result_amount / 10000 + 0.5))

            aud_target = candidate.get('audio_file_id')
            img_target = candidate.get('image_file_id')
            audio_url = f"/api/reaction/file/{aud_target}" if aud_target else ""
            image_url = f"/api/reaction/file/{img_target}" if img_target else ""

            # 💡 오버레이 슬롯 애니메이션 + 리액션 재생을 위해 reaction_queue에 추가 (후원자 이름 없음)
            reaction_uuid = f"rq_{uuid.uuid4().hex}"
            state['reaction_queue'].append({
                "id": reaction_uuid,
                "item_id": candidate['id'],
                "title": candidate['title'],
                "audio_url": audio_url,
                "image_url": image_url,
                "amount": 0,
                "donator": "",
                "message": "",
                "slot_machine": True,
                "skip_donation_popup": True,
                "slot_result_amount": result_amount,
                "slot_score_delta": score_delta,
                "slot_contribution_delta": contribution_delta
            })
            state['reaction_mode'] = True

            # 💡 승인 대기함(pending_donations)에 슬롯 결과 카드로 이름 없이 추가 (승인 눌러야 실제 반영)
            slot_result = {
                "item_id": candidate['id'],
                "title": candidate['title'],
                "result_amount": result_amount,
                "score_delta": score_delta,
                "contribution_delta": contribution_delta,
                "audio_url": audio_url,
                "image_url": image_url
            }
            if 'pending_donations' not in state or not isinstance(state.get('pending_donations'), list):
                state['pending_donations'] = []
            state['pending_donations'].append({
                'id': f"don_slot_{int(time.time() * 1000)}",
                'name': '슬롯머신',
                'amount': 0,
                'message': '',
                'time': time.strftime('%H:%M:%S'),
                'slot_result': slot_result
            })

            save_data(state)
            broadcast_event('update', state)
            print(f"  🎰 [슬롯머신 즉시 회전] '{candidate['title']}' 당첨 / 점수 +{score_delta}, 기여도 +{contribution_delta} (승인 대기)")

        return jsonify({"status": "success", "message": "슬롯머신을 돌렸습니다! 승인 대기함에서 결과를 확인해주세요."})
    except Exception as e:
        print(f"Error spinning slot machine now: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/slot/spin/<string:spin_id>/cancel', methods=['POST'])
def cancel_slot_spin(spin_id):
    """대기 중인 슬롯 스핀을 취소(무시)합니다."""
    try:
        with file_lock:
            state = load_data()
            pending_spins = state.get('pending_slot_spins', [])
            state['pending_slot_spins'] = [s for s in pending_spins if s.get('id') != spin_id]
            save_data(state)
            broadcast_event('update', state)
        return jsonify({"status": "success", "message": "슬롯 스핀 대기가 취소되었습니다."})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/vips', methods=['GET'])
def get_vips():
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            if IS_POSTGRES:
                cursor.execute("SELECT name, grade, custom_color, badge FROM vip_donators ORDER BY name ASC")
            else:
                cursor.execute("SELECT name, grade, custom_color, badge FROM vip_donators ORDER BY name ASC")
            vips = []
            for row in cursor.fetchall():
                vips.append({
                    "name": row[0],
                    "grade": row[1],
                    "custom_color": row[2],
                    "badge": row[3]
                })
            return jsonify({"status": "success", "vips": vips})
    except Exception as e:
        print(f"Error in get_vips: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/vips', methods=['POST'])
def add_or_update_vip():
    try:
        data = request.get_json(silent=True) or {}
        name = data.get('name')
        grade = data.get('grade')
        custom_color = data.get('custom_color', '#ffd700')
        badge = data.get('badge', '👑')
        
        if not name or not grade:
            return jsonify({"status": "error", "message": "닉네임과 등급은 필수 항목입니다."}), 400
            
        with get_db_connection() as conn:
            cursor = conn.cursor()
            if IS_POSTGRES:
                cursor.execute("""
                    INSERT INTO vip_donators (name, grade, custom_color, badge)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (name) DO UPDATE 
                    SET grade = EXCLUDED.grade,
                        custom_color = EXCLUDED.custom_color,
                        badge = EXCLUDED.badge
                """, (name, grade, custom_color, badge))
            else:
                cursor.execute("""
                    INSERT OR REPLACE INTO vip_donators (name, grade, custom_color, badge)
                    VALUES (?, ?, ?, ?)
                """, (name, grade, custom_color, badge))
            conn.commit()
        
        with file_lock:
            state = load_data()
            broadcast_event('update', state)
            broadcast_event('vips_updated', {})
            
        return jsonify({"status": "success", "message": "VIP 정보가 성공적으로 저장되었습니다."})
    except Exception as e:
        print(f"Error in add_or_update_vip: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/vips', methods=['DELETE'])
def delete_vip():
    try:
        name = request.args.get('name')
        if not name:
            return jsonify({"status": "error", "message": "닉네임이 누락되었습니다."}), 400
            
        with get_db_connection() as conn:
            cursor = conn.cursor()
            if IS_POSTGRES:
                cursor.execute("DELETE FROM vip_donators WHERE name = %s", (name,))
            else:
                cursor.execute("DELETE FROM vip_donators WHERE name = ?", (name,))
            conn.commit()
            
        with file_lock:
            state = load_data()
            broadcast_event('update', state)
            broadcast_event('vips_updated', {})
            
        return jsonify({"status": "success", "message": "VIP 해제 완료!"})
    except Exception as e:
        print(f"Error in delete_vip: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/reaction/queue/remove/<string:rq_id>', methods=['POST'])
def remove_from_queue(rq_id):
    try:
        with file_lock:
            state = load_data()
            queue = state.get('reaction_queue', [])
            if queue:
                is_currently_playing = (queue[0]['id'] == rq_id)
                state['reaction_queue'] = [item for item in queue if item['id'] != rq_id]
                
                if is_currently_playing:
                    broadcast_event('reaction_stop', {'id': rq_id})
                    
                if not state['reaction_queue']:
                    state['reaction_mode'] = False
                    
                save_data(state)
                broadcast_event('update', state)
        return jsonify({"status": "success", "message": "Removed from queue"})
    except Exception as e:
        print(f"Error in remove_from_queue: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

# ==========================================
# 🖥️ GUI 관리자 창 (로그인 없이 바로 표시)
# ==========================================
def start_self_ping():
    import urllib.request
    import threading
    import time
    
    if IS_VERCEL:
        return  # Vercel 서버리스: self-ping 불필요
    url = os.environ.get('RENDER_EXTERNAL_URL')
    if not url:
        return
        
    def ping_loop():
        # 즉시 초기화 로그 출력
        print(f"⏰ [Self-Ping] Daemon initialized for: {url}", flush=True)
        # 서버 시작 후 첫 30초 대기
        time.sleep(30)
        print(f"⏰ [Self-Ping] Starting self-ping loop...", flush=True)
        while True:
            try:
                req = urllib.request.Request(
                    url,
                    headers={'User-Agent': 'LiveMaster-KeepAwake/1.0'}
                )
                with urllib.request.urlopen(req, timeout=15) as response:
                    print(f"⏰ [Self-Ping] Ping sent successfully, response code: {response.getcode()}", flush=True)
            except Exception as e:
                print(f"⚠️ [Self-Ping] Ping failed: {e}", flush=True)
            time.sleep(600)  # 10분마다 실행 (Render 무료 비활성화 임계치인 15분보다 짧음)
            
    ping_thread = threading.Thread(target=ping_loop, daemon=True)
    ping_thread.start()

def run_flask():
    port = int(os.environ.get('PORT', 5000))
    start_self_ping()
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

def has_gui_support():
    if os.environ.get('HEADLESS'):
        return False
    if tk is None:
        return False
    try:
        temp_root = tk.Tk()
        temp_root.destroy()
        return True
    except Exception:
        return False

def open_link(url):
    webbrowser.open(url)

def on_closing(root):
    if messagebox.askokcancel('서버 종료', '방송 서버를 완전히 종료하시겠습니까?\n(정산 기능 및 오버레이 송출이 중단됩니다)'):
        root.destroy()
        sys.exit(0)

@app.route('/api/offwork/broadcast', methods=['POST'])
def broadcast_offwork():
    try:
        data = request.get_json(silent=True) or {}
        name = data.get('name', '선수')
        broadcast_event('off_work_event', {'name': name})
        return jsonify({"status": "success", "message": f"{name} 퇴근 이벤트 송출 완료"})
    except Exception as e:
        print(f"Error broadcasting offwork event: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

# ==========================================
# 🎴 카드 뒤집기 (Card Flip Game) API 라우트
# ==========================================

def build_card_deck_from_db(selected_ids=None):
    import random
    with get_db_connection() as conn:
        cursor = conn.cursor()
        query = """
            SELECT 
                i.id, i.title, i.amount, 
                fa.filename as audio_fname, 
                fi.filename as image_fname
            FROM reaction_items i
            LEFT JOIN reaction_files fa ON i.audio_file_id = fa.id
            LEFT JOIN reaction_files fi ON i.image_file_id = fi.id
            WHERE i.is_enabled = TRUE
        """
        cursor.execute(db_query(query))
        all_reactions = cursor.fetchall()
        
    if not all_reactions:
        return []
        
    items_map = {r[0]: r for r in all_reactions}
    chosen = []
    
    if selected_ids and isinstance(selected_ids, list) and len(selected_ids) > 0:
        for sid in selected_ids:
            if sid in items_map:
                chosen.append(items_map[sid])
                
    if len(chosen) < 20:
        remaining = [r for r in all_reactions if r not in chosen]
        random.shuffle(remaining)
        needed = 20 - len(chosen)
        chosen.extend(remaining[:needed])
        
    random.shuffle(chosen)
    chosen = chosen[:20]
    
    cards = []
    for idx, r in enumerate(chosen):
        r_id, title, amount, aud_fname, img_fname = r
        img_url = f"/api/reaction/file/{img_fname}" if img_fname else ""
        aud_url = f"/api/reaction/file/{aud_fname}" if aud_fname else ""
        cards.append({
            "id": idx,
            "reaction_id": r_id,
            "title": title,
            "amount": amount,
            "image_url": img_url,
            "audio_url": aud_url,
            "step": 0,
            "is_flipped": False,
            "is_passed": False
        })
    return cards

@app.route('/api/card_game/toggle', methods=['POST'])
def toggle_card_game():
    try:
        data = request.get_json(silent=True) or {}
        with file_lock:
            state = load_data()
            if 'card_game' not in state:
                state['card_game'] = {"active": False, "is_running": False, "time_left_ms": 300000, "selected_reaction_ids": [], "cards": []}
            
            new_active = data.get('active')
            if new_active is None:
                new_active = not state['card_game'].get('active', False)
            state['card_game']['active'] = bool(new_active)
            
            # 💡 [변경] 위젯을 켤 때 카드가 없어도 더 이상 자동으로 무작위 채우지 않음.
            # 운영자가 "20장 직접 선택 피커" 또는 "무작위로 20장 채우기"를 명시적으로 눌러야 카드가 생성됩니다.
                
            state['version'] = state.get('version', 0) + 1
            save_data(state)
            broadcast_event('update', state)
        return jsonify({"status": "success", "active": state['card_game']['active'], "card_game": state['card_game']})
    except Exception as e:
        print(f"Error toggling card game: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/card_game/shuffle', methods=['POST'])
def shuffle_card_game():
    try:
        data = request.get_json(silent=True) or {}
        selected_ids = data.get('selected_ids')
        with file_lock:
            state = load_data()
            if 'card_game' not in state:
                state['card_game'] = {"active": True, "is_running": False, "time_left_ms": 300000, "selected_reaction_ids": [], "cards": [], "finalized": False, "final_card_ids": [], "final_reaction_ids": []}
            
            if selected_ids is not None:
                state['card_game']['selected_reaction_ids'] = selected_ids
                
            state['card_game']['cards'] = build_card_deck_from_db(state['card_game'].get('selected_reaction_ids'))
            state['card_game']['finalized'] = False
            state['card_game']['final_card_ids'] = []
            state['card_game']['final_reaction_ids'] = []
            state['version'] = state.get('version', 0) + 1
            save_data(state)
            broadcast_event('update', state)
        return jsonify({"status": "success", "cards": state['card_game']['cards']})
    except Exception as e:
        print(f"Error shuffling card game: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/card_game/shuffle_order', methods=['POST'])
def shuffle_card_game_order():
    """💡 [신규] 기존 20장 리액션 구성은 그대로 유지하고, 카드 배열 순서(위치)만 무작위로 섞습니다.
    모든 카드의 상태(뒤집힘/PASS)는 초기화됩니다. 오버레이에서는 reaction_id를 key로 하는
    카드 DOM을 그대로 재사용하면서 위치만 이동하는 FLIP 애니메이션으로 자연스럽게 표현됩니다."""
    try:
        import random
        with file_lock:
            state = load_data()
            cg = state.get('card_game', {})
            cards = cg.get('cards', [])
            if not cards:
                return jsonify({"status": "error", "message": "섞을 카드가 없습니다. 먼저 카드를 채워주세요."}), 400

            random.shuffle(cards)
            # id를 순서대로 재부여하고 상태 초기화
            cg['cards'] = cards
            cg['finalized'] = False
            cg['final_card_ids'] = []
            cg['final_reaction_ids'] = []
            state['card_game'] = cg
            state['version'] = state.get('version', 0) + 1
            save_data(state)
            broadcast_event('update', state)
        return jsonify({"status": "success", "cards": cards, "card_game": state['card_game']})
    except Exception as e:
        print(f"Error shuffling card game order: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/card_game/finalize', methods=['POST'])
def finalize_card_game():
    """💡 [신규] 현재 앞면이거나 CLEAR(step>=1)된 카드들만 최종 선택하여 finalized 모드로 전환합니다.
    오버레이에서는 20장 그리드 대신 선택된 카드만 작게 표시되고, 원래 점수판이 다시 나타납니다."""
    try:
        with file_lock:
            state = load_data()
            cg = state.get('card_game', {})
            cards = cg.get('cards', [])
            
            passed_cards = [c for c in cards if c.get('step', 0) >= 1 or c.get('is_flipped') or c.get('is_passed')]
            if not passed_cards:
                return jsonify({"status": "error", "message": "앞면 공개 또는 CLEAR(통과)된 카드가 없습니다."}), 400

            cg['finalized'] = True
            cg['final_card_ids'] = [c.get('id') for c in passed_cards]
            cg['final_reaction_ids'] = [c.get('reaction_id') for c in passed_cards if c.get('reaction_id') is not None]
            state['card_game'] = cg
            state['version'] = state.get('version', 0) + 1
            save_data(state)
            broadcast_event('update', state)
        return jsonify({"status": "success", "card_game": state['card_game']})
    except Exception as e:
        print(f"Error finalizing card game: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/card_game/unfinalize', methods=['POST'])
def unfinalize_card_game():
    """💡 [신규] finalized 모드를 해제하고 다시 20장 전체 그리드 모드로 복귀합니다."""
    try:
        with file_lock:
            state = load_data()
            cg = state.get('card_game', {})
            cg['finalized'] = False
            cg['final_card_ids'] = []
            cg['final_reaction_ids'] = []
            state['card_game'] = cg
            state['version'] = state.get('version', 0) + 1
            save_data(state)
            broadcast_event('update', state)
        return jsonify({"status": "success", "card_game": state['card_game']})
    except Exception as e:
        print(f"Error unfinalizing card game: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/card_game/reset', methods=['POST'])
def reset_card_game():
    """💡 [신규] 카드 게임의 진행 상태(카드 뒤집힘, 타이머, 고정 모드 등)를 전부 초기화합니다."""
    try:
        with file_lock:
            state = load_data()
            cg = state.get('card_game', {})
            cards = cg.get('cards', [])
            
            # 모든 카드의 상태 초기화
            for c in cards:
                c['step'] = 0
                c['is_flipped'] = False
                c['is_passed'] = False
                
            # 타이머 초기화 (5분으로 리셋 및 일시정지)
            cg['time_left_ms'] = 300000
            cg['is_running'] = False
            
            # 고정 상태 초기화
            cg['finalized'] = False
            cg['final_card_ids'] = []
            cg['final_reaction_ids'] = []
            
            cg['cards'] = cards
            state['card_game'] = cg
            state['version'] = state.get('version', 0) + 1
            save_data(state)
            broadcast_event('update', state)
        return jsonify({"status": "success", "card_game": state['card_game']})
    except Exception as e:
        print(f"Error resetting card game: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/card_game/step', methods=['POST'])
def step_card_game():
    try:
        data = request.get_json(silent=True) or {}
        card_id = data.get('card_id')
        target_step = data.get('step')
        
        with file_lock:
            state = load_data()
            cg = state.get('card_game', {})
            cards = cg.get('cards', [])
            
            for c in cards:
                if c.get('id') == card_id:
                    if target_step is not None:
                        c['step'] = int(target_step) % 3
                    else:
                        c['step'] = (c.get('step', 0) + 1) % 3
                    
                    c['is_flipped'] = (c['step'] > 0)
                    c['is_passed'] = (c['step'] == 2)
                    break
                    
            state['version'] = state.get('version', 0) + 1
            save_data(state)
            broadcast_event('update', state)
        return jsonify({"status": "success", "cards": cards})
    except Exception as e:
        print(f"Error stepping card game: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/card_game/flip', methods=['POST'])
def flip_card_game():
    try:
        data = request.get_json(silent=True) or {}
        card_id = data.get('card_id')
        flip_count = data.get('count', 0)
        
        with file_lock:
            state = load_data()
            cg = state.get('card_game', {})
            cards = cg.get('cards', [])
            
            if card_id is not None:
                for c in cards:
                    if c.get('id') == card_id:
                        c['step'] = (c.get('step', 0) + 1) % 3
                        c['is_flipped'] = (c['step'] > 0)
                        c['is_passed'] = (c['step'] == 2)
                        break
            elif flip_count > 0:
                import random
                unflipped = [c for c in cards if c.get('step', 0) == 0]
                chosen = random.sample(unflipped, min(flip_count, len(unflipped)))
                for c in chosen:
                    c['step'] = 1
                    c['is_flipped'] = True
                    c['is_passed'] = False
                    
            state['version'] = state.get('version', 0) + 1
            save_data(state)
            broadcast_event('update', state)
        return jsonify({"status": "success", "cards": cards})
    except Exception as e:
        print(f"Error flipping card game: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/card_game/pass', methods=['POST'])
def pass_card_game():
    try:
        data = request.get_json(silent=True) or {}
        card_id = data.get('card_id')
        passed_val = data.get('passed')
        
        with file_lock:
            state = load_data()
            cg = state.get('card_game', {})
            cards = cg.get('cards', [])
            
            for c in cards:
                if c.get('id') == card_id:
                    if passed_val is None:
                        c['step'] = 2 if c.get('step') != 2 else 1
                    else:
                        c['step'] = 2 if bool(passed_val) else 1
                    c['is_flipped'] = True
                    c['is_passed'] = (c['step'] == 2)
                    break
                    
            state['version'] = state.get('version', 0) + 1
            save_data(state)
            broadcast_event('update', state)
        return jsonify({"status": "success", "cards": cards})
    except Exception as e:
        print(f"Error passing card game: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/card_game/timer', methods=['POST'])
def timer_card_game():
    try:
        data = request.get_json(silent=True) or {}
        with file_lock:
            state = load_data()
            if 'card_game' not in state:
                state['card_game'] = {"active": True, "is_running": False, "time_left_ms": 300000, "end_time_ms": 0, "selected_reaction_ids": [], "cards": []}
            cg = state['card_game']

            now_ms = int(time.time() * 1000)

            # 명시적으로 time_left_ms가 전달되면 우선 반영 (리셋/수동 설정 등)
            if 'time_left_ms' in data:
                cg['time_left_ms'] = int(data['time_left_ms'])
                # 시간이 재설정되면 현재 실행 상태 기준으로 종료 시각도 다시 계산
                if cg.get('is_running'):
                    cg['end_time_ms'] = now_ms + cg['time_left_ms']

            if 'is_running' in data:
                new_running = bool(data['is_running'])
                was_running = cg.get('is_running', False)
                if new_running and not was_running:
                    # 정지 -> 재생: 남은 시간을 기준으로 종료 시각 재계산
                    cg['end_time_ms'] = now_ms + max(0, int(cg.get('time_left_ms', 0)))
                elif (not new_running) and was_running:
                    # 재생 -> 정지: 종료 시각 기준으로 남은 시간을 고정
                    remaining = max(0, int(cg.get('end_time_ms', now_ms)) - now_ms)
                    cg['time_left_ms'] = remaining
                cg['is_running'] = new_running

            state['version'] = state.get('version', 0) + 1
            save_data(state)
            broadcast_event('update', state)
        return jsonify({"status": "success", "card_game": state['card_game']})
    except Exception as e:
        print(f"Error setting card game timer: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    init_db()
    if not has_gui_support():
        print("🖥️ [헤드리스 모드] GUI 모드를 사용할 수 없는 환경입니다. 백엔드 Flask 서버만 무중단 구동합니다.")
        run_flask()
    else:
        flask_thread = threading.Thread(target=run_flask, daemon=True)
        flask_thread.start()

        root = tk.Tk()
        root.title('💎 라이브 마스터 방송서버')
        root.configure(bg='#111113')
        root.resizable(False, False)

        try:
            root.attributes('-alpha', 0.96)
        except:
            pass

        ws = root.winfo_screenwidth()
        hs = root.winfo_screenheight()
        win_w, win_h = 400, 260
        x = (ws / 2) - (win_w / 2)
        y = (hs / 2) - (win_h / 2)
        root.geometry(f'{win_w}x{win_h}+{int(x)}+{int(y)}')

        port = int(os.environ.get('PORT', 5000))

        lbl_logo = tk.Label(root, text='💎 LIVE MASTER SERVER', fg='#00ffcc', bg='#111113', font=('Consolas', 18, 'bold'))
        lbl_logo.pack(pady=(25, 10))

        lbl_status = tk.Label(root, text=f'🟢 서버 구동 중 (Port: {port})', fg='#ffffff', bg='#111113', font=('Malgun Gothic', 12, 'bold'))
        lbl_status.pack(pady=5)

        frame_btns = tk.Frame(root, bg='#111113')
        frame_btns.pack(pady=25)

        btn_ctrl = tk.Button(frame_btns, text='💻 조종실 열기', command=lambda: open_link(f'http://localhost:{port}/controller'), fg='#000000', bg='#00ffcc', activebackground='#00cca3', font=('Malgun Gothic', 11, 'bold'), width=16, height=2, relief='flat')
        btn_ctrl.pack(side=tk.LEFT, padx=10)

        btn_ovr = tk.Button(frame_btns, text='🎬 오버레이 열기', command=lambda: open_link(f'http://localhost:{port}/overlay'), fg='#ffffff', bg='#333336', activebackground='#444448', font=('Malgun Gothic', 11, 'bold'), width=16, height=2, relief='flat')
        btn_ovr.pack(side=tk.LEFT, padx=10)

        root.protocol('WM_DELETE_WINDOW', lambda: on_closing(root))
        root.mainloop()
