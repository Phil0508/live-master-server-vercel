-- Seed data for Live Master Server local development
-- Run with: supabase db reset (includes seed)

-- ============================================
-- SAMPLE PLAYERS
-- ============================================
INSERT INTO players (id, name, score, contribution, rank, badge, is_vip, is_vvip, vip_tier, neon_color_hex, audio_chime) VALUES
('11111111-1111-1111-1111-111111111111', '플레이어김', 12500, 50000, 1, 'gold', true, false, 'vip', '#FFD700', '/sounds/vip-chime.mp3'),
('22222222-2222-2222-2222-222222222222', '플레이어이', 9800, 45000, 2, 'silver', false, false, null, '#C0C0C0', '/sounds/rank-up.mp3'),
('33333333-3333-3333-3333-333333333333', '플레이어박', 8700, 40000, 3, 'bronze', false, false, null, '#CD7F32', '/sounds/rank-up.mp3'),
('44444444-4444-4444-4444-444444444444', '플레이어최', 7200, 35000, 4, null, false, false, null, '#888888', null),
('55555555-5555-5555-5555-555555555555', '플레이어정', 6800, 30000, 5, null, false, false, null, '#888888', null),
('66666666-6666-6666-6666-666666666666', '플레이어강', 5500, 25000, 6, null, true, false, 'vip', '#FFD700', '/sounds/vip-chime.mp3'),
('77777777-7777-7777-7777-777777777777', '플레이어조', 4200, 20000, 7, null, false, true, 'vvip', '#E8B4B8', '/sounds/vvip-chime.mp3'),
('88888888-8888-8888-8888-888888888888', '플레이어윤', 3800, 18000, 8, null, false, false, null, '#888888', null),
('99999999-9999-9999-9999-999999999999', '플레이어장', 3200, 15000, 9, null, false, false, null, '#888888', null),
('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', '플레이어임', 2800, 12000, 10, null, false, false, null, '#888888', null),
('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', '플레이어한', 2500, 10000, 11, null, false, false, null, '#888888', null),
('cccccccc-cccc-cccc-cccc-cccccccccccc', '플레이어오', 2100, 8000, 12, null, false, false, null, '#888888', null),
('dddddddd-dddd-dddd-dddd-dddddddddddd', '플레이어서', 1800, 7000, 13, null, false, false, null, '#888888', null),
('eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee', '플레이어신', 1500, 5000, 14, null, false, false, null, '#888888', null),
('ffffffff-ffff-ffff-ffff-ffffffffffff', '플레이어김2', 1200, 3000, 15, null, false, false, null, '#888888', null)
ON CONFLICT (id) DO NOTHING;

-- ============================================
-- SAMPLE RANKING SNAPSHOT
-- ============================================
INSERT INTO rankings (left_column, right_column, bottom_fixed) VALUES (
  jsonb_build_object(
    'id', 'left',
    'title', '좌측 랭킹',
    'players', jsonb_agg(
      jsonb_build_object(
        'id', id,
        'name', name,
        'score', score,
        'contribution', contribution,
        'rank', rank,
        'badge', badge,
        'is_vip', is_vip,
        'is_vvip', is_vvip
      )
      ORDER BY rank
    )
  )::jsonb,
  jsonb_build_object(
    'id', 'right',
    'title', '우측 랭킹',
    'players', jsonb_build_array()
  )::jsonb,
  jsonb_build_object(
    'id', 'excel-bottom-fixed',
    'label', '방송 운영비 정산',
    'total_score', (SELECT SUM(score) FROM players),
    'total_contribution', (SELECT SUM(contribution) FROM players),
    'operating_cost', 100000,
    'net_profit', (SELECT SUM(contribution) FROM players) - 100000
  )::jsonb
)
SELECT * FROM players LIMIT 0; -- Dummy select to make this work

-- Actually insert with proper data
INSERT INTO rankings (left_column, right_column, bottom_fixed) 
SELECT 
  jsonb_build_object(
    'id', 'left',
    'title', '좌측 랭킹',
    'players', (
      SELECT jsonb_agg(to_jsonb(p)) 
      FROM players p 
      WHERE p.rank BETWEEN 1 AND 8
      ORDER BY p.rank
    )
  ),
  jsonb_build_object(
    'id', 'right',
    'title', '우측 랭킹',
    'players', (
      SELECT jsonb_agg(to_jsonb(p)) 
      FROM players p 
      WHERE p.rank BETWEEN 9 AND 15
      ORDER BY p.rank
    )
  ),
  jsonb_build_object(
    'id', 'excel-bottom-fixed',
    'label', '방송 운영비 정산',
    'total_score', (SELECT SUM(score) FROM players),
    'total_contribution', (SELECT SUM(contribution) FROM players),
    'operating_cost', 100000,
    'net_profit', (SELECT SUM(contribution) FROM players) - 100000
  );

-- ============================================
-- SAMPLE ROULETTE SEGMENTS
-- ============================================
INSERT INTO roulette_segments (id, label, weight, color, is_custom_punishment, player_id, display_order) VALUES
('seg-1111-1111-1111-111111111111', '물 마시기', 10, '#FF6B6B', false, NULL, 1),
('seg-2222-2222-2222-222222222222', '춤추기', 8, '#4ECDC4', false, NULL, 2),
('seg-3333-3333-3333-333333333333', '노래 부르기', 8, '#FFE66D', false, NULL, 3),
('seg-4444-4444-4444-444444444444', '플레이어김 벌칙', 5, '#FF6EC7', true, '11111111-1111-1111-1111-111111111111', 4),
('seg-5555-5555-5555-555555555555', '플레이어이 벌칙', 5, '#A8E6CF', true, '22222222-2222-2222-2222-222222222222', 5),
('seg-6666-6666-6666-666666666666', '플레이어박 벌칙', 5, '#FFD3B6', true, '33333333-3333-3333-3333-333333333333', 6),
('seg-7777-7777-7777-777777777777', '10초 플랭크', 6, '#00D4FF', false, NULL, 7),
('seg-8888-8888-8888-888888888888', '애교 3종 세트', 7, '#BC13FE', false, NULL, 8),
('seg-9999-9999-9999-999999999999', '운 좋게 통과!', 15, '#00E676', false, NULL, 9),
('seg-aaaa-aaaa-aaaa-aaaaaaaaaaaa', '전원 한 잔', 10, '#FFD600', false, NULL, 10)
ON CONFLICT (id) DO NOTHING;

-- Calculate angles for roulette
SELECT calculate_roulette_angles();

-- ============================================
-- SAMPLE SLOT ITEMS (3 reels, 12 items each)
-- ============================================
-- Reel 1
INSERT INTO slot_items (id, image_url, label, reaction_amount, probability, reel_id, display_order) VALUES
('slot-1-1', '/images/slot/cherry.png', '체리', 1000, 25, 1, 1),
('slot-1-2', '/images/slot/lemon.png', '레몬', 1000, 20, 1, 2),
('slot-1-3', '/images/slot/orange.png', '오렌지', 2000, 15, 1, 3),
('slot-1-4', '/images/slot/plum.png', '자두', 2000, 15, 1, 4),
('slot-1-5', '/images/slot/bell.png', '종', 5000, 8, 1, 5),
('slot-1-6', '/images/slot/bar.png', 'BAR', 10000, 5, 1, 6),
('slot-1-7', '/images/slot/seven.png', '7', 20000, 3, 1, 7),
('slot-1-8', '/images/slot/cherry.png', '체리', 1000, 25, 1, 8),
('slot-1-9', '/images/slot/lemon.png', '레몬', 1000, 20, 1, 9),
('slot-1-10', '/images/slot/orange.png', '오렌지', 2000, 15, 1, 10),
('slot-1-11', '/images/slot/plum.png', '자두', 2000, 15, 1, 11),
('slot-1-12', '/images/slot/bell.png', '종', 5000, 8, 1, 12)
ON CONFLICT (id) DO NOTHING;

-- Reel 2
INSERT INTO slot_items (id, image_url, label, reaction_amount, probability, reel_id, display_order) VALUES
('slot-2-1', '/images/slot/cherry.png', '체리', 1000, 25, 2, 1),
('slot-2-2', '/images/slot/lemon.png', '레몬', 1000, 20, 2, 2),
('slot-2-3', '/images/slot/orange.png', '오렌지', 2000, 15, 2, 3),
('slot-2-4', '/images/slot/plum.png', '자두', 2000, 15, 2, 4),
('slot-2-5', '/images/slot/bell.png', '종', 5000, 8, 2, 5),
('slot-2-6', '/images/slot/bar.png', 'BAR', 10000, 5, 2, 6),
('slot-2-7', '/images/slot/seven.png', '7', 20000, 3, 2, 7),
('slot-2-8', '/images/slot/cherry.png', '체리', 1000, 25, 2, 8),
('slot-2-9', '/images/slot/lemon.png', '레몬', 1000, 20, 2, 9),
('slot-2-10', '/images/slot/orange.png', '오렌지', 2000, 15, 2, 10),
('slot-2-11', '/images/slot/plum.png', '자두', 2000, 15, 2, 11),
('slot-2-12', '/images/slot/bell.png', '종', 5000, 8, 2, 12)
ON CONFLICT (id) DO NOTHING;

-- Reel 3
INSERT INTO slot_items (id, image_url, label, reaction_amount, probability, reel_id, display_order) VALUES
('slot-3-1', '/images/slot/cherry.png', '체리', 1000, 25, 3, 1),
('slot-3-2', '/images/slot/lemon.png', '레몬', 1000, 20, 3, 2),
('slot-3-3', '/images/slot/orange.png', '오렌지', 2000, 15, 3, 3),
('slot-3-4', '/images/slot/plum.png', '자두', 2000, 15, 3, 4),
('slot-3-5', '/images/slot/bell.png', '종', 5000, 8, 3, 5),
('slot-3-6', '/images/slot/bar.png', 'BAR', 10000, 5, 3, 6),
('slot-3-7', '/images/slot/seven.png', '7', 20000, 3, 3, 7),
('slot-3-8', '/images/slot/cherry.png', '체리', 1000, 25, 3, 8),
('slot-3-9', '/images/slot/lemon.png', '레몬', 1000, 20, 3, 9),
('slot-3-10', '/images/slot/orange.png', '오렌지', 2000, 15, 3, 10),
('slot-3-11', '/images/slot/plum.png', '자두', 2000, 15, 3, 11),
('slot-3-12', '/images/slot/bell.png', '종', 5000, 8, 3, 12)
ON CONFLICT (id) DO NOTHING;

-- ============================================
-- SAMPLE REACTIONS
-- ============================================
INSERT INTO reactions (id, name, amount, image_url, probability) VALUES
('react-1', '작은 하트', 1000, '/images/reactions/small-heart.png', 30),
('react-2', '큰 하트', 5000, '/images/reactions/big-heart.png', 15),
('react-3', '별 폭죽', 10000, '/images/reactions/star-burst.png', 10),
('react-4', '왕관', 50000, '/images/reactions/crown.png', 3),
('react-5', '무지개', 100000, '/images/reactions/rainbow.png', 1),
('react-6', '골드바', 500000, '/images/reactions/gold-bar.png', 0.5),
('react-7', '다이아몬드', 1000000, '/images/reactions/diamond.png', 0.1)
ON CONFLICT (id) DO NOTHING;

-- ============================================
-- SAMPLE SETTINGS (already in schema.sql but ensuring)
-- ============================================
INSERT INTO settings (key, value, description) VALUES
('test_mode', 'true', 'Enable test mode for development'),
('debug_overlay', 'true', 'Show debug info on overlay')
ON CONFLICT (key) DO NOTHING;

-- ============================================
-- SAMPLE SNAPSHOT
-- ============================================
INSERT INTO snapshots (label, rankings, extra_games, matches, donations, created_by)
SELECT 
  '초기 스냅샷 - ' || TO_CHAR(NOW(), 'YYYY-MM-DD HH24:MI'),
  (SELECT jsonb_build_object(
    'leftColumn', left_column,
    'rightColumn', right_column,
    'bottomFixed', bottom_fixed
  ) FROM rankings ORDER BY created_at DESC LIMIT 1),
  (SELECT jsonb_agg(to_jsonb(eg)) FROM extra_games eg),
  (SELECT jsonb_agg(to_jsonb(m)) FROM matches m),
  (SELECT jsonb_agg(to_jsonb(d)) FROM donations d WHERE d.status != 'pending'),
  'system'
WHERE EXISTS (SELECT 1 FROM rankings);