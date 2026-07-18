import { serve } from "https://deno.land/std@0.168.0/http/server.ts"
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2.39.0'

// CORS 헤더 설정
const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
  'Access-Control-Allow-Methods': 'POST, OPTIONS',
}

// 요청 본문 타입 정의
interface RecalcRequest {
  trigger?: 'manual' | 'donation' | 'match_end' | 'extra_game' | 'snapshot_restore' | 'scheduled'
  player_ids?: string[]  // 특정 플레이어만 재계산 (선택)
  snapshot_id?: string   // 스냅샷 복원 후 재계산 시
}

interface RecalcResponse {
  success: boolean
  message: string
  updated_count: number
  rankings: {
    left_column_count: number
    right_column_count: number
    bottom_fixed: {
      total_score: number
      total_contribution: number
      operating_cost: number
      net_profit: number
    }
  }
  timestamp: string
  triggered_by: string
}

// 랭킹 재계산 메인 함수
async function recalculateRankings(
  supabase: any,
  options: { player_ids?: string[] } = {}
): Promise<{ updated_count: number; rankings: any }> {
  const { player_ids } = options

  // 1. 대상 플레이어 조회 (점수+기여도 내림차순)
  let query = supabase
    .from('players')
    .select('id, name, score, contribution')
    .order('score', { ascending: false })
    .order('contribution', { ascending: false })

  if (player_ids && player_ids.length > 0) {
    query = query.in('id', player_ids)
  }

  const { data: players, error: playersError } = await query

  if (playersError) {
    throw new Error(`플레이어 조회 실패: ${playersError.message}`)
  }

  if (!players || players.length === 0) {
    return { updated_count: 0, rankings: { left_column_count: 0, right_column_count: 0, bottom_fixed: { total_score: 0, total_contribution: 0, operating_cost: 0, net_profit: 0 } } }
  }

  // 2. 순위 및 배지 계산
  const updates = players.map((player: any, index: number) => {
    const rank = index + 1
    let badge: 'gold' | 'silver' | 'bronze' | null = null
    if (rank === 1) badge = 'gold'
    else if (rank === 2) badge = 'silver'
    else if (rank === 3) badge = 'bronze'

    return {
      id: player.id,
      rank,
      badge,
      updated_at: new Date().toISOString()
    }
  })

  // 3. 배치 업데이트 (트랜잭션으로 처리)
  const { error: updateError } = await supabase.rpc('batch_update_players_rank', {
    updates: updates
  })

  if (updateError) {
    // RPC 함수가 없으면 개별 업데이트로 폴백
    console.warn('RPC 함수 없음, 개별 업데이트로 폴백:', updateError.message)
    
    for (const update of updates) {
      const { error } = await supabase
        .from('players')
        .update({ rank: update.rank, badge: update.badge, updated_at: update.updated_at })
        .eq('id', update.id)
      
      if (error) {
        console.error(`플레이어 ${update.id} 업데이트 실패:`, error.message)
      }
    }
  }

  // 4. 랭킹 스냅샷 생성 (좌/우 컬럼 분배 + 하단 고정행)
  const leftColumnPlayers = players.slice(0, 8)
  const rightColumnPlayers = players.slice(8, 16)

  const totalScore = players.reduce((sum: number, p: any) => sum + p.score, 0)
  const totalContribution = players.reduce((sum: number, p: any) => sum + p.contribution, 0)

  // 운영비 설정 조회
  const { data: settings } = await supabase
    .from('settings')
    .select('value')
    .eq('key', 'operating_cost')
    .single()

  const operatingCost = settings?.value || 100000
  const netProfit = totalContribution - operatingCost

  const rankingSnapshot = {
    left_column: {
      id: 'left',
      title: '좌측 랭킹',
      players: leftColumnPlayers.map((p: any, i: number) => ({
        ...p,
        rank: i + 1
      }))
    },
    right_column: {
      id: 'right',
      title: '우측 랭킹',
      players: rightColumnPlayers.map((p: any, i: number) => ({
        ...p,
        rank: i + 9
      }))
    },
    bottom_fixed: {
      id: 'excel-bottom-fixed',
      label: '방송 운영비 정산',
      total_score: totalScore,
      total_contribution: totalContribution,
      operating_cost: operatingCost,
      net_profit: netProfit
    }
  }

  // 5. rankings 테이블에 새 스냅샷 저장
  const { data: rankingRecord, error: rankingError } = await supabase
    .from('rankings')
    .insert({
      left_column: rankingSnapshot.left_column,
      right_column: rankingSnapshot.right_column,
      bottom_fixed: rankingSnapshot.bottom_fixed
    })
    .select()
    .single()

  if (rankingError) {
    throw new Error(`랭킹 스냅샷 저장 실패: ${rankingError.message}`)
  }

  // 6. 실시간 이벤트 발행 (Supabase Realtime)
  await supabase.channel('ranking-updates').send({
    type: 'broadcast',
    event: 'ranking:update',
    payload: rankingSnapshot
  })

  return {
    updated_count: players.length,
    rankings: {
      left_column_count: leftColumnPlayers.length,
      right_column_count: rightColumnPlayers.length,
      bottom_fixed: rankingSnapshot.bottom_fixed
    }
  }
}

// 감사 로그 기록
async function logAudit(
  supabase: any,
  action: string,
  entityType: string,
  entityId: string | null,
  performedBy: string,
  details: Record<string, any>
) {
  await supabase.from('audit_logs').insert({
    action,
    entity_type: entityType,
    entity_id: entityId,
    new_data: details,
    performed_by: performedBy,
    ip_address: null, // Edge Function에서는 IP 추출 제한적
    user_agent: 'supabase-edge-function'
  })
}

// 메인 핸들러
serve(async (req: Request) => {
  // CORS preflight 처리
  if (req.method === 'OPTIONS') {
    return new Response('ok', { headers: corsHeaders })
  }

  // POST 메서드만 허용
  if (req.method !== 'POST') {
    return new Response(
      JSON.stringify({ error: 'Method not allowed' }),
      { status: 405, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )
  }

  try {
    // Supabase 클라이언트 생성 (Service Role Key 사용)
    const supabaseUrl = Deno.env.get('SUPABASE_URL')!
    const supabaseServiceKey = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!
    
    const supabase = createClient(supabaseUrl, supabaseServiceKey, {
      auth: { persistSession: false }
    })

    // 요청 본문 파싱
    const body: RecalcRequest = await req.json().catch(() => ({}))
    const { trigger = 'manual', player_ids, snapshot_id } = body

    // 인증 헤더에서 사용자 정보 추출
    const authHeader = req.headers.get('Authorization')
    let triggeredBy = 'system'
    let userRole = 'admin'

    if (authHeader) {
      // JWT 토큰에서 사용자 정보 추출 (실제로는 Supabase Auth 검증 필요)
      const token = authHeader.replace('Bearer ', '')
      try {
        const { data: { user }, error } = await supabase.auth.getUser(token)
        if (!error && user) {
          triggeredBy = user.id
          // user_roles 테이블에서 역할 조회
          const { data: roles } = await supabase
            .from('user_roles')
            .select('role')
            .eq('user_id', user.id)
            .eq('is_active', true)
            .single()
          userRole = roles?.role || 'controller'
        }
      } catch (e) {
        console.warn('토큰 검증 실패, 시스템 계정으로 처리:', e.message)
      }
    }

    console.log(`[Ranking Recalc] Trigger: ${trigger}, By: ${triggeredBy} (${userRole})`)

    // 스냅샷 복원 후 재계산인 경우
    if (snapshot_id) {
      const { data: snapshot, error: snapError } = await supabase
        .from('snapshots')
        .select('*')
        .eq('id', snapshot_id)
        .single()

      if (snapError || !snapshot) {
        throw new Error(`스냅샷을 찾을 수 없음: ${snapshot_id}`)
      }

      // 스냅샷에서 플레이어 데이터 복원 후 재계산
      // (실제 구현에서는 스냅샷 데이터를 players 테이블에 복원하는 로직 필요)
      console.log(`[Ranking Recalc] Snapshot restore triggered: ${snapshot.label}`)
    }

    // 랭킹 재계산 실행
    const result = await recalculateRankings(supabase, { player_ids })

    // 감사 로그 기록
    await logAudit(supabase, 'ranking_recalculate', 'ranking', null, triggeredBy, {
      trigger,
      updated_count: result.updated_count,
      snapshot_id,
      player_ids: player_ids || 'all',
      rankings: result.rankings
    })

    const response: RecalcResponse = {
      success: true,
      message: `랭킹 재계산 완료 (${result.updated_count}명 업데이트)`,
      updated_count: result.updated_count,
      rankings: result.rankings,
      timestamp: new Date().toISOString(),
      triggered_by: triggeredBy
    }

    return new Response(
      JSON.stringify(response),
      { status: 200, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )

  } catch (error) {
    console.error('[Ranking Recalc] Error:', error)

    const errorResponse = {
      success: false,
      message: error instanceof Error ? error.message : '알 수 없는 오류',
      updated_count: 0,
      rankings: null,
      timestamp: new Date().toISOString(),
      triggered_by: 'system'
    }

    return new Response(
      JSON.stringify(errorResponse),
      { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )
  }
})

/*
배포 방법:
1. Supabase CLI 설치: npm install -g supabase
2. 로그인: supabase login
3. 프로젝트 연결: supabase link --project-ref YOUR_PROJECT_REF
4. 배포: supabase functions deploy ranking-recalc

로컬 테스트:
supabase functions serve ranking-recalc --env-file .env.local

호출 예시 (Controller에서):
const response = await fetch(`${SUPABASE_URL}/functions/v1/ranking-recalc`, {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${SUPABASE_ANON_KEY}`,
    'Content-Type': 'application/json',
    'apikey': SUPABASE_ANON_KEY
  },
  body: JSON.stringify({ 
    trigger: 'donation', 
    player_ids: ['player-uuid-1', 'player-uuid-2'] 
  })
})
*/

/*
필요한 데이터베이스 함수 (schema.sql에 추가 권장):

-- 배치 업데이트용 RPC 함수
CREATE OR REPLACE FUNCTION batch_update_players_rank(updates JSONB)
RETURNS VOID LANGUAGE plpgsql AS $$
DECLARE
  update_item JSONB;
BEGIN
  FOR update_item IN SELECT * FROM jsonb_array_elements(updates)
  LOOP
    UPDATE players
    SET rank = (update_item->>'rank')::INTEGER,
        badge = (update_item->>'badge'),
        updated_at = (update_item->>'updated_at')::TIMESTAMPTZ
    WHERE id = (update_item->>'id')::UUID;
  END LOOP;
END;
$$;

-- 운영비 설정 기본값
INSERT INTO settings (key, value, description) VALUES
('operating_cost', '100000', '방송 운영비 (원)')
ON CONFLICT (key) DO NOTHING;
*/