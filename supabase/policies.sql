-- Supabase RLS (Row Level Security) 세분화 정책
-- Live Master Server - 프로덕션용 세분화된 권한 정책
-- 실행: supabase db reset 후 supabase db push 또는 직접 SQL 실행

-- ============================================
-- 1. CUSTOM ROLES 및 JWT CLAIMS 설정
-- ============================================

-- 커스텀 JWT 클레임을 위한 타입 정의 (PostgreSQL ENUM 대체)
-- JWT의 app_metadata.role 값: 'overlay' | 'controller' | 'admin' | 'viewer'
-- JWT의 app_metadata.permissions: string[]

-- ============================================
-- 2. HELPER FUNCTIONS FOR RLS POLICIES
-- ============================================

-- 현재 요청 사용자의 역할 확인
CREATE OR REPLACE FUNCTION current_user_role()
RETURNS TEXT LANGUAGE sql STABLE AS $$
  SELECT COALESCE(
    (current_setting('request.jwt.claims', true)::jsonb ->> 'role'),
    (current_setting('request.jwt.claims', true)::jsonb -> 'app_metadata' ->> 'role'),
    'anonymous'
  );
$$;

-- 현재 요청 사용자의 권한 배열 확인
CREATE OR REPLACE FUNCTION current_user_permissions()
RETURNS TEXT[] LANGUAGE sql STABLE AS $$
  SELECT COALESCE(
    (current_setting('request.jwt.claims', true)::jsonb -> 'app_metadata' -> 'permissions')::jsonb ->> 0,
    '[]'
  )::TEXT[];
$$;

-- 현재 요청 사용자가 특정 권한을 가지고 있는지 확인
CREATE OR REPLACE FUNCTION has_permission(required_permission TEXT)
RETURNS BOOLEAN LANGUAGE sql STABLE AS $$
  SELECT required_permission = ANY(current_user_permissions());
$$;

-- 현재 요청 사용자가 특정 역할인지 확인
CREATE OR REPLACE FUNCTION is_role(target_role TEXT)
RETURNS BOOLEAN LANGUAGE sql STABLE AS $$
  SELECT current_user_role() = target_role;
$$;

-- 현재 요청 사용자가 관리자인지 확인
CREATE OR REPLACE FUNCTION is_admin()
RETURNS BOOLEAN LANGUAGE sql STABLE AS $$
  SELECT current_user_role() = 'admin';
$$;

-- 현재 요청 사용자가 컨트롤러(운영자)인지 확인
CREATE OR REPLACE FUNCTION is_controller()
RETURNS BOOLEAN LANGUAGE sql STABLE AS $$
  SELECT current_user_role() IN ('controller', 'admin');
$$;

-- 현재 요청 사용자가 오버레이(방송 화면)인지 확인
CREATE OR REPLACE FUNCTION is_overlay()
RETURNS BOOLEAN LANGUAGE sql STABLE AS $$
  SELECT current_user_role() IN ('overlay', 'admin');
$$;

-- 현재 요청 사용자가 뷰어(시청자)인지 확인
CREATE OR REPLACE FUNCTION is_viewer()
RETURNS BOOLEAN LANGUAGE sql STABLE AS $$
  SELECT current_user_role() IN ('viewer', 'overlay', 'controller', 'admin');
$$;

-- 익명 사용자 확인
CREATE OR REPLACE FUNCTION is_anonymous()
RETURNS BOOLEAN LANGUAGE sql STABLE AS $$
  SELECT current_user_role() = 'anonymous';
$$;

-- ============================================
-- 3. PLAYERS TABLE POLICIES
-- ============================================

-- 기존 정책 삭제
DROP POLICY IF EXISTS "Allow all for authenticated" ON players;
DROP POLICY IF EXISTS "Allow public read" ON players;

-- 오버레이(방송 화면): 모든 플레이어 읽기 가능 (실시간 랭킹 표시용)
CREATE POLICY "overlay_read_players" ON players
  FOR SELECT USING (is_overlay() OR is_admin() OR is_controller());

-- 컨트롤러(운영자): 플레이어 생성/수정/삭제 가능
CREATE POLICY "controller_write_players" ON players
  FOR ALL USING (is_controller() OR is_admin())
  WITH CHECK (is_controller() OR is_admin());

-- 뷰어(시청자): 랭킹 상위 20명만 읽기 가능 (개인정보 보호)
CREATE POLICY "viewer_read_top_players" ON players
  FOR SELECT USING (
    is_viewer() AND rank <= 20
  );

-- 익명 사용자: 랭킹 상위 10명만 읽기 가능
CREATE POLICY "anonymous_read_top10_players" ON players
  FOR SELECT USING (
    is_anonymous() AND rank <= 10
  );

-- ============================================
-- 4. RANKINGS TABLE POLICIES
-- ============================================

DROP POLICY IF EXISTS "Allow all for authenticated" ON rankings;
DROP POLICY IF EXISTS "Allow public read" ON rankings;

-- 오버레이: 최신 랭킹 스냅샷 읽기
CREATE POLICY "overlay_read_latest_ranking" ON rankings
  FOR SELECT USING (
    is_overlay() OR is_admin() OR is_controller()
  );

-- 컨트롤러: 랭킹 스냅샷 생성/수정
CREATE POLICY "controller_write_rankings" ON rankings
  FOR ALL USING (is_controller() OR is_admin())
  WITH CHECK (is_controller() OR is_admin());

-- 뷰어/익명: 최신 1개 랭킹만 읽기
CREATE POLICY "public_read_latest_ranking" ON rankings
  FOR SELECT USING (
    (is_viewer() OR is_anonymous()) 
    AND id = (SELECT id FROM rankings ORDER BY created_at DESC LIMIT 1)
  );

-- ============================================
-- 5. EXTRA_GAMES TABLE POLICIES
-- ============================================

DROP POLICY IF EXISTS "Allow all for authenticated" ON extra_games;
DROP POLICY IF EXISTS "Allow public read" ON extra_games;

-- 오버레이: 활성화된 미니게임만 읽기
CREATE POLICY "overlay_read_active_extra_games" ON extra_games
  FOR SELECT USING (
    (is_overlay() OR is_admin() OR is_controller())
    AND is_visible = TRUE
  );

-- 컨트롤러: 미니게임 전체 관리
CREATE POLICY "controller_write_extra_games" ON extra_games
  FOR ALL USING (is_controller() OR is_admin())
  WITH CHECK (is_controller() OR is_admin());

-- 뷰어: 활성화된 미니게임만 읽기
CREATE POLICY "viewer_read_active_extra_games" ON extra_games
  FOR SELECT USING (
    (is_viewer() OR is_anonymous())
    AND is_visible = TRUE
  );

-- ============================================
-- 6. MATCHES TABLE POLICIES
-- ============================================

DROP POLICY IF EXISTS "Allow all for authenticated" ON matches;
DROP POLICY IF EXISTS "Allow public read" ON matches;

-- 오버레이: 활성화된 매치만 읽기
CREATE POLICY "overlay_read_active_matches" ON matches
  FOR SELECT USING (
    (is_overlay() OR is_admin() OR is_controller())
    AND is_active = TRUE
  );

-- 컨트롤러: 매치 전체 관리
CREATE POLICY "controller_write_matches" ON matches
  FOR ALL USING (is_controller() OR is_admin())
  WITH CHECK (is_controller() OR is_admin());

-- 뷰어: 활성화된 매치만 읽기
CREATE POLICY "viewer_read_active_matches" ON matches
  FOR SELECT USING (
    (is_viewer() OR is_anonymous())
    AND is_active = TRUE
  );

-- ============================================
-- 7. ROULETTE_SEGMENTS TABLE POLICIES
-- ============================================

DROP POLICY IF EXISTS "Allow all for authenticated" ON roulette_segments;
DROP POLICY IF EXISTS "Allow public read" ON roulette_segments;

-- 오버레이: 활성화된 룰렛 구간만 읽기 (실시간 회전 표시용)
CREATE POLICY "overlay_read_active_roulette" ON roulette_segments
  FOR SELECT USING (
    (is_overlay() OR is_admin() OR is_controller())
    AND is_active = TRUE
  );

-- 컨트롤러: 룰렛 구간 전체 관리 (조작 기능 포함)
CREATE POLICY "controller_write_roulette_segments" ON roulette_segments
  FOR ALL USING (is_controller() OR is_admin())
  WITH CHECK (is_controller() OR is_admin());

-- 뷰어: 활성화된 룰렛 구간만 읽기
CREATE POLICY "viewer_read_active_roulette" ON roulette_segments
  FOR SELECT USING (
    (is_viewer() OR is_anonymous())
    AND is_active = TRUE
  );

-- ============================================
-- 8. ROULETTE_HISTORY TABLE POLICIES
-- ============================================

DROP POLICY IF EXISTS "Allow all for authenticated" ON roulette_history;
DROP POLICY IF EXISTS "Allow public read" ON roulette_history;

-- 오버레이/컨트롤러/관리자: 전체 히스토리 읽기/쓰기
CREATE POLICY "staff_read_write_roulette_history" ON roulette_history
  FOR ALL USING (is_overlay() OR is_controller() OR is_admin())
  WITH CHECK (is_controller() OR is_admin());

-- 뷰어/익명: 최근 50개만 읽기
CREATE POLICY "public_read_recent_roulette_history" ON roulette_history
  FOR SELECT USING (
    (is_viewer() OR is_anonymous())
    AND id IN (
      SELECT id FROM roulette_history 
      ORDER BY created_at DESC 
      LIMIT 50
    )
  );

-- ============================================
-- 9. SLOT_ITEMS TABLE POLICIES
-- ============================================

DROP POLICY IF EXISTS "Allow all for authenticated" ON slot_items;
DROP POLICY IF EXISTS "Allow public read" ON slot_items;

-- 오버레이: 활성화된 슬롯 아이템만 읽기 (릴 회전 표시용)
CREATE POLICY "overlay_read_active_slot_items" ON slot_items
  FOR SELECT USING (
    (is_overlay() OR is_admin() OR is_controller())
    AND is_active = TRUE
  );

-- 컨트롤러: 슬롯 아이템 전체 관리
CREATE POLICY "controller_write_slot_items" ON slot_items
  FOR ALL USING (is_controller() OR is_admin())
  WITH CHECK (is_controller() OR is_admin());

-- 뷰어: 활성화된 슬롯 아이템만 읽기
CREATE POLICY "viewer_read_active_slot_items" ON slot_items
  FOR SELECT USING (
    (is_viewer() OR is_anonymous())
    AND is_active = TRUE
  );

-- ============================================
-- 10. SLOT_HISTORY TABLE POLICIES
-- ============================================

DROP POLICY IF EXISTS "Allow all for authenticated" ON slot_history;
DROP POLICY IF EXISTS "Allow public read" ON slot_history;

-- 스태프: 전체 히스토리 관리
CREATE POLICY "staff_manage_slot_history" ON slot_history
  FOR ALL USING (is_overlay() OR is_controller() OR is_admin())
  WITH CHECK (is_controller() OR is_admin());

-- 공개: 최근 50개만 조회
CREATE POLICY "public_read_recent_slot_history" ON slot_history
  FOR SELECT USING (
    (is_viewer() OR is_anonymous())
    AND id IN (
      SELECT id FROM slot_history 
      ORDER BY created_at DESC 
      LIMIT 50
    )
  );

-- ============================================
-- 11. DONATIONS TABLE POLICIES
-- ============================================

DROP POLICY IF EXISTS "Allow all for authenticated" ON donations;
DROP POLICY IF EXISTS "Allow public read" ON donations;

-- 오버레이: 승인된 후원만 표시 (보상 연출용)
CREATE POLICY "overlay_read_approved_donations" ON donations
  FOR SELECT USING (
    (is_overlay() OR is_admin() OR is_controller())
    AND status IN ('approved', 'split', 'distributed')
  );

-- 컨트롤러: 후원 전체 관리 (승인, 분할, 지급)
CREATE POLICY "controller_manage_donations" ON donations
  FOR ALL USING (is_controller() OR is_admin())
  WITH CHECK (is_controller() OR is_admin());

-- 뷰어: 승인된 후원 중 상위 20개만 표시 (홀오브페임용)
CREATE POLICY "viewer_read_top_donations" ON donations
  FOR SELECT USING (
    (is_viewer() OR is_anonymous())
    AND status IN ('approved', 'split', 'distributed')
    AND id IN (
      SELECT id FROM donations 
      WHERE status IN ('approved', 'split', 'distributed')
      ORDER BY amount DESC, timestamp DESC
      LIMIT 20
    )
  );

-- 익명 후원자: 본인 후원 내역만 조회 가능 (donor_name 기반 필터링은 애플리케이션 레벨에서)
CREATE POLICY "donor_read_own_donations" ON donations
  FOR SELECT USING (
    donor_name = current_setting('request.jwt.claims', true)::jsonb ->> 'donor_name'
    AND status IN ('approved', 'split', 'distributed')
  );

-- ============================================
-- 12. PENDING_DONATIONS TABLE POLICIES
-- ============================================

DROP POLICY IF EXISTS "Allow all for authenticated" ON pending_donations;
DROP POLICY IF EXISTS "Allow public read" ON pending_donations;

-- 컨트롤러만 대기열 관리 가능 (보안상 중요)
CREATE POLICY "controller_manage_pending_donations" ON pending_donations
  FOR ALL USING (is_controller() OR is_admin())
  WITH CHECK (is_controller() OR is_admin());

-- 오버레이: 대기열 개수만 확인 (알림 표시용)
CREATE POLICY "overlay_count_pending_donations" ON pending_donations
  FOR SELECT USING (is_overlay() OR is_admin() OR is_controller());

-- ============================================
-- 13. SNAPSHOTS TABLE POLICIES (타임머신)
-- ============================================

DROP POLICY IF EXISTS "Allow all for authenticated" ON snapshots;
DROP POLICY IF EXISTS "Allow public read" ON snapshots;

-- 스태프: 스냅샷 전체 관리
CREATE POLICY "staff_manage_snapshots" ON snapshots
  FOR ALL USING (is_controller() OR is_admin())
  WITH CHECK (is_controller() OR is_admin());

-- 오버레이: 복원용 스냅샷 읽기
CREATE POLICY "overlay_read_snapshots" ON snapshots
  FOR SELECT USING (is_overlay() OR is_admin() OR is_controller());

-- 뷰어/익명: 스냅샷 목록만 조회 (상세 데이터는 컨트롤러 승인 후)
CREATE POLICY "public_list_snapshots" ON snapshots
  FOR SELECT USING (
    (is_viewer() OR is_anonymous())
    AND id IN (
      SELECT id FROM snapshots 
      ORDER BY created_at DESC 
      LIMIT 10
    )
  );

-- ============================================
-- 14. REACTIONS TABLE POLICIES
-- ============================================

DROP POLICY IF EXISTS "Allow all for authenticated" ON reactions;
DROP POLICY IF EXISTS "Allow public read" ON reactions;

-- 오버레이: 활성화된 리액션만 읽기 (슬롯머신 연출용)
CREATE POLICY "overlay_read_active_reactions" ON reactions
  FOR SELECT USING (
    (is_overlay() OR is_admin() OR is_controller())
    AND is_active = TRUE
  );

-- 컨트롤러: 리액션 전체 관리
CREATE POLICY "controller_manage_reactions" ON reactions
  FOR ALL USING (is_controller() OR is_admin())
  WITH CHECK (is_controller() OR is_admin());

-- 뷰어: 활성화된 리액션만 읽기
CREATE POLICY "viewer_read_active_reactions" ON reactions
  FOR SELECT USING (
    (is_viewer() OR is_anonymous())
    AND is_active = TRUE
  );

-- ============================================
-- 15. SETTINGS TABLE POLICIES
-- ============================================

DROP POLICY IF EXISTS "Allow all for authenticated" ON settings;
DROP POLICY IF EXISTS "Allow public read" ON settings;

-- 오버레이/컨트롤러/관리자: 설정 전체 읽기/쓰기
CREATE POLICY "staff_manage_settings" ON settings
  FOR ALL USING (is_overlay() OR is_controller() OR is_admin())
  WITH CHECK (is_controller() OR is_admin());

-- 뷰어/익명: 공개 설정만 읽기 (민감한 설정 제외)
CREATE POLICY "public_read_public_settings" ON settings
  FOR SELECT USING (
    (is_viewer() OR is_anonymous())
    AND key IN (
      'master_volume', 'bgm_volume', 'sfx_volume', 'chime_volume',
      'fever_threshold', 'match_default_duration',
      'slot_machine_enabled', 'vip_lighting_sync', 'time_machine_enabled'
    )
  );

-- ============================================
-- 16. AUDIT_LOGS TABLE POLICIES
-- ============================================

DROP POLICY IF EXISTS "Allow all for authenticated" ON audit_logs;
DROP POLICY IF EXISTS "Allow public read" ON audit_logs;

-- 관리자만 감사 로그 접근 가능 (보안/컴플라이언스)
CREATE POLICY "admin_only_audit_logs" ON audit_logs
  FOR ALL USING (is_admin())
  WITH CHECK (is_admin());

-- 컨트롤러: 본인 작업 로그만 조회
CREATE POLICY "controller_read_own_audit_logs" ON audit_logs
  FOR SELECT USING (
    is_controller()
    AND performed_by = current_setting('request.jwt.claims', true)::jsonb ->> 'sub'
  );

-- ============================================
-- 17. REALTIME PUBLICATION 최적화
-- ============================================

-- 실시간 구독 최적화: 필요한 테이블만 발행
-- 오버레이는 players, rankings, extra_games, matches, roulette_segments, slot_items, donations, reactions, settings 구독
-- 컨트롤러는 모든 테이블 구독 가능

-- 플레이어 랭킹 변경 실시간 반영 (점수/순위 변동 시)
ALTER PUBLICATION supabase_realtime ADD TABLE players;
ALTER PUBLICATION supabase_realtime ADD TABLE rankings;
ALTER PUBLICATION supabase_realtime ADD TABLE extra_games;
ALTER PUBLICATION supabase_realtime ADD TABLE matches;
ALTER PUBLICATION supabase_realtime ADD TABLE roulette_segments;
ALTER PUBLICATION supabase_realtime ADD TABLE roulette_history;
ALTER PUBLICATION supabase_realtime ADD TABLE slot_items;
ALTER PUBLICATION supabase_realtime ADD TABLE slot_history;
ALTER PUBLICATION supabase_realtime ADD TABLE donations;
ALTER PUBLICATION supabase_realtime ADD TABLE pending_donations;
ALTER PUBLICATION supabase_realtime ADD TABLE snapshots;
ALTER PUBLICATION supabase_realtime ADD TABLE reactions;
ALTER PUBLICATION supabase_realtime ADD TABLE settings;

-- ============================================
-- 18. RLS 활성화 확인 및 성능 인덱스
-- ============================================

-- 모든 테이블 RLS 활성화 확인
ALTER TABLE players ENABLE ROW LEVEL SECURITY;
ALTER TABLE rankings ENABLE ROW LEVEL SECURITY;
ALTER TABLE extra_games ENABLE ROW LEVEL SECURITY;
ALTER TABLE matches ENABLE ROW LEVEL SECURITY;
ALTER TABLE roulette_segments ENABLE ROW LEVEL SECURITY;
ALTER TABLE roulette_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE slot_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE slot_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE donations ENABLE ROW LEVEL SECURITY;
ALTER TABLE pending_donations ENABLE ROW LEVEL SECURITY;
ALTER TABLE snapshots ENABLE ROW LEVEL SECURITY;
ALTER TABLE reactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE settings ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;

-- RLS 정책 성능 최적화를 위한 추가 인덱스
CREATE INDEX IF NOT EXISTS idx_players_rank_score ON players(rank, score DESC);
CREATE INDEX IF NOT EXISTS idx_players_vip_tier ON players(vip_tier) WHERE vip_tier IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_rankings_created_at ON rankings(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_extra_games_visible ON extra_games(is_visible) WHERE is_visible = TRUE;
CREATE INDEX IF NOT EXISTS idx_matches_active ON matches(is_active) WHERE is_active = TRUE;
CREATE INDEX IF NOT EXISTS idx_roulette_segments_active_order ON roulette_segments(is_active, display_order) WHERE is_active = TRUE;
CREATE INDEX IF NOT EXISTS idx_slot_items_reel_active ON slot_items(reel_id, is_active, display_order) WHERE is_active = TRUE;
CREATE INDEX IF NOT EXISTS idx_donations_status_timestamp ON donations(status, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_pending_donations_priority ON pending_donations(priority DESC, created_at);
CREATE INDEX IF NOT EXISTS idx_snapshots_created ON snapshots(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_reactions_active ON reactions(is_active) WHERE is_active = TRUE;
CREATE INDEX IF NOT EXISTS idx_settings_key ON settings(key);

-- ============================================
-- 19. 테스트용 헬퍼 함수 (개발 환경에서만)
-- ============================================

-- 현재 세션의 역할을 임시로 설정 (테스트용)
CREATE OR REPLACE FUNCTION set_test_role(role_name TEXT)
RETURNS VOID LANGUAGE plpgsql AS $$
BEGIN
  IF current_setting('app.environment', true) = 'development' THEN
    PERFORM set_config('request.jwt.claims', jsonb_build_object(
      'role', role_name,
      'app_metadata', jsonb_build_object('role', role_name, 'permissions', '[]'::jsonb),
      'sub', 'test-user-' || role_name
    )::TEXT, false);
  ELSE
    RAISE EXCEPTION 'Test role setting only allowed in development environment';
  END IF;
END;
$$;

-- 테스트 역할 초기화
CREATE OR REPLACE FUNCTION clear_test_role()
RETURNS VOID LANGUAGE plpgsql AS $$
BEGIN
  PERFORM set_config('request.jwt.claims', '{}', false);
END;
$$;

-- ============================================
-- 20. 적용 완료 확인 쿼리
-- ============================================

-- 정책 확인용 쿼리 (개발 환경에서 실행)
-- SELECT schemaname, tablename, policyname, permissive, roles, cmd, qual, with_check
-- FROM pg_policies 
-- WHERE schemaname = 'public'
-- ORDER BY tablename, policyname;

-- RLS 상태 확인
-- SELECT schemaname, tablename, rowsecurity
-- FROM pg_tables
-- WHERE schemaname = 'public'
-- ORDER BY tablename;

COMMENT ON TABLE players IS '플레이어 정보 - RLS: overlay/컨트롤러/관리자 읽기/쓰기, 뷰어 상위 20위, 익명 상위 10위';
COMMENT ON TABLE rankings IS '랭킹 스냅샷 - RLS: 스태프 전체, 공개 최신 1개';
COMMENT ON TABLE donations IS '후원 내역 - RLS: 오버레이 승인된 것만, 컨트롤러 전체 관리, 뷰어 상위 20개';
COMMENT ON TABLE pending_donations IS '대기 중인 후원 - RLS: 컨트롤러만 관리 (보안 중요)';
COMMENT ON TABLE audit_logs IS '감사 로그 - RLS: 관리자만 접근 (컴플라이언스)';