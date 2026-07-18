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
    viewMode,
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
      {/* 🚀 전면 독점 화면 전환 (Exclusive View Mode Switcher) */}
      <AnimatePresence mode="wait">
        {viewMode === 'MAIN_RANKING' && <RankingContainer key="main-ranking" />}
        {viewMode === 'EXTRA_GAME' && <ExtraRankingContainer key="extra-ranking" />}
        {viewMode === 'MATCH_MODE' && <MatchContainer key="match-mode" />}
      </AnimatePresence>

      {/* 🎰 미니게임 오버레이 모달들 (상시 레이어) */}
      {rouletteVisible && <RouletteContainer />}
      {slotMachineVisible && <SlotMachineContainer />}
      {vipCardVisible && <VIPPremiumCardContainer />}
    </div>
  )
}

export default App