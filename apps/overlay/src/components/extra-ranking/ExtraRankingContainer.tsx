import { motion } from 'framer-motion'
import { useOverlayStore } from '../../stores/overlayStore'
import { ExtraRankingBoard } from './ExtraRankingBoard'

export function ExtraRankingContainer() {
  const { extraRankingVisible, extraRankingData } = useOverlayStore()

  if (!extraRankingVisible) return null

  return (
    <motion.div
      id="extra-ranking-container"
      className="extra-ranking-container"
      initial={{ x: 1500, opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      exit={{ x: 1500, opacity: 0 }}
      transition={{ 
        type: 'spring', 
        stiffness: 120, 
        damping: 20,
        duration: 0.8 
      }}
      style={{
        position: 'absolute',
        top: 0,
        left: 0,
        width: '1080px',
        height: '1920px',
        pointerEvents: 'auto',
        zIndex: 100,
      }}
    >
      <ExtraRankingBoard data={extraRankingData} />
    </motion.div>
  )
}