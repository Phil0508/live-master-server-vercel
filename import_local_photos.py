import os
import shutil
import sqlite3
import re

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PHOTOS_DIR = os.path.join(BASE_DIR, '사진')
MEDIA_CACHE_DIR = os.path.join(BASE_DIR, 'media_cache')
os.makedirs(MEDIA_CACHE_DIR, exist_ok=True)

def fix_db_and_import():
    db_path = os.path.join(BASE_DIR, 'live_master.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 1. 기존 reaction_files, reaction_items 테이블 깔끔하게 재생성
    cursor.execute("DROP TABLE IF EXISTS reaction_files")
    cursor.execute("DROP TABLE IF EXISTS reaction_items")
    
    cursor.execute("""
        CREATE TABLE reaction_files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            content_type TEXT,
            file_data BLOB
        )
    """)
    
    cursor.execute("""
        CREATE TABLE reaction_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            audio_file_id INTEGER,
            image_file_id INTEGER,
            amount INTEGER DEFAULT 0,
            is_enabled INTEGER DEFAULT 1
        )
    """)
    conn.commit()

    if not os.path.exists(PHOTOS_DIR):
        print("Photos dir missing")
        return

    photo_files = [f for f in os.listdir(PHOTOS_DIR) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif'))]
    print(f"Importing {len(photo_files)} photo files...")

    for fname in photo_files:
        src_path = os.path.join(PHOTOS_DIR, fname)
        dest_path = os.path.join(MEDIA_CACHE_DIR, fname)
        
        # media_cache 복사
        try:
            shutil.copy2(src_path, dest_path)
        except Exception:
            pass

        num_match = re.search(r'\d+', fname)
        amount = int(num_match.group()) if num_match else 0
        title = os.path.splitext(fname)[0]
        mime = "image/png" if fname.lower().endswith(".png") else "image/jpeg"

        cursor.execute(
            "INSERT INTO reaction_files (filename, content_type) VALUES (?, ?)",
            (fname, mime)
        )
        file_id = cursor.lastrowid

        # media_cache 에 ID_파일명 복사본 생성
        id_dest_path = os.path.join(MEDIA_CACHE_DIR, f"{file_id}_{fname}")
        try:
            shutil.copy2(src_path, id_dest_path)
        except Exception:
            pass

        cursor.execute(
            "INSERT INTO reaction_items (title, image_file_id, amount, is_enabled) VALUES (?, ?, ?, 1)",
            (title, file_id, amount)
        )

    conn.commit()
    conn.close()
    print("SUCCESSFULLY BUILT AUTOINCREMENT DB AND MATCHED 85 MEDIA FILES!")

if __name__ == '__main__':
    fix_db_and_import()
