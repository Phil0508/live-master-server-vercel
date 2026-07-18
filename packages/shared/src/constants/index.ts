// Shared constants for Live Master Server

// Screen dimensions
export const SCREEN_WIDTH = 1080
export const SCREEN_HEIGHT = 1920
export const ASPECT_RATIO = SCREEN_WIDTH / SCREEN_HEIGHT // 9:16 vertical

// Animation durations (ms)
export const ANIMATION = {
  RANK_BOUNCE: 600,
  SCORE_PARTICLE: 800,
  EXTRA_GAME_SLIDE: 800,
  ROULETTE_SPIN_MIN: 4000,
  ROULETTE_SPIN_MAX: 8000,
  SLOT_SPIN: 3000,
  SLOT_DECELERATION: 1500,
  VIP_CARD_FADE_IN: 500,
  VIP_CARD_FADE_OUT: 1000,
  FEVER_BORDER_PULSE: 1000,
  BEEP_INTERVAL: 500,
  SNAPSHOT_FLASH: 300,
} as const

// Z-index layers
export const Z_INDEX = {
  BACKGROUND: 0,
  RANKING: 10,
  EXTRA_GAME: 20,
  MATCH_BOARD: 30,
  ROULETTE: 100,
  SLOT_MACHINE: 200,
  VIP_CARD: 300,
  FEVER_BORDER: 400,
  CONFETTI: 9999,
  TOAST: 10000,
} as const

// Colors
export const COLORS = {
  // Rank badges
  GOLD: '#FFD700',
  SILVER: '#C0C0C0',
  BRONZE: '#CD7F32',
  
  // VIP tiers
  VIP_GOLD: '#FFD700',
  VVIP_ROSE_GOLD: '#E8B4B8',
  
  // Neon colors
  NEON_CYAN: '#00FFFF',
  NEON_MAGENTA: '#FF00FF',
  NEON_GREEN: '#39FF14',
  NEON_ORANGE: '#FF6EC7',
  NEON_PURPLE: '#BC13FE',
  
  // Team colors
  RED_TEAM: '#FF3366',
  BLUE_TEAM: '#00D4FF',
  
  // Status colors
  SUCCESS: '#00E676',
  WARNING: '#FFD600',
  ERROR: '#FF1744',
  INFO: '#2979FF',
  
  // Backgrounds
  OVERLAY_BG: 'rgba(0, 0, 0, 0.85)',
  ROULETTE_BACKDROP: 'rgba(0, 0, 0, 0.95)',
  SLOT_BACKDROP: 'rgba(0, 0, 0, 0.98)',
  CONTROLLER_BG: '#0A0A0F',
  CARD_BG: 'rgba(20, 20, 30, 0.9)',
  CARD_BORDER: 'rgba(255, 255, 255, 0.1)',
} as const

// Fonts
export const FONTS = {
  ORBITRON: '"Orbitron", "sans-serif"',
  NANUM_GOTHIC: '"Nanum Gothic", "sans-serif"',
  JETBRAINS_MONO: '"JetBrains Mono", "monospace"',
} as const

// Audio
export const AUDIO = {
  MASTER_VOLUME: 0.7,
  BGM_VOLUME: 0.3,
  SFX_VOLUME: 0.8,
  CHIME_VOLUME: 1.0,
  BEEP_FREQUENCY: 880, // Hz (A5)
  BEEP_DURATION: 100, // ms
  
  // Sound effect URLs (to be configured)
  SOUNDS: {
    RANK_UP: '/sounds/rank-up.mp3',
    SCORE_PARTICLE: '/sounds/sparkle.mp3',
    EXTRA_GAME_SLIDE: '/sounds/slide.mp3',
    ROULETTE_TICK: '/sounds/tick.mp3',
    ROULETTE_WIN: '/sounds/win.mp3',
    SLOT_SPIN: '/sounds/slot-spin.mp3',
    SLOT_STOP: '/sounds/slot-stop.mp3',
    SLOT_JACKPOT: '/sounds/jackpot.mp3',
    VIP_CHIME: '/sounds/vip-chime.mp3',
    VVIP_CHIME: '/sounds/vvip-chime.mp3',
    FEVER_BEEP: '/sounds/beep.mp3',
    DONATION_CHIME: '/sounds/donation-chime.mp3',
    SNAPSHOT: '/sounds/snapshot.mp3',
    CONFETTI: '/sounds/confetti.mp3',
  } as const,
} as const

// WebSocket event types
export const WS_EVENTS = {
  // Ranking
  'ranking:update': 'ranking:update',
  'ranking:score-change': 'ranking:score-change',
  'ranking:reorder': 'ranking:reorder',
  
  // Extra Game
  'extra-game:toggle': 'extra-game:toggle',
  'extra-game:update': 'extra-game:update',
  'extra-game:score-change': 'extra-game:score-change',
  
  // Match
  'match:start': 'match:start',
  'match:update': 'match:update',
  'match:end': 'match:end',
  'match:countdown': 'match:countdown',
  'match:fever-start': 'match:fever-start',
  'match:fever-end': 'match:fever-end',
  
  // Roulette
  'roulette:spin': 'roulette:spin',
  'roulette:rig': 'roulette:rig',
  'roulette:result': 'roulette:result',
  
  // Slot Machine
  'slot:spin': 'slot:spin',
  'slot:result': 'slot:result',
  
  // Donations
  'donation:new': 'donation:new',
  'donation:approve': 'donation:approve',
  'donation:split': 'donation:split',
  'donation:distribute': 'donation:distribute',
  'donation:update': 'donation:update',
  
  // Lighting
  'lighting:update': 'lighting:update',
  'lighting:vip-color': 'lighting:vip-color',
  'lighting:audi-chase': 'lighting:audi-chase',
  
  // Audio
  'audio:play': 'audio:play',
  'audio:pause': 'audio:pause',
  'audio:volume': 'audio:volume',
  'audio:sync': 'audio:sync',
  
  // Snapshots
  'snapshot:create': 'snapshot:create',
  'snapshot:restore': 'snapshot:restore',
  'snapshot:list': 'snapshot:list',
  'snapshot:delete': 'snapshot:delete',
  
  // Controller actions
  'controller:ping': 'controller:ping',
  'controller:pong': 'controller:pong',
  'controller:sync-request': 'controller:sync-request',
  'controller:sync-response': 'controller:sync-response',
} as const

// API endpoints (for Supabase Edge Functions)
export const API_ENDPOINTS = {
  WEBHOOK_TOONATION: '/functions/v1/webhook-toonation',
  ROULETTE_SPIN: '/functions/v1/roulette-spin',
  ROULETTE_RIG: '/functions/v1/roulette-rig',
  SNAPSHOT_CREATE: '/functions/v1/snapshot-create',
  REACTION_UPLOAD: '/functions/v1/reaction-upload',
  LEADERBOARD: '/functions/v1/leaderboard',
} as const

// Database table names
export const TABLES = {
  PLAYERS: 'players',
  RANKINGS: 'rankings',
  EXTRA_GAMES: 'extra_games',
  MATCHES: 'matches',
  ROULETTE_SEGMENTS: 'roulette_segments',
  ROULETTE_HISTORY: 'roulette_history',
  SLOT_ITEMS: 'slot_items',
  SLOT_HISTORY: 'slot_history',
  DONATIONS: 'donations',
  PENDING_DONATIONS: 'pending_donations',
  SNAPSHOTS: 'snapshots',
  REACTIONS: 'reactions',
  SETTINGS: 'settings',
  AUDIT_LOGS: 'audit_logs',
} as const

// Supabase Realtime channels
export const REALTIME_CHANNELS = {
  OVERLAY: 'overlay-updates',
  CONTROLLER: 'controller-commands',
  DONATIONS: 'donations',
  RANKINGS: 'rankings',
  MATCHES: 'matches',
  ROULETTE: 'roulette',
  SLOTS: 'slots',
  LIGHTING: 'lighting',
  AUDIO: 'audio',
  SNAPSHOTS: 'snapshots',
  SYSTEM: 'system-events',
} as const

// LocalStorage keys
export const STORAGE_KEYS = {
  CONTROLLER_LAYOUT: 'controller-layout',
  OVERLAY_SETTINGS: 'overlay-settings',
  AUDIO_PREFERENCES: 'audio-preferences',
  LIGHTING_PRESETS: 'lighting-presets',
  LAST_SNAPSHOT: 'last-snapshot',
  VIP_COLOR_CACHE: 'vip-color-cache',
} as const

// Default values
export const DEFAULTS = {
  PLAYER_INITIAL_SCORE: 0,
  PLAYER_INITIAL_CONTRIBUTION: 0,
  RANKING_COLUMN_COUNT: 2,
  MAX_PLAYERS_PER_COLUMN: 10,
  MATCH_DEFAULT_DURATION: 300, // 5 minutes
  FEVER_TIME_THRESHOLD: 60, // seconds
  ROULETTE_MIN_SEGMENTS: 3,
  ROULETTE_MAX_SEGMENTS: 20,
  SLOT_REEL_COUNT: 3,
  SLOT_ITEMS_PER_REEL: 12,
  DONATION_MIN_AMOUNT: 1000,
  VIP_MIN_AMOUNT: 50000,
  VVIP_MIN_AMOUNT: 200000,
  SNAPSHOT_MAX_COUNT: 50,
  AUDIO_SYNC_INTERVAL: 1000, // ms
} as const

// Regex patterns
export const PATTERNS = {
  YOUTUBE_URL: /^(https?:\/\/)?(www\.)?(youtube\.com|youtu\.be)\/.+$/,
  IMAGE_URL: /\.(jpg|jpeg|png|gif|webp)(\?.*)?$/i,
  AUDIO_URL: /\.(mp3|wav|ogg|m4a)(\?.*)?$/i,
  HEX_COLOR: /^#[0-9A-Fa-f]{6}$/,
  HSL_COLOR: /^hsl\(\s*\d+\s*,\s*\d+%\s*,\s*\d+%\s*\)$/,
} as const

// Feature flags
export const FEATURES = {
  ROULETTE_RIGGING: true,
  SLOT_MACHINE: true,
  VIP_LIGHTING_SYNC: true,
  TIME_MACHINE: true,
  AUDIO_SYNC: true,
  MULTI_CONTROLLER: false, // Future: multiple controllers
  MOBILE_CONTROLLER: true,
  STREAM_DECK_INTEGRATION: false, // Future
} as const