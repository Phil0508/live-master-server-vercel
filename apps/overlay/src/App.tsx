import React from 'react'
import { AnimatePresence } from 'framer-motion'
import { RankingContainer } from './components/ranking/RankingContainer'
import { ExtraRankingContainer } from './components/extra-ranking/ExtraRankingContainer'
import { MatchContainer } from './components/match/MatchContainer'
import { RouletteContainer } from './components/roulette/RouletteContainer'
import { SlotMachineContainer } from './components/slot-machine/SlotMachineContainer'
import { VIPPremiumCardContainer } from './components/vip/VIPPremiumCardContainer'
import { useOverlayStore } from './stores/overlayStore'
import { subscribeToRankings, subscribeToDonations, subscribeToRoulette, subscribeToMatch, subscribeToVIP } from './lib/supabase'

function App() {
  const { 
    rankingVisible,
    extraRankingVisible,
    matchVisible,
    rouletteVisible, 
    slotMachineVisible,
    vipCardVisible 
  } = useOverlayStore()

  // 실시간 구독 설정
  React.useEffect(() => {
    const channels = [
      subscribeToRankings((payload) => {
        useOverlayStore.getState().updateRanking(payload)
      }),
      subscribeToDonations((payload) => {
        useOverlayStore.getState().handleNewDonation(payload)
      }),
      subscribeToRoulette((payload) => {
        useOverlayStore.getState().handleRouletteEvent(payload)
      }),
      subscribeToMatch((payload) => {
        useOverlayStore.getState().handleMatchEvent(payload)
      }),
      subscribeToVIP((payload) => {
        useOverlayStore.getState().showVIPCard(payload)
      }),
    ]

    return () => {
      channels.forEach((ch) => ch.unsubscribe())
    }
  }, [])

  return (
    <div className="overlay-root" style={{ width: '1080px', height: '1920px', position: 'relative', overflow: 'hidden' }}>
      {/* 1. 메인 랭킹판 (배경 레이어) */}
      {rankingVisible && <RankingContainer />}

      {/* 2. 번외게임 / 퇴근전쟁 (우측 슬라이딩 전면 패널) */}
      <AnimatePresence>
        {extraRankingVisible && <ExtraRankingContainer key="extra-ranking-slide" />}
      </AnimatePresence>

      {/* 3. 대결 매치판 (상단 패널) */}
      <AnimatePresence>
        {matchVisible && <MatchContainer key="match-container-slide" />}
      </AnimatePresence>

      {/* 4. 미니게임 모달 오버레이들 */}
      {rouletteVisible && <RouletteContainer />}
      {slotMachineVisible && <SlotMachineContainer />}
      {vipCardVisible && <VIPPremiumCardContainer />}
    </div>
  )
}

export default App