import os
import sys
import sqlite3
import psycopg2

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SQLITE_DB = os.path.join(BASE_DIR, 'live_master.db')
MEDIA_CACHE_DIR = os.path.join(BASE_DIR, 'media_cache')

def get_mime_type(fname):
    ext = os.path.splitext(fname)[1].lower()
    if ext in ('.mp3', '.wav', '.m4a', '.aac'):
        return f'audio/{ext.replace(".", "")}'
    elif ext in ('.mp4', '.webm'):
        return f'video/{ext.replace(".", "")}'
    elif ext in ('.png', '.jpg', '.jpeg', '.gif', '.webp'):
        return f'image/{ext.replace(".", "").replace("jpg", "jpeg")}'
    return 'application/octet-stream'

def migrate(db_url):
    print("🚀 [Supabase 마이그레이션] 시작합니다...")
    if not os.path.exists(SQLITE_DB):
        print(f"❌ 로컬 DB 파일({SQLITE_DB})을 찾을 수 없습니다.")
        return

    print("🔌 Supabase PostgreSQL 연결 중...")
    pg_conn = psycopg2.connect(db_url)
    pg_cursor = pg_conn.cursor()

    sq_conn = sqlite3.connect(SQLITE_DB)
    sq_cursor = sq_conn.cursor()

    # 1. 테이블 초기화 (PostgreSQL 전용 테이블)
    print("📋 Supabase 데이터베이스 테이블 구조 생성 중...")
    pg_cursor.execute("""
        CREATE TABLE IF NOT EXISTS kv_store (key TEXT PRIMARY KEY, value TEXT);
        CREATE TABLE IF NOT EXISTS players (name TEXT PRIMARY KEY, score INTEGER, contribution INTEGER);
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
        );
        CREATE TABLE IF NOT EXISTS donation_history (
            id SERIAL PRIMARY KEY,
            timestamp TEXT,
            name TEXT,
            amount INTEGER,
            current_total INTEGER, 
            message TEXT,
            source TEXT,
            tx_id TEXT
        );
        CREATE TABLE IF NOT EXISTS reaction_files (
            id TEXT PRIMARY KEY,
            filename TEXT,
            content_type TEXT,
            file_data BYTEA
        );
        CREATE TABLE IF NOT EXISTS reaction_items (
            id SERIAL PRIMARY KEY,
            title TEXT,
            amount INTEGER DEFAULT 0,
            audio_file_id TEXT,
            image_file_id TEXT,
            is_enabled BOOLEAN DEFAULT TRUE
        );
        CREATE TABLE IF NOT EXISTS vip_donators (
            name TEXT PRIMARY KEY,
            grade TEXT NOT NULL,
            custom_color TEXT DEFAULT '#ffd700',
            summary TEXT
        );
    """)
    pg_conn.commit()

    # 2. KV Store 이관
    print("🔄 kv_store 마이그레이션 중...")
    sq_cursor.execute("SELECT key, value FROM kv_store")
    for row in sq_cursor.fetchall():
        pg_cursor.execute("INSERT INTO kv_store (key, value) VALUES (%s, %s) ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value", row)

    # 3. Players 이관
    print("🔄 players 마이그레이션 중...")
    sq_cursor.execute("SELECT name, score, contribution FROM players")
    for row in sq_cursor.fetchall():
        pg_cursor.execute("INSERT INTO players (name, score, contribution) VALUES (%s, %s, %s) ON CONFLICT (name) DO UPDATE SET score = EXCLUDED.score, contribution = EXCLUDED.contribution", row)

    # 4. Bank Ledger 이관
    print("🔄 bank_ledger 마이그레이션 중...")
    sq_cursor.execute("SELECT timestamp, player_name, tx_type, score_change, score_balance, contrib_change, contrib_balance, description FROM bank_ledger")
    for row in sq_cursor.fetchall():
        pg_cursor.execute("""
            INSERT INTO bank_ledger (timestamp, player_name, tx_type, score_change, score_balance, contrib_change, contrib_balance, description)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, row)

    # 5. Donation History 이관
    print("🔄 donation_history 마이그레이션 중...")
    sq_cursor.execute("SELECT timestamp, name, amount, current_total, message, source, tx_id FROM donation_history")
    for row in sq_cursor.fetchall():
        pg_cursor.execute("""
            INSERT INTO donation_history (timestamp, name, amount, current_total, message, source, tx_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, row)

    # 6. VIP Donators 이관
    try:
        print("🔄 vip_donators 마이그레이션 중...")
        sq_cursor.execute("SELECT name, grade, custom_color, summary FROM vip_donators")
        for row in sq_cursor.fetchall():
            pg_cursor.execute("INSERT INTO vip_donators (name, grade, custom_color, summary) VALUES (%s, %s, %s, %s) ON CONFLICT (name) DO NOTHING", row)
    except Exception as e:
        print(f"  └ vip_donators 이관 생략: {e}")

    # 7. Reaction Items 이관
    try:
        print("🔄 reaction_items 마이그레이션 중...")
        sq_cursor.execute("SELECT id, title, amount, audio_file_id, image_file_id, is_enabled FROM reaction_items")
        for row in sq_cursor.fetchall():
            pg_cursor.execute("""
                INSERT INTO reaction_items (id, title, amount, audio_file_id, image_file_id, is_enabled)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET title = EXCLUDED.title, amount = EXCLUDED.amount, audio_file_id = EXCLUDED.audio_file_id, image_file_id = EXCLUDED.image_file_id, is_enabled = EXCLUDED.is_enabled
            """, (row[0], row[1], row[2], row[3], row[4], bool(row[5])))
    except Exception as e:
        print(f"  └ reaction_items 이관 생략: {e}")

    # 8. Media Cache 및 Reaction Files 이관 (BYTEA 저장)
    print("🖼️🎵 media_cache 파일 바이너리 Supabase 이관 중...")
    if os.path.exists(MEDIA_CACHE_DIR):
        file_count = 0
        for fname in os.listdir(MEDIA_CACHE_DIR):
            fpath = os.path.join(MEDIA_CACHE_DIR, fname)
            if os.path.isfile(fpath) and os.path.getsize(fpath) > 0:
                with open(fpath, 'rb') as f:
                    file_data = f.read()
                file_id = fname.split('_')[0] if '_' in fname else fname
                content_type = get_mime_type(fname)
                pg_cursor.execute("""
                    INSERT INTO reaction_files (id, filename, content_type, file_data)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (id) DO UPDATE SET file_data = EXCLUDED.file_data, filename = EXCLUDED.filename, content_type = EXCLUDED.content_type
                """, (file_id, fname, content_type, psycopg2.Binary(file_data)))
                file_count += 1
        print(f"  └ {file_count}개 파일 Supabase reaction_files 테이블 업로드 완료!")

    pg_conn.commit()
    pg_cursor.close()
    pg_conn.close()
    sq_conn.close()
    print("✨ [Supabase 마이그레이션 완료] 모든 데이터와 미디어가 정상적으로 이관되었습니다!")

if __name__ == '__main__':
    db_url = os.environ.get('DATABASE_URL')
    if len(sys.argv) > 1:
        db_url = sys.argv[1]
    if not db_url:
        print("사용법: python migrate_to_supabase.py <DATABASE_URL>")
        sys.exit(1)
    migrate(db_url)
