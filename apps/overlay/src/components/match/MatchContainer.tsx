import { motion } from 'framer-motion'
import { useOverlayStore } from '../../stores/overlayStore'
import { MatchBoard } from './MatchBoard'
import { FeverBorderFire } from './FeverBorderFire'

export function MatchContainer() {
  const { matchVisible, matchData } = useOverlayStore()

  if (!matchVisible) return null

  return (
    <motion.div
      id="match-container"
      className="match-container"
      initial={{ y: -100, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      exit={{ y: -100, opacity: 0 }}
      transition={{ type: 'spring', stiffness: 200, damping: 25 }}
      style={{
        position: 'absolute',
        top: 0,
        left: 0,
        width: '1080px',
        height: '1920px',
        pointerEvents: 'none',
        zIndex: 200,
      }}
    >
      <MatchBoard data={matchData} />
      
      {/* 피버 타임 불꽃 테두리 */}
      {matchData?.isFeverTime && <FeverBorderFire />}
    </motion.div>
  )
}