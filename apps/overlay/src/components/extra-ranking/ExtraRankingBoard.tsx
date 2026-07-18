import React from 'react'
import { motion } from 'framer-motion'
import type { ExtraGameData, ExtraGamePlayer } from '@live-master/shared/types'

interface ExtraRankingBoardProps {
  data: ExtraGameData | null
}

const gameTypeLabels: Record<string, { label: string; color: string; icon: string }> = {
  'pokemon-pack': { label: '포켓몬 카드깡', color: '#FFD700', icon: '🃏' },
  'go-stop': { label: '고앤스톱', color: '#FF6B35', icon: '🎴' },
  'custom': { label: '커스텀 게임', color: '#00D4FF', icon: '🎮' },
}

const playerRowStyle: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: '16px',
  padding: '16px 24px',
  background: 'rgba(0, 20, 40, 0.9)',
  border: '1px solid rgba(255,215,0,0.3)',
  borderRadius: '16px',
  backdropFilter: 'blur(15px)',
  boxShadow: '0 8px 32px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.1)',
  minWidth: 0,
}

export function ExtraRankingBoard({ data }: ExtraRankingBoardProps) {
  if (!data) return null

  const gameTypeKey = data?.gameType || 'custom'
  const gameInfo = gameTypeLabels[gameTypeKey] || gameTypeLabels.custom
  const sortedPlayers = [...(data?.players || [])].sort((a, b) => b.score - a.score)

  const containerStyle: React.CSSProperties = {
    position: 'absolute',
    top: 0,
    left: 0,
    width: '1080px',
    height: '1920px',
    background: 'linear-gradient(135deg, rgba(0,10,20,0.98), rgba(0,20,40,0.95))',
    border: '3px solid rgba(255,215,0,0.5)',
    borderRadius: '24px',
    boxShadow: '0 0 80px rgba(255,215,0,0.3), inset 0 1px 0 rgba(255,255,255,0.1)',
    backdropFilter: 'blur(20px)',
    display: 'flex',
    flexDirection: 'column',
    padding: '40px 60px',
    pointerEvents: 'auto',
    overflow: 'hidden',
  }

  const headerStyle: React.CSSProperties = {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: '32px',
    paddingBottom: '24px',
    borderBottom: '2px solid rgba(255,215,0,0.3)',
  }

  const titleStyle: React.CSSProperties = {
    display: 'flex',
    alignItems: 'center',
    gap: '16px',
    fontSize: '36px',
    fontWeight: '900',
    fontFamily: '"Orbitron", "Noto Sans KR", sans-serif',
    background: `linear-gradient(135deg, ${gameInfo.color}, #FFF)`,
    backgroundClip: 'text',
    WebkitBackgroundClip: 'text',
    WebkitTextFillColor: 'transparent',
    textShadow: `0 0 40px ${gameInfo.color}80`,
  }

  const closeButtonStyle: React.CSSProperties = {
    width: '56px',
    height: '56px',
    borderRadius: '50%',
    background: 'rgba(255,0,0,0.2)',
    border: '2px solid rgba(255,0,0,0.5)',
    color: '#FF4444',
    fontSize: '24px',
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    transition: 'all 0.2s ease',
    backdropFilter: 'blur(10px)',
  }

  const playersListStyle: React.CSSProperties = {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    gap: '16px',
    overflowY: 'auto',
    paddingRight: '8px',
  }

  const footerStyle: React.CSSProperties = {
    display: 'flex',
    justifyContent: 'space-between',
    paddingTop: '24px',
    borderTop: '2px solid rgba(255,215,0,0.3)',
    marginTop: 'auto',
  }

  const prizeStyle: React.CSSProperties = {
    fontSize: '18px',
    fontWeight: '700',
    fontFamily: '"Orbitron", monospace',
    color: gameInfo.color,
    textShadow: `0 0 20px ${gameInfo.color}80`,
  }

  return (
    <motion.div
      style={containerStyle}
      initial={{ scale: 0.95, opacity: 0 }}
      animate={{ scale: 1, opacity: 1 }}
      transition={{ type: 'spring', stiffness: 150, damping: 20 }}
      className="extra-ranking-board"
    >
      {/* 반짝이는 테두리 애니메이션 */}
      <div style={{
        position: 'absolute',
        inset: '-3px',
        borderRadius: '27px',
        background: `conic-gradient(from 0deg, ${gameInfo.color}, transparent 50%, ${gameInfo.color})`,
        animation: 'rotateBorder 4s linear infinite',
        zIndex: -1,
        filter: 'blur(8px)',
        opacity: 0.5,
      }}>
        <style>{`
          @keyframes rotateBorder {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
          }
        `}</style>
      </div>

      {/* 헤더 */}
      <div style={headerStyle}>
        <div style={titleStyle}>
          <span style={{ fontSize: '40px' }}>{gameInfo.icon}</span>
          {gameInfo.label}
          {data.currentRound !== undefined && (
            <span style={{ 
              fontSize: '20px', 
              fontWeight: '600',
              opacity: 0.8,
              marginLeft: '16px',
              padding: '4px 12px',
              background: `rgba(${gameInfo.color.replace('#', '')}, 0.2)`,
              borderRadius: '8px',
            }}>
              {data.currentRound} / {data.totalRounds} 라운드
            </span>
          )}
        </div>
        <button 
          style={closeButtonStyle}
          onClick={() => window.dispatchEvent(new CustomEvent('overlay:close-extra-ranking'))}
          onMouseEnter={(e) => e.currentTarget.style.background = 'rgba(255,0,0,0.4)'}
          onMouseLeave={(e) => e.currentTarget.style.background = 'rgba(255,0,0,0.2)'}
          aria-label="번외 게임 닫기"
        >
          ✕
        </button>
      </div>

      {/* 플레이어 리스트 */}
      <div style={playersListStyle}>
        {sortedPlayers.map((player, index) => (
          <ExtraPlayerRow 
            key={player.id} 
            player={player} 
            rank={index + 1}
            gameColor={gameInfo.color}
          />
        ))}
      </div>

      {/* 푸터 - 상금/벌칙 정보 */}
      <div style={footerStyle}>
        <div style={prizeStyle}>
          🏆 1등 상금: {data.firstPrize?.toLocaleString() || '?'}원
        </div>
        <div style={prizeStyle}>
          💀 벌칙: {data.penalty || '없음'}
        </div>
        <div style={prizeStyle}>
          💰 누적: {data.totalPot?.toLocaleString() || '0'}원
        </div>
      </div>
    </motion.div>
  )
}

interface ExtraPlayerRowProps {
  player: ExtraGamePlayer
  rank: number
  gameColor: string
}

function ExtraPlayerRow({ player, rank, gameColor }: ExtraPlayerRowProps) {
  const medals = ['🥇', '🥈', '🥉']
  const medal = rank <= 3 ? medals[rank - 1] : `#${rank}`

  const rankColor = rank === 1 ? '#FFD700' : rank === 2 ? '#C0C0C0' : rank === 3 ? '#CD7F32' : gameColor

  return (
    <motion.div
      style={{
        ...playerRowStyle,
        borderColor: `rgba(${rankColor.replace('#', '')}, 0.5)`,
        boxShadow: `0 8px 32px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.1), 0 0 ${rank <= 3 ? '30px' : '0'} ${rankColor}40`,
      }}
      initial={{ opacity: 0, x: -50 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: rank * 0.1, duration: 0.5, ease: 'easeOut' }}
      className="extra-player-row"
    >
      {/* 순위 메달 */}
      <div style={{
        width: '56px',
        height: '56px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        fontSize: rank <= 3 ? '28px' : '20px',
        fontWeight: '900',
        color: rank <= 3 ? '#000' : '#FFF',
        background: rank <= 3 
          ? `linear-gradient(135deg, ${rankColor}, ${rankColor}CC)`
          : 'linear-gradient(135deg, #1a2a4a, #0d1a2f)',
        borderRadius: '50%',
        boxShadow: rank <= 3 
          ? `0 0 20px ${rankColor}, inset 0 -2px 4px rgba(0,0,0,0.3)`
          : 'inset 0 2px 4px rgba(0,0,0,0.4)',
        border: rank <= 3 ? `3px solid ${rankColor}` : '1px solid rgba(255,255,255,0.1)',
        flexShrink: 0,
      }}>
        {medal}
      </div>

      {/* 플레이어 이름 */}
      <div style={{
        flex: 1,
        fontSize: '24px',
        fontWeight: '800',
        color: '#FFF',
        textShadow: '0 0 15px rgba(255,215,0,0.5)',
        fontFamily: '"Noto Sans KR", sans-serif',
        whiteSpace: 'nowrap',
        overflow: 'hidden',
        textOverflow: 'ellipsis',
      }}>
        {player.name}
        {player.isWinner && <span style={{ marginLeft: '12px', color: '#FFD700', fontSize: '18px' }}>👑 승자</span>}
      </div>

      {/* 점수 */}
      <div style={{
        fontSize: '22px',
        fontWeight: '800',
        color: rankColor,
        textShadow: `0 0 20px ${rankColor}`,
        fontFamily: '"Orbitron", monospace',
        fontVariantNumeric: 'tabular-nums',
        minWidth: '120px',
        textAlign: 'right',
      }}>
        {player.score.toLocaleString()}
        {player.scoreChange !== undefined && player.scoreChange !== 0 && (
          <span style={{
            marginLeft: '8px',
            fontSize: '16px',
            color: player.scoreChange > 0 ? '#00FF88' : '#FF4466',
            fontWeight: '700',
          }}>
            {player.scoreChange > 0 ? '+' : ''}{player.scoreChange}
          </span>
        )}
      </div>

      {/* 기여도/벌칙 횟수 */}
      <div style={{
        fontSize: '16px',
        fontWeight: '600',
        color: '#FF6B9D',
        textShadow: '0 0 10px rgba(255,107,157,0.5)',
        fontFamily: '"Orbitron", monospace',
        minWidth: '100px',
        textAlign: 'right',
      }}>
        {player.penaltyCount !== undefined ? `벌칙 ${player.penaltyCount}회` : `+${player.contribution?.toLocaleString() || 0}`}
      </div>
    </motion.div>
  )
}