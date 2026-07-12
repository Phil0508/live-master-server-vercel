-- ==========================================
-- Supabase PostgreSQL 테이블 생성 스크립트
-- Supabase 대시보드 > SQL Editor > New Query
-- 위에 들어가서 아래 전체를 복사 붙여넣기 후 Run 버튼 클릭!
-- ==========================================

-- kv_store: 설정 키-값 저장소
CREATE TABLE IF NOT EXISTS kv_store (
    key TEXT PRIMARY KEY,
    value TEXT
);

-- players: 플레이어 점수판
CREATE TABLE IF NOT EXISTS players (
    name TEXT PRIMARY KEY,
    score INTEGER,
    contribution INTEGER
);

-- donation_history: 후원 내역
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

-- snapshots: 타임머신 스냅샷
CREATE TABLE IF NOT EXISTS snapshots (
    id SERIAL PRIMARY KEY,
    timestamp TEXT,
    state_json TEXT,
    summary TEXT
);

-- reaction_files: 리액션 파일 (오디오/이미지)
CREATE TABLE IF NOT EXISTS reaction_files (
    id TEXT PRIMARY KEY,
    filename TEXT,
    content_type TEXT,
    file_data BYTEA
);

-- reaction_items: 리액션 아이템
CREATE TABLE IF NOT EXISTS reaction_items (
    id SERIAL PRIMARY KEY,
    title TEXT,
    amount INTEGER DEFAULT 0,
    audio_file_id TEXT,
    image_file_id TEXT,
    is_enabled BOOLEAN DEFAULT TRUE
);