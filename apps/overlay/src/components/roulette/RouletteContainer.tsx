import React from 'react'
import { motion } from 'framer-motion'
import { useOverlayStore } from '../../stores/overlayStore'

export const RouletteContainer: React.FC = () => {
  const rouletteData = useOverlayStore((state) => state.rouletteData)

  if (!rouletteData) return null

  return (
    <motion.div
      className="roulette-modal"
      initial={{ opacity: 0, scale: 0.8 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.8 }}
      style={{
        position: 'absolute',
        top: '50%',
        left: '50%',
        transform: 'translate(-50%, -50%)',
        zIndex: 100,
        background: 'rgba(15, 23, 42, 0.95)',
        backdropFilter: 'blur(16px)',
        border: '2px solid rgba(234, 179, 8, 0.5)',
        borderRadius: '24px',
        padding: '32px',
        boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.5)',
        color: '#fff',
        textAlign: 'center',
        minWidth: '400px',
      }}
    >
      <h2 style={{ fontSize: '2rem', color: '#facc15', marginBottom: '16px', fontWeight: 'bold' }}>
        🎰 룰렛 이벤트
      </h2>
      {rouletteData.winner_name ? (
        <div>
          <p style={{ fontSize: '1.2rem', color: '#94a3b8' }}>당첨자</p>
          <p style={{ fontSize: '2rem', fontWeight: 'bold', color: '#38bdf8', marginTop: '8px' }}>
            {rouletteData.winner_name}
          </p>
        </div>
      ) : (
        <p style={{ fontSize: '1.2rem', color: '#cbd5e1' }}>룰렛 회전 중...</p>
      )}
    </motion.div>
  )
}
