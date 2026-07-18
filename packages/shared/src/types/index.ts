// Core domain types for Live Master Server

// User & Player types
export interface Player {
  id: string
  name: string
  score: number
  contribution: number
  rank: number
  badge?: 'gold' | 'silver' | 'bronze' | null
  isVip?: boolean
  isVvip?: boolean
  createdAt: Date
  updatedAt: Date
}

export interface VipPlayer extends Player {
  vipTier: 'vip' | 'vvip'
  crownEffect: string
  neonColor: string
  audioChime: string
}

// Ranking & Leaderboard types
export interface RankingColumn {
  id: string
  title: string
  players: Player[]
}

export interface RankingData {
  leftColumn: RankingColumn
  rightColumn: RankingColumn
  bottomFixed: ExcelBottomRow
}

export interface ExcelBottomRow {
  id: 'excel-bottom-fixed'
  label: '방송 운영비 정산'
  totalScore: number
  totalContribution: number
  operatingCost: number
  netProfit: number
}

// Extra Game (Mini-game) types
export interface ExtraGamePlayer {
  id: string
  name: string
  score: number
  gameType: 'pokemon' | 'pokemon-pack' | 'go-stop' | 'off-work' | 'custom' | string
  isActive: boolean
  isWinner?: boolean
  scoreChange?: number
  penaltyCount?: number
  contribution?: number
}

export interface ExtraGameState {
  isVisible: boolean
  gameType: 'pokemon' | 'pokemon-pack' | 'go-stop' | 'off-work' | 'custom' | string | null
  players: ExtraGamePlayer[]
  slidePosition: 'hidden' | 'sliding-in' | 'visible' | 'sliding-out'
  currentRound?: number
  totalRounds?: number
  firstPrize?: string
  penalty?: string
  totalPot?: number
}

export type ExtraGameData = ExtraGameState

// Match (1v1/Team Deathmatch) types
export interface MatchTeam {
  id: 'red' | 'blue'
  name: string
  score: number
  players: Player[]
  neonColor: string
  shieldEffect: boolean
}

export interface MatchData {
  teamA: MatchTeam
  teamB: MatchTeam
  timer: number
  isFeverTime: boolean
  matchType: '1v1' | 'team' | 'custom'
}

export interface MatchState {
  isActive: boolean
  teams: [MatchTeam, MatchTeam]
  countdown: number // seconds
  isFeverTime: boolean
  feverBorderActive: boolean
  beepSoundActive: boolean
}

// Roulette types
export interface RouletteSegment {
  id: string
  label: string
  weight: number // contribution-based weight
  color: string
  isCustomPunishment?: boolean
  playerId?: string
}

export interface RouletteState {
  isSpinning: boolean
  segments: RouletteSegment[]
  winnerId?: string
  winnerLabel?: string
  winner_name?: string
  riggedTargetId?: string // For "Election Commission" rigging
  riggedAngle?: number
}

// Slot Machine types
export interface SlotReel {
  id: number
  items: SlotItem[]
  currentIndex: number
  isSpinning: boolean
  targetIndex?: number
}

export interface SlotItem {
  id: string
  imageUrl: string
  label: string
  reactionAmount: number
  probability: number
}

export interface SlotMachineState {
  isActive: boolean
  reels: SlotReel[]
  result?: SlotResult
  confettiActive: boolean
  status?: string
}

export interface SlotResult {
  matchedItem: SlotItem
  isJackpot: boolean
  message: string
}

// Donation & Reaction types
export interface Donation {
  id: string
  donorName: string
  amount: number
  message?: string
  reactionId?: string
  reactionImageUrl?: string
  timestamp: Date
  status: 'pending' | 'approved' | 'split' | 'distributed'
  splitType?: 'full' | 'half' | 'split-n'
  splitTargets?: string[] // player IDs
}

export interface PendingDonation extends Donation {
  status: 'pending'
}

export interface ApprovedDonation extends Donation {
  status: 'approved' | 'split' | 'distributed'
  processedAt: Date
  processedBy: string
}

// Audio & Media types
export interface AudioTrack {
  id: string
  title: string
  url: string
  volume: number
  isPlaying: boolean
  duration: number
  currentTime: number
}

export interface MediaState {
  youtubeBgm: AudioTrack | null
  localAudio: AudioTrack[]
  masterVolume: number
}

// Lighting & Effects types
export interface NeonColor {
  h: number
  s: number
  l: number
  hex: string
}

export interface LightingState {
  borderNeonColor: NeonColor
  audiLightChaseSpeed: number
  isChaseActive: boolean
  dominantColorSource: 'vip-image' | 'manual' | 'default'
}

// Snapshot / Time Machine types
export interface ScoreSnapshot {
  id: string
  timestamp: Date
  label: string
  rankings: RankingData
  extraGames: ExtraGameState
  matches: MatchState
  donations: Donation[]
  createdBy: string
}

export interface TimeMachineState {
  snapshots: ScoreSnapshot[]
  currentSnapshotId?: string
  canRollback: boolean
}

// WebSocket / Real-time types
export interface RealtimeEvent<T = unknown> {
  type: string
  payload: T
  timestamp: Date
  source: 'overlay' | 'controller' | 'server'
}

export interface ServerToClientEvents {
  'ranking:update': RankingData
  'extra-game:update': ExtraGameState
  'match:update': MatchState
  'roulette:spin': { segments: RouletteSegment[]; targetAngle?: number }
  'roulette:result': { winnerId: string; winnerLabel: string }
  'slot:spin': SlotMachineState
  'slot:result': SlotResult
  'donation:new': PendingDonation
  'donation:update': Donation
  'lighting:update': LightingState
  'audio:update': MediaState
  'snapshot:created': ScoreSnapshot
  'snapshot:restored': ScoreSnapshot
}

export interface ClientToServerEvents {
  'controller:ranking:update': Partial<RankingData>
  'controller:extra-game:toggle': { isVisible: boolean; gameType?: string }
  'controller:match:start': { teams: [MatchTeam, MatchTeam]; duration: number }
  'controller:roulette:spin': { segments: RouletteSegment[]; riggedTargetId?: string }
  'controller:slot:spin': { reels: SlotReel[] }
  'controller:donation:approve': { donationId: string; splitType: Donation['splitType']; targets?: string[] }
  'controller:lighting:set': LightingState
  'controller:audio:control': Partial<MediaState>
  'controller:snapshot:create': { label: string }
  'controller:snapshot:restore': { snapshotId: string }
}

// JSON type for Supabase
export type Json = string | number | boolean | null | { [key: string]: Json } | Json[];

// Utility types
export type DeepPartial<T> = {
  [P in keyof T]?: DeepPartial<T[P]>
}

export type SlotMachineData = SlotMachineState
export type RouletteData = RouletteState
export type RankingBottomFixed = ExcelBottomRow

export interface VIPData {
  id: string
  name: string
  donor_name?: string
  username?: string
  amount: number
  tier: 'vip' | 'vvip'
  message?: string
  crownEffect?: string
  neonColor?: string
  audioChime?: string
}

export interface Database {
  public: {
    Tables: Record<string, any>
    Views: Record<string, any>
    Functions: Record<string, any>
  }
}

export type Optional<T, K extends keyof T> = Omit<T, K> & Partial<Pick<T, K>>

export type RequiredFields<T, K extends keyof T> = T & Required<Pick<T, K>>