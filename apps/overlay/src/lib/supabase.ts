import { createClient } from '@supabase/supabase-js'
import type { Database } from '@live-master/shared/types'

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY

if (!supabaseUrl || !supabaseAnonKey) {
  throw new Error('Supabase 환경 변수가 설정되지 않았습니다. VITE_SUPABASE_URL, VITE_SUPABASE_ANON_KEY를 확인하세요.')
}

export const supabase = createClient<Database>(supabaseUrl, supabaseAnonKey, {
  auth: {
    persistSession: false,
    autoRefreshToken: false,
  },
  realtime: {
    params: {
      eventsPerSecond: 10,
    },
  },
})

export function initializeSupabase() {
  console.log('[Overlay] Supabase Realtime 클라이언트가 초기화되었습니다.')
  return supabase
}

// 타입 안전한 채널 구독 헬퍼
export function subscribeToRankings(callback: (payload: any) => void) {
  return supabase
    .channel('ranking-updates')
    .on(
      'broadcast',
      { event: 'ranking:update' },
      (payload) => callback(payload.payload)
    )
    .subscribe()
}

export function subscribeToDonations(callback: (payload: any) => void) {
  return supabase
    .channel('donation-events')
    .on(
      'broadcast',
      { event: 'donation:new' },
      (payload) => callback(payload.payload)
    )
    .subscribe()
}

export function subscribeToRoulette(callback: (payload: any) => void) {
  return supabase
    .channel('roulette-events')
    .on(
      'broadcast',
      { event: 'roulette:spin' },
      (payload) => callback(payload.payload)
    )
    .on(
      'broadcast',
      { event: 'roulette:result' },
      (payload) => callback(payload.payload)
    )
    .subscribe()
}

export function subscribeToMatch(callback: (payload: any) => void) {
  return supabase
    .channel('match-events')
    .on(
      'broadcast',
      { event: 'match:update' },
      (payload) => callback(payload.payload)
    )
    .on(
      'broadcast',
      { event: 'match:timer' },
      (payload) => callback(payload.payload)
    )
    .subscribe()
}

export function subscribeToVIP(callback: (payload: any) => void) {
  return supabase
    .channel('vip-events')
    .on(
      'broadcast',
      { event: 'vip:donation' },
      (payload) => callback(payload.payload)
    )
    .subscribe()
}