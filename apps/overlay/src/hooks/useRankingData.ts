import { useMemo } from 'react'
import { useOverlayStore } from '../stores/overlayStore'

export function useRankingData() {
  const { rankingData } = useOverlayStore()

  const { leftColumn, rightColumn, bottomFixed } = useMemo(() => {
    if (!rankingData) {
      return {
        leftColumn: [],
        rightColumn: [],
        bottomFixed: {
          totalScore: 0,
          totalContribution: 0,
          operatingCost: 0,
          netProfit: 0,
        },
      }
    }

    return {
      leftColumn: Array.isArray(rankingData.leftColumn) ? rankingData.leftColumn : (rankingData.leftColumn?.players || []),
      rightColumn: Array.isArray(rankingData.rightColumn) ? rankingData.rightColumn : (rankingData.rightColumn?.players || []),
      bottomFixed: rankingData.bottomFixed || {
        id: 'excel-bottom-fixed',
        label: '방송 운영비 정산',
        totalScore: 0,
        totalContribution: 0,
        operatingCost: 0,
        netProfit: 0,
      },
    }
  }, [rankingData])

  return { leftColumn, rightColumn, bottomFixed }
}