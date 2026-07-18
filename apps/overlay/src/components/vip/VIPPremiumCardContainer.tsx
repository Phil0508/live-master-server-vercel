import React from 'react'
import { motion } from 'framer-motion'
import { useOverlayStore } from '../../stores/overlayStore'

export const VIPPremiumCardContainer: React.FC = () => {
  const vipCardData = useOverlayStore((state) => state.vipCardData)

  if (!vipCardData) return null

  return (
    <motion.div
      className="vip-card-modal"
      initial={{ opacity: 0, scale: 0.5, y: -100 }}
      animate={{ opacity: 1, scale: 1, y: 0 }}
      exit={{ opacity: 0, scale: 0.5, y: -100 }}
      transition={{ type: 'spring', damping: 15, stiffness: 200 }}
      style={{
        position: 'absolute',
        top: '150px',
        left: '50%',
        transform: 'translateX(-50%)',
        zIndex: 110,
        background: 'linear-gradient(135deg, rgba(234, 179, 8, 0.95), rgba(161, 98, 7, 0.95))',
        backdropFilter: 'blur(20px)',
        border: '3px solid #fef08a',
        borderRadius: '24px',
        padding: '32px 48px',
        boxShadow: '0 0 50px rgba(234, 179, 8, 0.6), 0 25px 50px -12px rgba(0, 0, 0, 0.8)',
        color: '#0f172a',
        textAlign: 'center',
        minWidth: '450px',
      }}
    >
      <div style={{ fontSize: '0.9rem', letterSpacing: '4px', textTransform: 'uppercase', fontWeight: 800, opacity: 0.8 }}>
        VIP 후원 카드
      </div>
      <h2 style={{ fontSize: '2.5rem', fontWeight: 900, margin: '8px 0', textShadow: '0 2px 4px rgba(255,255,255,0.4)' }}>
        {vipCardData.donor_name || vipCardData.username}
      </h2>
      <p style={{ fontSize: '1.8rem', fontWeight: 700, color: '#78350f' }}>
        {vipCardData.amount ? `${vipCardData.amount.toLocaleString()}원` : ''}
      </p>
      {vipCardData.message && (
        <p style={{ marginTop: '12px', fontSize: '1.2rem', fontStyle: 'italic', color: '#1e293b' }}>
          "{vipCardData.message}"
        </p>
      )}
    </motion.div>
  )
}
