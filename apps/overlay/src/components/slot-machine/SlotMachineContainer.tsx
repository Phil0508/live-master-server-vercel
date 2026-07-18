import React from 'react'
import { motion } from 'framer-motion'
import { useOverlayStore } from '../../stores/overlayStore'

export const SlotMachineContainer: React.FC = () => {
  const slotMachineData = useOverlayStore((state) => state.slotMachineData)

  if (!slotMachineData) return null

  return (
    <motion.div
      className="slot-machine-modal"
      initial={{ opacity: 0, y: 50 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: 50 }}
      style={{
        position: 'absolute',
        bottom: '100px',
        left: '50%',
        transform: 'translateX(-50%)',
        zIndex: 90,
        background: 'rgba(30, 27, 75, 0.95)',
        backdropFilter: 'blur(16px)',
        border: '2px solid rgba(168, 85, 247, 0.5)',
        borderRadius: '20px',
        padding: '24px 40px',
        boxShadow: '0 20px 40px rgba(0, 0, 0, 0.6)',
        color: '#fff',
        textAlign: 'center',
      }}
    >
      <h3 style={{ fontSize: '1.5rem', color: '#c084fc', marginBottom: '12px', fontWeight: 'bold' }}>
        🎰 슬롯머신
      </h3>
      <p style={{ fontSize: '1.1rem', color: '#e2e8f0' }}>{slotMachineData.status || '진행 중'}</p>
    </motion.div>
  )
}
