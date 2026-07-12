import sqlite3
import psycopg2
import os
import sys

def migrate():
    print("====================================================")
    print("   SQLite -> PostgreSQL Migration Tool")
    print("====================================================\n")
    
    db_file = 'live_master.db'
    if not os.path.exists(db_file):
        print(f"Error: Local DB file '{db_file}' not found.")
        sys.exit(1)
        
    pg_url = input("Enter PostgreSQL DATABASE_URL:\n> ").strip()
    if not pg_url:
        print("Error: URL is empty.")
        sys.exit(1)
        
    print("\nConnecting to databases...")
    
    try:
        lite_conn = sqlite3.connect(db_file)
        lite_cur = lite_conn.cursor()
        
        pg_conn = psycopg2.connect(pg_url)
        pg_cur = pg_conn.cursor()
        
        print("Connected successfully to both databases.")
        
        print("\n[1/5] Preparing PostgreSQL schemas...")
        pg_cur.execute("CREATE TABLE IF NOT EXISTS kv_store (key TEXT PRIMARY KEY, value TEXT)")
        pg_cur.execute("CREATE TABLE IF NOT EXISTS players (name TEXT PRIMARY KEY, score INTEGER, contribution INTEGER)")
        pg_cur.execute("""
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
        pg_cur.execute("""
            CREATE TABLE IF NOT EXISTS snapshots (
                id SERIAL PRIMARY KEY,
                timestamp TEXT,
                state_json TEXT,
                summary TEXT
            )
        """)
        pg_conn.commit()
        
        print("[2/5] Migrating kv_store...")
        lite_cur.execute("SELECT key, value FROM kv_store")
        kv_rows = lite_cur.fetchall()
        for k, v in kv_rows:
            pg_cur.execute(
                "INSERT INTO kv_store (key, value) VALUES (%s, %s) ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value",
                (k, v)
            )
        pg_conn.commit()
        print(f"  - Migrated {len(kv_rows)} kv_store rows.")
        
        print("[3/5] Migrating players...")
        pg_cur.execute("DELETE FROM players")
        lite_cur.execute("SELECT name, score, contribution FROM players")
        player_rows = lite_cur.fetchall()
        for name, score, contrib in player_rows:
            pg_cur.execute(
                "INSERT INTO players (name, score, contribution) VALUES (%s, %s, %s) ON CONFLICT (name) DO UPDATE SET score = EXCLUDED.score, contribution = EXCLUDED.contribution",
                (name, score, contrib)
            )
        pg_conn.commit()
        print(f"  - Migrated {len(player_rows)} players.")
        
        print("[4/5] Migrating donation_history...")
        pg_cur.execute("TRUNCATE TABLE donation_history RESTART IDENTITY CASCADE")
        
        # Check if tx_id column exists in sqlite
        lite_cur.execute("PRAGMA table_info(donation_history)")
        columns = [row[1] for row in lite_cur.fetchall()]
        has_tx_id = 'tx_id' in columns
        
        if has_tx_id:
            lite_cur.execute("SELECT id, timestamp, name, amount, current_total, message, source, tx_id FROM donation_history")
        else:
            lite_cur.execute("SELECT id, timestamp, name, amount, current_total, message, source, NULL FROM donation_history")
            
        hist_rows = lite_cur.fetchall()
        for row in hist_rows:
            pg_cur.execute(
                "INSERT INTO donation_history (id, timestamp, name, amount, current_total, message, source, tx_id) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                row
            )
        if hist_rows:
            max_id = max(r[0] for r in hist_rows)
            pg_cur.execute(f"SELECT setval('donation_history_id_seq', {max_id})")
        pg_conn.commit()
        print(f"  - Migrated {len(hist_rows)} donation_history rows.")
        
        print("[5/5] Migrating snapshots...")
        pg_cur.execute("TRUNCATE TABLE snapshots RESTART IDENTITY CASCADE")
        lite_cur.execute("SELECT id, timestamp, state_json, summary FROM snapshots")
        snap_rows = lite_cur.fetchall()
        for row in snap_rows:
            pg_cur.execute(
                "INSERT INTO snapshots (id, timestamp, state_json, summary) VALUES (%s, %s, %s, %s)",
                row
            )
        if snap_rows:
            max_snap_id = max(r[0] for r in snap_rows)
            pg_cur.execute(f"SELECT setval('snapshots_id_seq', {max_snap_id})")
        pg_conn.commit()
        print(f"  - Migrated {len(snap_rows)} snapshots.")
        
        print("\n====================================================")
        print("   Migration Completed Successfully!")
        print("====================================================")
        
        lite_conn.close()
        pg_conn.close()
        
    except Exception as e:
        print("\nError occurred during migration:")
        print(e)
        sys.exit(1)

if __name__ == '__main__':
    migrate()
