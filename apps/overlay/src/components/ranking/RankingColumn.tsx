import React from 'react'
import { PlayerRow } from './PlayerRow'
import type { Player } from '@live-master/shared/types'

interface RankingColumnProps {
  title: string
  players: Player[]
  column: 'left' | 'right'
  animations: Map<string, 'spark' | 'bounce' | 'idle'>
}

export function RankingColumn({ title, players, column, animations }: RankingColumnProps) {
  const columnStyle: React.CSSProperties = {
    position: 'absolute',
    top: '120px',
    [column === 'left' ? 'left' : 'right']: '60px',
    width: '450px',
    height: 'calc(100% - 200px)',
    display: 'flex',
    flexDirection: 'column',
    gap: '8px',
    pointerEvents: 'none',
  }

  const headerStyle: React.CSSProperties = {
    fontSize: '24px',
    fontWeight: '800',
    color: column === 'left' ? '#00D4FF' : '#FF6B9D',
    textShadow: '0 0 20px currentColor',
    marginBottom: '16px',
    fontFamily: '"Orbitron", "Noto Sans KR", sans-serif',
    letterSpacing: '2px',
  }

  return (
    <div style={columnStyle}>
      <div style={headerStyle}>{title}</div>
      {players.map((player, index) => (
        <PlayerRow
          key={player.id}
          player={player}
          index={index}
          animation={animations.get(player.id) || 'idle'}
        />
      ))}
    </div>
  )
}