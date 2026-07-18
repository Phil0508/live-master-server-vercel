import os
import json
import urllib.request
import sqlite3
from dotenv import load_dotenv

load_dotenv()

MEDIA_CACHE_DIR = os.path.join(os.path.dirname(__file__), 'media_cache')
os.makedirs(MEDIA_CACHE_DIR, exist_ok=True)

SUPABASE_URL = os.environ.get('SUPABASE_URL', 'https://vkwytlnyxetgvhzthwzw.supabase.co')
SUPABASE_KEY = os.environ.get('SUPABASE_SERVICE_ROLE_KEY') or os.environ.get('SUPABASE_ANON_KEY')

print(f"[REACTION MEDIA SYNC] Fetching directly from Supabase Cloud API...")
print(f"Supabase URL: {SUPABASE_URL}")

def get_local_db_connection():
    db_path = os.path.join(os.path.dirname(__file__), 'live_master.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def fetch_supabase_rest(endpoint):
    url = f"{SUPABASE_URL}/rest/v1/{endpoint}?select=*"
    req = urllib.request.Request(url, headers={
        'apikey': SUPABASE_KEY,
        'Authorization': f'Bearer {SUPABASE_KEY}',
        'Content-Type': 'application/json'
    })
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode('utf-8'))

def sync_reaction_files():
    try:
        supabase_files = fetch_supabase_rest('reaction_files')
        print(f"Fetched {len(supabase_files)} reaction_files records from Supabase Cloud!")
    except Exception as e:
        print(f"Error fetching from Supabase Cloud REST: {e}")
        supabase_files = []

    try:
        supabase_items = fetch_supabase_rest('reaction_items')
        print(f"Fetched {len(supabase_items)} reaction_items records from Supabase Cloud!")
    except Exception as e:
        print(f"Error fetching reaction_items: {e}")
        supabase_items = []

    # 1. 로컬 SQLite DB 동기화
    conn = get_local_db_connection()
    cursor = conn.cursor()

    for item in supabase_items:
        try:
            cursor.execute("""
                INSERT INTO reaction_items (id, title, audio_file_id, image_file_id, amount, is_enabled)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    title=excluded.title,
                    audio_file_id=excluded.audio_file_id,
                    image_file_id=excluded.image_file_id,
                    amount=excluded.amount,
                    is_enabled=excluded.is_enabled
            """, (
                item.get('id'),
                item.get('title'),
                item.get('audio_file_id'),
                item.get('image_file_id'),
                item.get('amount', 0),
                1 if item.get('is_enabled', True) else 0
            ))
        except Exception as e:
            print(f"Local DB sync error for item {item.get('id')}: {e}")

    for file_rec in supabase_files:
        try:
            cursor.execute("""
                INSERT INTO reaction_files (id, filename, mime_type, storage_path, url)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    filename=excluded.filename,
                    storage_path=excluded.storage_path,
                    url=excluded.url
            """, (
                file_rec.get('id'),
                file_rec.get('filename') or file_rec.get('name'),
                file_rec.get('mime_type') or file_rec.get('file_type'),
                file_rec.get('storage_path'),
                file_rec.get('url')
            ))
        except Exception as e:
            # 컬럼명이 다른 경우 처리
            pass
            
    conn.commit()

    # 2. 미디어 파일 로컬 다운로드 및 매칭
    downloaded_count = 0
    already_exists_count = 0
    failed_count = 0

    for f in supabase_files:
        file_id = f.get('id')
        filename = f.get('filename') or f.get('name') or f"file_{file_id}"
        storage_path = f.get('storage_path')
        url = f.get('url')

        local_filename = f"{file_id}_{filename}"
        local_path = os.path.join(MEDIA_CACHE_DIR, local_filename)
        alt_local_path = os.path.join(MEDIA_CACHE_DIR, filename)

        if (os.path.exists(local_path) and os.path.getsize(local_path) > 0) or \
           (os.path.exists(alt_local_path) and os.path.getsize(alt_local_path) > 0):
            already_exists_count += 1
            continue

        download_url = None
        if url and url.startswith('http'):
            download_url = url
        elif storage_path:
            download_url = f"{SUPABASE_URL}/storage/v1/object/public/reaction-files/{storage_path}"

        if not download_url:
            print(f"[SKIP] No valid download URL for ID {file_id}: {filename}")
            failed_count += 1
            continue

        try:
            print(f"[DOWNLOADING] ID {file_id}: {filename} <- {download_url}")
            req = urllib.request.Request(download_url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = resp.read()
                with open(local_path, 'wb') as out_f:
                    out_f.write(data)
                # 원본 파일명으로도 복사본 생성하여 서빙 실패 방지
                with open(alt_local_path, 'wb') as alt_out_f:
                    alt_out_f.write(data)
                print(f"[SUCCESS] ID {file_id}: {filename} ({len(data)} bytes)")
                downloaded_count += 1
        except Exception as e:
            print(f"[FAILED] ID {file_id} ({filename}): {e}")
            failed_count += 1

    print("\n=========================================")
    print(f"SYNC RESULTS SUMMARY:")
    print(f" - Newly Downloaded: {downloaded_count}")
    print(f" - Already Exists Locally: {already_exists_count}")
    print(f" - Failed / Missing: {failed_count}")
    print("=========================================\n")
    conn.close()

if __name__ == '__main__':
    sync_reaction_files()
