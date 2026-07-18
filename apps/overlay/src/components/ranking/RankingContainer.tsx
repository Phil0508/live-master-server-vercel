import { motion, AnimatePresence } from 'framer-motion'
import { useOverlayStore } from '../../stores/overlayStore'
import { RankingColumn } from './RankingColumn'
import { RankingBottomFixed } from './RankingBottomFixed'
import { SparkParticles } from './SparkParticles'
import { useRankingData } from '../../hooks/useRankingData'

export function RankingContainer() {
  const { rankingData, rankingVisible, rankingAnimations, sparkParticles } = useOverlayStore()
  const { leftColumn, rightColumn, bottomFixed } = useRankingData()

  if (!rankingVisible || !rankingData) return null

  const safeBottomFixed = {
    id: 'excel-bottom-fixed' as const,
    label: '방송 운영비 정산' as const,
    ...bottomFixed
  } as const

  return (
    <motion.div
      id="ranking-container"
      className="ranking-container"
      initial={{ opacity: 0, y: 50 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -50 }}
      transition={{ duration: 0.5, ease: 'easeOut' }}
      style={{
        position: 'absolute',
        top: 0,
        left: 0,
        width: '1080px',
        height: '1920px',
        pointerEvents: 'none',
      }}
    >
      {/* 좌측 컬럼 */}
      <RankingColumn
        title="좌측 랭킹"
        players={leftColumn as any}
        column="left"
        animations={rankingAnimations}
      />

      {/* 우측 컬럼 */}
      <RankingColumn
        title="우측 랭킹"
        players={rightColumn as any}
        column="right"
        animations={rankingAnimations}
      />

      {/* 하단 고정행 - 방송 운영비 정산 */}
      <RankingBottomFixed data={safeBottomFixed} />

      {/* 스파크 파티클 오버레이 */}
      <AnimatePresence>
        {sparkParticles.map((particle) => (
          <SparkParticles key={particle.id} particle={particle} />
        ))}
      </AnimatePresence>
    </motion.div>
  )
}