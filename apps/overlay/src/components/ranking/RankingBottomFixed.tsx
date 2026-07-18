import React from 'react'
import { motion } from 'framer-motion'
import type { RankingBottomFixed } from '@live-master/shared/types'

interface RankingBottomFixedProps {
  data: RankingBottomFixed
}

const formatNumber = (num: number) => num.toLocaleString()

export function RankingBottomFixed({ data }: RankingBottomFixedProps) {
  const containerStyle: React.CSSProperties = {
    position: 'absolute',
    bottom: '40px',
    left: '60px',
    right: '60px',
    height: '120px',
    background: 'linear-gradient(135deg, rgba(0,15,30,0.95), rgba(0,30,60,0.9))',
    border: '2px solid rgba(0,212,255,0.4)',
    borderRadius: '16px',
    backdropFilter: 'blur(20px)',
    boxShadow: '0 0 40px rgba(0,212,255,0.2), inset 0 1px 0 rgba(255,255,255,0.1)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-around',
    padding: '0 24px',
    pointerEvents: 'none',
    overflow: 'hidden',
  }

  const labelStyle: React.CSSProperties = {
    fontSize: '14px',
    fontWeight: '600',
    color: 'rgba(255,255,255,0.6)',
    textTransform: 'uppercase',
    letterSpacing: '1px',
    fontFamily: '"Orbitron", monospace',
    marginBottom: '4px',
  }

  const valueStyle: React.CSSProperties = {
    fontSize: '28px',
    fontWeight: '800',
    fontFamily: '"Orbitron", monospace',
    fontVariantNumeric: 'tabular-nums',
    textShadow: '0 0 20px currentColor',
  }

  const itemStyle: React.CSSProperties = {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: '4px',
  }

  const dividerStyle: React.CSSProperties = {
    width: '1px',
    height: '60px',
    background: 'linear-gradient(180deg, transparent, rgba(0,212,255,0.4), transparent)',
  }

  const netProfitColor = data.netProfit >= 0 ? '#00FF88' : '#FF4466'

  return (
    <motion.div
      style={containerStyle}
      initial={{ opacity: 0, y: 50 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.8, delay: 0.5, ease: 'easeOut' }}
      className="ranking-bottom-fixed"
    >
      {/* 반짝이는 상단 보더 */}
      <div style={{
        position: 'absolute',
        top: 0,
        left: 0,
        right: 0,
        height: '2px',
        background: 'linear-gradient(90deg, transparent, #00D4FF, #00FF88, #FF6B9D, transparent)',
        backgroundSize: '300% 100%',
        animation: 'shimmer 3s linear infinite',
      }} />

      <div style={itemStyle}>
        <div style={labelStyle}>총 점수</div>
        <div style={{ ...valueStyle, color: '#00D4FF' }}>{formatNumber(data.totalScore)}</div>
      </div>

      <div style={dividerStyle} />

      <div style={itemStyle}>
        <div style={labelStyle}>총 기여도</div>
        <div style={{ ...valueStyle, color: '#FF6B9D' }}>{formatNumber(data.totalContribution)}</div>
      </div>

      <div style={dividerStyle} />

      <div style={itemStyle}>
        <div style={labelStyle}>운영비</div>
        <div style={{ ...valueStyle, color: '#FFAA00' }}>{formatNumber(data.operatingCost)}</div>
      </div>

      <div style={dividerStyle} />

      <div style={itemStyle}>
        <div style={labelStyle}>순이익</div>
        <div style={{ ...valueStyle, color: netProfitColor }}>
          {data.netProfit >= 0 ? '+' : ''}{formatNumber(data.netProfit)}
        </div>
      </div>

      <style>{`
        @keyframes shimmer {
          0% { background-position: -200% 0; }
          100% { background-position: 200% 0; }
        }
      `}</style>
    </motion.div>
  )
}