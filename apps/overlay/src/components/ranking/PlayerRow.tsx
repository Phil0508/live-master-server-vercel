import React from 'react'
import { motion } from 'framer-motion'
import type { Player } from '@live-master/shared/types'

interface PlayerRowProps {
  player: Player
  index: number
  animation: 'spark' | 'bounce' | 'idle'
}

const badgeMap: Record<string, string> = {
  gold: '🥇',
  silver: '🥈',
  bronze: '🥉',
}

const rankColors = [
  '#FFD700', // 1위 - 골드
  '#C0C0C0', // 2위 - 실버
  '#CD7F32', // 3위 - 브론즈
  '#FFFFFF', // 4위 이상
]

export function PlayerRow({ player, index, animation }: PlayerRowProps) {
  const rank = index + 1
  const badge = badgeMap[player.badge || '']
  const rankColor = rankColors[Math.min(rank - 1, rankColors.length - 1)]

  const rowStyle: React.CSSProperties = {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
    padding: '10px 16px',
    background: 'rgba(0, 20, 40, 0.85)',
    border: `1px solid rgba(${rank <= 3 ? rankColor.replace('#', '') : '0,212,255'}, 0.4)`,
    borderRadius: '12px',
    backdropFilter: 'blur(10px)',
    boxShadow: rank <= 3 
      ? `0 0 30px ${rankColor}80, inset 0 1px 0 rgba(255,255,255,0.1)`
      : '0 4px 20px rgba(0,0,0,0.3)',
    transition: 'all 0.3s ease',
    minWidth: 0,
  }

  const rankBadgeStyle: React.CSSProperties = {
    width: '44px',
    height: '44px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: '20px',
    fontWeight: '900',
    color: rank <= 3 ? '#000' : '#FFF',
    background: rank <= 3 
      ? `linear-gradient(135deg, ${rankColor}, ${rankColor}CC)`
      : 'linear-gradient(135deg, #1a2a4a, #0d1a2f)',
    borderRadius: '50%',
    boxShadow: rank <= 3 
      ? `0 0 20px ${rankColor}, inset 0 -2px 4px rgba(0,0,0,0.3)`
      : 'inset 0 2px 4px rgba(0,0,0,0.4)',
    border: rank <= 3 ? `2px solid ${rankColor}` : '1px solid rgba(255,255,255,0.1)',
    flexShrink: 0,
  }

  const nameStyle: React.CSSProperties = {
    flex: 1,
    fontSize: '20px',
    fontWeight: '700',
    color: '#FFF',
    textShadow: '0 0 10px rgba(0,212,255,0.5)',
    whiteSpace: 'nowrap',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    fontFamily: '"Noto Sans KR", sans-serif',
  }

  const scoreStyle: React.CSSProperties = {
    fontSize: '18px',
    fontWeight: '800',
    color: rank <= 3 ? rankColor : '#00D4FF',
    textShadow: `0 0 15px ${rank <= 3 ? rankColor : '#00D4FF'}`,
    fontFamily: '"Orbitron", monospace',
    fontVariantNumeric: 'tabular-nums',
    minWidth: '100px',
    textAlign: 'right',
  }

  const contributionStyle: React.CSSProperties = {
    fontSize: '14px',
    fontWeight: '600',
    color: '#FF6B9D',
    textShadow: '0 0 10px rgba(255,107,157,0.5)',
    fontFamily: '"Orbitron", monospace',
    fontVariantNumeric: 'tabular-nums',
    minWidth: '80px',
    textAlign: 'right',
  }

  // 애니메이션 변형
  const animateProps = animation === 'spark' ? {
    scale: [1, 1.05, 1],
    boxShadow: [
      rank <= 3 ? `0 0 30px ${rankColor}80` : '0 4px 20px rgba(0,0,0,0.3)',
      rank <= 3 ? `0 0 50px ${rankColor}CC, inset 0 1px 0 rgba(255,255,255,0.2)` : '0 8px 40px rgba(0,0,0,0.4)',
      rank <= 3 ? `0 0 30px ${rankColor}80` : '0 4px 20px rgba(0,0,0,0.3)',
    ],
    transition: { duration: 0.6, ease: 'easeOut' },
  } : animation === 'bounce' ? {
    y: [0, -10, 0],
    transition: { duration: 0.5, ease: 'easeOut' },
  } : {}

  return (
    <motion.div
      style={rowStyle}
      animate={animateProps}
      className="player-row"
    >
      {/* 순위 배지 + 메달 */}
      <div style={rankBadgeStyle}>
        {badge || rank}
      </div>

      {/* 플레이어 이름 */}
      <div style={nameStyle}>{player.name}</div>

      {/* 점수 */}
      <div style={scoreStyle}>
        {player.score.toLocaleString()}
      </div>

      {/* 기여도 */}
      <div style={contributionStyle}>
        +{player.contribution.toLocaleString()}
      </div>
    </motion.div>
  )
}