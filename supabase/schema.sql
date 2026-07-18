-- Live Master Server Database Schema
-- Supabase (PostgreSQL) with RLS policies

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================
-- PLAYERS TABLE
-- ============================================
CREATE TABLE players (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  name TEXT NOT NULL,
  score INTEGER NOT NULL DEFAULT 0,
  contribution INTEGER NOT NULL DEFAULT 0,
  rank INTEGER NOT NULL DEFAULT 0,
  badge TEXT CHECK (badge IN ('gold', 'silver', 'bronze', NULL)),
  is_vip BOOLEAN NOT NULL DEFAULT FALSE,
  is_vvip BOOLEAN NOT NULL DEFAULT FALSE,
  vip_tier TEXT CHECK (vip_tier IN ('vip', 'vvip', NULL)),
  crown_effect TEXT,
  neon_color_h INTEGER,
  neon_color_s INTEGER,
  neon_color_l INTEGER,
  neon_color_hex TEXT,
  audio_chime TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_players_score ON players(score DESC);
CREATE INDEX idx_players_rank ON players(rank);
CREATE INDEX idx_players_vip ON players(is_vip, is_vvip);

-- ============================================
-- RANKINGS TABLE (Snapshot of leaderboard state)
-- ============================================
CREATE TABLE rankings (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  left_column JSONB NOT NULL DEFAULT '{"id": "left", "title": "좌측 랭킹", "players": []}',
  right_column JSONB NOT NULL DEFAULT '{"id": "right", "title": "우측 랭킹", "players": []}',
  bottom_fixed JSONB NOT NULL DEFAULT '{"id": "excel-bottom-fixed", "label": "방송 운영비 정산", "total_score": 0, "total_contribution": 0, "operating_cost": 0, "net_profit": 0}',
  snapshot_id UUID, -- References snapshots.id
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================
-- EXTRA GAMES TABLE (Mini-games: Pokemon, Go-Stop, Custom)
-- ============================================
CREATE TABLE extra_games (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  game_type TEXT NOT NULL CHECK (game_type IN ('pokemon', 'go-stop', 'custom')),
  is_visible BOOLEAN NOT NULL DEFAULT FALSE,
  slide_position TEXT NOT NULL DEFAULT 'hidden' CHECK (slide_position IN ('hidden', 'sliding-in', 'visible', 'sliding-out')),
  players JSONB NOT NULL DEFAULT '[]',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================
-- MATCHES TABLE (1v1 / Team Deathmatch)
-- ============================================
CREATE TABLE matches (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  is_active BOOLEAN NOT NULL DEFAULT FALSE,
  red_team JSONB NOT NULL DEFAULT '{"id": "red", "name": "레드팀", "score": 0, "players": [], "neon_color": "#FF3366", "shield_effect": false}',
  blue_team JSONB NOT NULL DEFAULT '{"id": "blue", "name": "블루팀", "score": 0, "players": [], "neon_color": "#00D4FF", "shield_effect": false}',
  countdown INTEGER NOT NULL DEFAULT 300,
  is_fever_time BOOLEAN NOT NULL DEFAULT FALSE,
  fever_border_active BOOLEAN NOT NULL DEFAULT FALSE,
  beep_sound_active BOOLEAN NOT NULL DEFAULT FALSE,
  started_at TIMESTAMPTZ,
  ended_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================
-- ROULETTE SEGMENTS TABLE
-- ============================================
CREATE TABLE roulette_segments (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  label TEXT NOT NULL,
  weight NUMERIC NOT NULL DEFAULT 1,
  color TEXT NOT NULL,
  is_custom_punishment BOOLEAN NOT NULL DEFAULT FALSE,
  player_id UUID REFERENCES players(id) ON DELETE SET NULL,
  start_angle NUMERIC,
  end_angle NUMERIC,
  mid_angle NUMERIC,
  display_order INTEGER NOT NULL DEFAULT 0,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_roulette_segments_active ON roulette_segments(is_active, display_order);

-- ============================================
-- ROULETTE HISTORY TABLE
-- ============================================
CREATE TABLE roulette_history (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  segments JSONB NOT NULL, -- Snapshot of segments at spin time
  winner_id UUID REFERENCES players(id) ON DELETE SET NULL,
  winner_label TEXT,
  winner_segment_id UUID REFERENCES roulette_segments(id) ON DELETE SET NULL,
  rigged_target_id UUID REFERENCES roulette_segments(id) ON DELETE SET NULL,
  rigged BOOLEAN NOT NULL DEFAULT FALSE,
  spun_by TEXT NOT NULL, -- Controller user ID
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================
-- SLOT ITEMS TABLE
-- ============================================
CREATE TABLE slot_items (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  image_url TEXT NOT NULL,
  label TEXT NOT NULL,
  reaction_amount INTEGER NOT NULL,
  probability NUMERIC NOT NULL DEFAULT 1,
  reel_id INTEGER NOT NULL CHECK (reel_id IN (1, 2, 3)),
  display_order INTEGER NOT NULL DEFAULT 0,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_slot_items_reel ON slot_items(reel_id, display_order);

-- ============================================
-- SLOT HISTORY TABLE
-- ============================================
CREATE TABLE slot_history (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  reels JSONB NOT NULL, -- Snapshot of reel state
  result JSONB NOT NULL, -- { matched_item, is_jackpot, message }
  confetti_active BOOLEAN NOT NULL DEFAULT FALSE,
  spun_by TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================
-- DONATIONS TABLE
-- ============================================
CREATE TABLE donations (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  donor_name TEXT NOT NULL,
  amount INTEGER NOT NULL,
  message TEXT,
  reaction_id TEXT,
  reaction_image_url TEXT,
  timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'split', 'distributed')),
  split_type TEXT CHECK (split_type IN ('full', 'half', 'split-n', NULL)),
  split_targets UUID[] DEFAULT '{}',
  processed_at TIMESTAMPTZ,
  processed_by TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_donations_status ON donations(status);
CREATE INDEX idx_donations_timestamp ON donations(timestamp DESC);

-- ============================================
-- PENDING DONATIONS TABLE (Separate for controller queue)
-- ============================================
CREATE TABLE pending_donations (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  donation_id UUID NOT NULL REFERENCES donations(id) ON DELETE CASCADE,
  priority INTEGER NOT NULL DEFAULT 0,
  chime_played BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================
-- SNAPSHOTS TABLE (Time Machine)
-- ============================================
CREATE TABLE snapshots (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  label TEXT NOT NULL,
  rankings JSONB NOT NULL,
  extra_games JSONB NOT NULL,
  matches JSONB NOT NULL,
  donations JSONB NOT NULL,
  created_by TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_snapshots_created ON snapshots(created_at DESC);

-- ============================================
-- REACTIONS TABLE (For slot machine items)
-- ============================================
CREATE TABLE reactions (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  name TEXT NOT NULL UNIQUE,
  amount INTEGER NOT NULL,
  image_url TEXT NOT NULL,
  thumbnail_url TEXT,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  probability NUMERIC NOT NULL DEFAULT 1,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================
-- SETTINGS TABLE (Global configuration)
-- ============================================
CREATE TABLE settings (
  key TEXT PRIMARY KEY,
  value JSONB NOT NULL,
  description TEXT,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_by TEXT
);

-- Default settings
INSERT INTO settings (key, value, description) VALUES
('master_volume', '0.7', 'Master audio volume'),
('bgm_volume', '0.3', 'Background music volume'),
('sfx_volume', '0.8', 'Sound effects volume'),
('chime_volume', '1.0', 'Chime/notification volume'),
('fever_threshold', '60', 'Fever time threshold in seconds'),
('match_default_duration', '300', 'Default match duration in seconds'),
('vip_min_amount', '50000', 'Minimum amount for VIP tier'),
('vvip_min_amount', '200000', 'Minimum amount for VVIP tier'),
('max_snapshots', '50', 'Maximum snapshots to keep'),
('roulette_rigging_enabled', 'true', 'Enable roulette rigging feature'),
('slot_machine_enabled', 'true', 'Enable slot machine feature'),
('vip_lighting_sync', 'true', 'Enable VIP lighting sync'),
('time_machine_enabled', 'true', 'Enable time machine feature')
ON CONFLICT (key) DO NOTHING;

-- ============================================
-- AUDIT LOGS TABLE
-- ============================================
CREATE TABLE audit_logs (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  action TEXT NOT NULL,
  entity_type TEXT NOT NULL, -- 'player', 'donation', 'match', etc.
  entity_id UUID,
  old_data JSONB,
  new_data JSONB,
  performed_by TEXT NOT NULL,
  ip_address INET,
  user_agent TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_audit_logs_entity ON audit_logs(entity_type, entity_id);
CREATE INDEX idx_audit_logs_created ON audit_logs(created_at DESC);

-- ============================================
-- ROW LEVEL SECURITY (RLS) POLICIES
-- ============================================

-- Enable RLS on all tables
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

-- Policy: Allow all operations for authenticated users (controllers)
-- In production, replace with proper role-based policies
CREATE POLICY "Allow all for authenticated" ON players FOR ALL USING (auth.role() = 'authenticated');
CREATE POLICY "Allow all for authenticated" ON rankings FOR ALL USING (auth.role() = 'authenticated');
CREATE POLICY "Allow all for authenticated" ON extra_games FOR ALL USING (auth.role() = 'authenticated');
CREATE POLICY "Allow all for authenticated" ON matches FOR ALL USING (auth.role() = 'authenticated');
CREATE POLICY "Allow all for authenticated" ON roulette_segments FOR ALL USING (auth.role() = 'authenticated');
CREATE POLICY "Allow all for authenticated" ON roulette_history FOR ALL USING (auth.role() = 'authenticated');
CREATE POLICY "Allow all for authenticated" ON slot_items FOR ALL USING (auth.role() = 'authenticated');
CREATE POLICY "Allow all for authenticated" ON slot_history FOR ALL USING (auth.role() = 'authenticated');
CREATE POLICY "Allow all for authenticated" ON donations FOR ALL USING (auth.role() = 'authenticated');
CREATE POLICY "Allow all for authenticated" ON pending_donations FOR ALL USING (auth.role() = 'authenticated');
CREATE POLICY "Allow all for authenticated" ON snapshots FOR ALL USING (auth.role() = 'authenticated');
CREATE POLICY "Allow all for authenticated" ON reactions FOR ALL USING (auth.role() = 'authenticated');
CREATE POLICY "Allow all for authenticated" ON settings FOR ALL USING (auth.role() = 'authenticated');
CREATE POLICY "Allow all for authenticated" ON audit_logs FOR ALL USING (auth.role() = 'authenticated');

-- Policy: Allow anonymous read for overlay (public data)
CREATE POLICY "Allow public read" ON players FOR SELECT USING (true);
CREATE POLICY "Allow public read" ON rankings FOR SELECT USING (true);
CREATE POLICY "Allow public read" ON extra_games FOR SELECT USING (true);
CREATE POLICY "Allow public read" ON matches FOR SELECT USING (true);
CREATE POLICY "Allow public read" ON roulette_segments FOR SELECT USING (true);
CREATE POLICY "Allow public read" ON slot_items FOR SELECT USING (true);
CREATE POLICY "Allow public read" ON reactions FOR SELECT USING (true);
CREATE POLICY "Allow public read" ON settings FOR SELECT USING (true);

-- ============================================
-- REALTIME PUBLICATION
-- ============================================
ALTER PUBLICATION supabase_realtime ADD TABLE players;
ALTER PUBLICATION supabase_realtime ADD TABLE rankings;
ALTER PUBLICATION supabase_realtime ADD TABLE extra_games;
ALTER PUBLICATION supabase_realtime ADD TABLE matches;
ALTER PUBLICATION supabase_realtime ADD TABLE roulette_segments;
ALTER PUBLICATION supabase_realtime ADD TABLE slot_items;
ALTER PUBLICATION supabase_realtime ADD TABLE donations;
ALTER PUBLICATION supabase_realtime ADD TABLE pending_donations;
ALTER PUBLICATION supabase_realtime ADD TABLE snapshots;
ALTER PUBLICATION supabase_realtime ADD TABLE reactions;
ALTER PUBLICATION supabase_realtime ADD TABLE settings;

-- ============================================
-- TRIGGERS FOR updated_at
-- ============================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_players_updated_at BEFORE UPDATE ON players FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_extra_games_updated_at BEFORE UPDATE ON extra_games FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_matches_updated_at BEFORE UPDATE ON matches FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_roulette_segments_updated_at BEFORE UPDATE ON roulette_segments FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_slot_items_updated_at BEFORE UPDATE ON slot_items FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_donations_updated_at BEFORE UPDATE ON donations FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_reactions_updated_at BEFORE UPDATE ON reactions FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_settings_updated_at BEFORE UPDATE ON settings FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- HELPER FUNCTIONS
-- ============================================

-- Function to recalculate player ranks
CREATE OR REPLACE FUNCTION recalculate_ranks()
RETURNS VOID AS $$
DECLARE
  player_record RECORD;
  rank_counter INTEGER := 1;
BEGIN
  FOR player_record IN 
    SELECT id FROM players ORDER BY score DESC, contribution DESC
  LOOP
    UPDATE players 
    SET rank = rank_counter,
        badge = CASE 
          WHEN rank_counter = 1 THEN 'gold'
          WHEN rank_counter = 2 THEN 'silver'
          WHEN rank_counter = 3 THEN 'bronze'
          ELSE NULL
        END,
        updated_at = NOW()
    WHERE id = player_record.id;
    rank_counter := rank_counter + 1;
  END LOOP;
END;
$$ LANGUAGE plpgsql;

-- Function to calculate roulette angles
CREATE OR REPLACE FUNCTION calculate_roulette_angles()
RETURNS VOID AS $$
DECLARE
  segment_record RECORD;
  total_weight NUMERIC := 0;
  current_angle NUMERIC := -PI() / 2;
BEGIN
  -- Calculate total weight
  SELECT COALESCE(SUM(weight), 0) INTO total_weight 
  FROM roulette_segments WHERE is_active = TRUE;
  
  IF total_weight = 0 THEN RETURN; END IF;
  
  FOR segment_record IN
    SELECT id, weight FROM roulette_segments 
    WHERE is_active = TRUE 
    ORDER BY display_order
  LOOP
    DECLARE
      angle NUMERIC := (segment_record.weight / total_weight) * 2 * PI();
      start_angle NUMERIC := current_angle;
      end_angle NUMERIC := current_angle + angle;
      mid_angle NUMERIC := (start_angle + end_angle) / 2;
    BEGIN
      UPDATE roulette_segments
      SET start_angle = start_angle,
          end_angle = end_angle,
          mid_angle = mid_angle,
          updated_at = NOW()
      WHERE id = segment_record.id;
      
      current_angle := end_angle;
    END;
  END LOOP;
END;
$$ LANGUAGE plpgsql;

-- Function to create snapshot
CREATE OR REPLACE FUNCTION create_snapshot(p_label TEXT, p_created_by TEXT)
RETURNS UUID AS $$
DECLARE
  v_snapshot_id UUID;
  v_rankings JSONB;
  v_extra_games JSONB;
  v_matches JSONB;
  v_donations JSONB;
BEGIN
  -- Get current state
  SELECT jsonb_build_object(
    'leftColumn', left_column,
    'rightColumn', right_column,
    'bottomFixed', bottom_fixed
  ) INTO v_rankings FROM rankings ORDER BY created_at DESC LIMIT 1;
  
  SELECT jsonb_agg(to_jsonb(eg)) INTO v_extra_games FROM extra_games eg;
  SELECT jsonb_agg(to_jsonb(m)) INTO v_matches FROM matches m;
  SELECT jsonb_agg(to_jsonb(d)) INTO v_donations FROM donations d WHERE d.status != 'pending';
  
  INSERT INTO snapshots (label, rankings, extra_games, matches, donations, created_by)
  VALUES (p_label, v_rankings, v_extra_games, v_matches, v_donations, p_created_by)
  RETURNING id INTO v_snapshot_id;
  
  RETURN v_snapshot_id;
END;
$$ LANGUAGE plpgsql;

-- Function to cleanup old snapshots
CREATE OR REPLACE FUNCTION cleanup_old_snapshots()
RETURNS VOID AS $$
DECLARE
  v_max_snapshots INTEGER;
BEGIN
  SELECT (value->>0)::INTEGER INTO v_max_snapshots FROM settings WHERE key = 'max_snapshots';
  IF v_max_snapshots IS NULL THEN v_max_snapshots := 50; END IF;
  
  DELETE FROM snapshots
  WHERE id IN (
    SELECT id FROM snapshots
    ORDER BY created_at DESC
    OFFSET v_max_snapshots
  );
END;
$$ LANGUAGE plpgsql;