import React from 'react'
import { motion } from 'framer-motion'
import type { MatchData } from '@live-master/shared/types'

interface MatchBoardProps {
  data: MatchData | null
}

const formatTime = (seconds: number) => {
  const m = Math.floor(seconds / 60).toString().padStart(2, '0')
  const s = (seconds % 60).toString().padStart(2, '0')
  return `${m}:${s}`
}

export function MatchBoard({ data }: MatchBoardProps) {
  if (!data) return null

  const { teamA, teamB, timer, isFeverTime, matchType } = data

  const boardStyle: React.CSSProperties = {
    position: 'absolute',
    top: '40px',
    left: '50%',
    transform: 'translateX(-50%)',
    width: '960px',
    height: '280px',
    background: 'linear-gradient(135deg, rgba(0,5,15,0.98), rgba(0,15,35,0.95))',
    border: '2px solid',
    borderImage: 'linear-gradient(135deg, #00D4FF, #FF6B9D, #00FF88) 1',
    borderRadius: '24px',
    boxShadow: `
      0 0 60px rgba(0,212,255,0.4),
      0 0 120px rgba(255,107,157,0.2),
      inset 0 1px 0 rgba(255,255,255,0.1),
      inset 0 -1px 0 rgba(0,212,255,0.1)
    `,
    backdropFilter: 'blur(30px)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '0 40px',
    pointerEvents: 'none',
    overflow: 'hidden',
  }

  const teamStyle: React.CSSProperties = {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '12px',
    position: 'relative',
  }

  const shieldStyle: React.CSSProperties = {
    width: '140px',
    height: '140px',
    borderRadius: '50%',
    background: `
      radial-gradient(circle at 30% 30%, rgba(255,255,255,0.15) 0%, transparent 50%),
      linear-gradient(135deg, rgba(0,212,255,0.2), rgba(255,107,157,0.15))
    `,
    border: '3px solid',
    borderImage: 'linear-gradient(135deg, #00D4FF, #FF6B9D) 1',
    boxShadow: `
      0 0 40px rgba(0,212,255,0.5),
      inset 0 2px 0 rgba(255,255,255,0.2),
      inset 0 -2px 0 rgba(0,0,0,0.3)
    `,
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '4px',
    position: 'relative',
    overflow: 'hidden',
  }

  const teamNameStyle: React.CSSProperties = {
    fontSize: '20px',
    fontWeight: '700',
    fontFamily: '"Orbitron", "Noto Sans KR", sans-serif',
    letterSpacing: '2px',
    textShadow: '0 0 20px currentColor',
    color: '#FFF',
  }

  const scoreStyle: React.CSSProperties = {
    fontSize: '72px',
    fontWeight: '900',
    fontFamily: '"Orbitron", monospace',
    fontVariantNumeric: 'tabular-nums',
    background: 'linear-gradient(135deg, #00D4FF, #FF6B9D, #00FF88)',
    backgroundClip: 'text',
    WebkitBackgroundClip: 'text',
    WebkitTextFillColor: 'transparent',
    textShadow: '0 0 40px rgba(0,212,255,0.5)',
    lineHeight: 1,
  }

  const vsStyle: React.CSSProperties = {
    position: 'absolute',
    left: '50%',
    top: '50%',
    transform: 'translate(-50%, -50%)',
    width: '80px',
    height: '80px',
    borderRadius: '50%',
    background: 'linear-gradient(135deg, #001a33, #00081a)',
    border: '3px solid',
    borderImage: 'linear-gradient(135deg, #00D4FF, #FF6B9D) 1',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    boxShadow: '0 0 40px rgba(0,212,255,0.5), inset 0 0 20px rgba(0,0,0,0.5)',
    zIndex: 10,
  }

  const timerCapsuleStyle: React.CSSProperties = {
    position: 'absolute',
    left: '50%',
    top: '50%',
    transform: 'translate(-50%, -50%)',
    width: '200px',
    height: '200px',
    borderRadius: '100px',
    background: `
      radial-gradient(circle at 50% 50%, rgba(0,212,255,0.15) 0%, transparent 70%),
      linear-gradient(135deg, rgba(0,10,20,0.95), rgba(0,20,40,0.9))
    `,
    border: '3px solid',
    borderImage: isFeverTime 
      ? 'linear-gradient(135deg, #FF4466, #FFAA00, #FF4466) 1'
      : 'linear-gradient(135deg, #00D4FF, #00FF88) 1',
    boxShadow: `
      ${isFeverTime 
        ? '0 0 60px rgba(255,68,102,0.6), inset 0 0 40px rgba(255,170,0,0.2)'
        : '0 0 50px rgba(0,212,255,0.5), inset 0 0 30px rgba(0,255,136,0.1)'
      }
    `,
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '8px',
    animation: isFeverTime ? 'pulseFever 0.5s ease-in-out infinite alternate' : 'pulseNormal 2s ease-in-out infinite',
    zIndex: 5,
  }

  const timerLabelStyle: React.CSSProperties = {
    fontSize: '14px',
    fontWeight: '700',
    fontFamily: '"Orbitron", sans-serif',
    letterSpacing: '3px',
    textTransform: 'uppercase',
    color: isFeverTime ? '#FFAA00' : '#00D4FF',
    textShadow: `0 0 15px ${isFeverTime ? '#FFAA00' : '#00D4FF'}`,
  }

  const timerValueStyle: React.CSSProperties = {
    fontSize: '56px',
    fontWeight: '900',
    fontFamily: '"Orbitron", monospace',
    fontVariantNumeric: 'tabular-nums',
    color: isFeverTime ? '#FF4466' : '#00FF88',
    textShadow: `0 0 30px ${isFeverTime ? '#FF4466' : '#00FF88'}`,
    lineHeight: 1,
    animation: timer <= 10 && !isFeverTime ? 'beepPulse 0.5s ease-in-out infinite' : 'none',
  }

  const matchTypeStyle: React.CSSProperties = {
    position: 'absolute',
    bottom: '16px',
    left: '50%',
    transform: 'translateX(-50%)',
    fontSize: '14px',
    fontWeight: '600',
    fontFamily: '"Orbitron", sans-serif',
    letterSpacing: '2px',
    color: 'rgba(255,255,255,0.6)',
    textTransform: 'uppercase',
    whiteSpace: 'nowrap',
  }

  return (
    <motion.div
      style={boardStyle}
      initial={{ scale: 0.9, opacity: 0 }}
      animate={{ scale: 1, opacity: 1 }}
      transition={{ type: 'spring', stiffness: 180, damping: 20 }}
      className="match-board"
    >
      {/* 팀 A - 좌측 */}
      <div style={teamStyle}>
        <div style={shieldStyle}>
          <div style={{ ...teamNameStyle, color: '#00D4FF' }}>
            {teamA.name}
          </div>
          <div style={scoreStyle}>
            {teamA.score.toLocaleString()}
          </div>
        </div>
      </div>

      {/* 중앙 캡슐 타이머 + VS */}
      <div style={{ position: 'relative', zIndex: 10 }}>
        <div style={timerCapsuleStyle}>
          <div style={timerLabelStyle}>
            {isFeverTime ? '🔥 FEVER TIME 🔥' : 'COUNTDOWN'}
          </div>
          <div style={timerValueStyle}>
            {formatTime(timer)}
          </div>
        </div>
        
        <div style={vsStyle}>
          <span style={{
            fontSize: '24px',
            fontWeight: '900',
            fontFamily: '"Orbitron", sans-serif',
            background: 'linear-gradient(135deg, #00D4FF, #FF6B9D)',
            backgroundClip: 'text',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
          }}>
            VS
          </span>
        </div>
      </div>

      {/* 팀 B - 우측 */}
      <div style={teamStyle}>
        <div style={shieldStyle}>
          <div style={{ ...teamNameStyle, color: '#FF6B9D' }}>
            {teamB.name}
          </div>
          <div style={scoreStyle}>
            {teamB.score.toLocaleString()}
          </div>
        </div>
      </div>

      {/* 매치 타입 표시 */}
      <div style={matchTypeStyle}>
        {matchType === '1v1' ? '1 : 1 데스매치' : matchType === 'team' ? '팀전 데스매치' : '커스텀 매치'}
      </div>

      {/* 애니메이션 키프레임 */}
      <style>{`
        @keyframes pulseNormal {
          0% { box-shadow: 0 0 50px rgba(0,212,255,0.5), inset 0 0 30px rgba(0,255,136,0.1); }
          100% { box-shadow: 0 0 70px rgba(0,212,255,0.7), inset 0 0 40px rgba(0,255,136,0.2); }
        }
        @keyframes pulseFever {
          0% { box-shadow: 0 0 60px rgba(255,68,102,0.6), inset 0 0 40px rgba(255,170,0,0.2); border-image: linear-gradient(135deg, #FF4466, #FFAA00, #FF4466) 1; }
          100% { box-shadow: 0 0 90px rgba(255,68,102,0.9), inset 0 0 60px rgba(255,170,0,0.4); border-image: linear-gradient(135deg, #FF4466, #FF0000, #FFAA00) 1; }
        }
        @keyframes beepPulse {
          0% { transform: scale(1); text-shadow: 0 0 30px #FF4466; }
          50% { transform: scale(1.05); text-shadow: 0 0 50px #FF4466, 0 0 80px #FF4466; }
          100% { transform: scale(1); text-shadow: 0 0 30px #FF4466; }
        }
      `}</style>
    </motion.div>
  )
}