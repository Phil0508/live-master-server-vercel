import os
import shutil
import sqlite3
import re

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PHOTOS_DIR = os.path.join(BASE_DIR, '사진')
MEDIA_CACHE_DIR = os.path.join(BASE_DIR, 'media_cache')
os.makedirs(MEDIA_CACHE_DIR, exist_ok=True)

print(f"[LOCAL PHOTOS AUTO MATCH] source: {PHOTOS_DIR} -> dest: {MEDIA_CACHE_DIR}")

def get_db():
    conn = sqlite3.connect(os.path.join(BASE_DIR, 'live_master.db'))
    conn.row_factory = sqlite3.Row
    return conn

def import_photos():
    if not os.path.exists(PHOTOS_DIR):
        print(f"❌ [오류] 사진 폴더가 없습니다: {PHOTOS_DIR}")
        return

    conn = get_db()
    cursor = conn.cursor()

    photo_files = [f for f in os.listdir(PHOTOS_DIR) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif'))]
    print(f"Total photo files found: {len(photo_files)}")

    copied_count = 0
    matched_count = 0

    for fname in photo_files:
        src_path = os.path.join(PHOTOS_DIR, fname)
        dest_path = os.path.join(MEDIA_CACHE_DIR, fname)
        
        # 1. media_cache에 복사
        try:
            shutil.copy2(src_path, dest_path)
            copied_count += 1
        except Exception as e:
            print(f"Copy error for {fname}: {e}")

        # 2. 파일명에서 후원 금액(숫자) 추출
        num_match = re.search(r'\d+', fname)
        amount = int(num_match.group()) if num_match else 0
        title = os.path.splitext(fname)[0]

        # 3. reaction_files 및 reaction_items DB 등록
        try:
            mime = "image/png" if fname.lower().endswith(".png") else "image/jpeg"
            cursor.execute(
                "INSERT INTO reaction_files (filename, content_type) VALUES (?, ?)",
                (fname, mime)
            )
            file_id = cursor.lastrowid
            
            # id_filename 구조로도 media_cache에 복사본 생성하여 서빙 100% 보장
            id_dest_path = os.path.join(MEDIA_CACHE_DIR, f"{file_id}_{fname}")
            shutil.copy2(src_path, id_dest_path)

            cursor.execute(
                "INSERT INTO reaction_items (title, image_file_id, amount, is_enabled) VALUES (?, ?, ?, 1)",
                (title, file_id, amount)
            )
            matched_count += 1
        except Exception as e:
            print(f"DB insert notice ({fname}): {e}")

    conn.commit()
    conn.close()

    print("\n=========================================")
    print(f"LOCAL PHOTOS IMPORT COMPLETE:")
    print(f" - Copied to media_cache: {copied_count}")
    print(f" - Matched in local DB: {matched_count}")
    print("=========================================\n")

if __name__ == '__main__':
    import_photos()
