import { create } from 'zustand'
import { devtools, persist } from 'zustand/middleware'
import type { RankingData, Player, ExtraGameData, MatchData, RouletteData, SlotMachineData, VIPData } from '@live-master/shared/types'

export type ViewMode = 'MAIN_RANKING' | 'EXTRA_GAME' | 'MATCH_MODE'

interface OverlayState {
  // Current view mode (exclusive screen switching)
  viewMode: ViewMode

  // Visibility states
  rankingVisible: boolean
  extraRankingVisible: boolean
  matchVisible: boolean
  rouletteVisible: boolean
  slotMachineVisible: boolean
  vipCardVisible: boolean

  // Data states
  rankingData: RankingData | null
  extraRankingData: ExtraGameData | null
  matchData: MatchData | null
  rouletteData: RouletteData | null
  slotMachineData: SlotMachineData | null
  vipCardData: VIPData | null

  // Animation states
  rankingAnimations: Map<string, 'spark' | 'bounce' | 'idle'>
  sparkParticles: Array<{ id: string; x: number; y: number; playerId: string }>

  // Actions
  setViewMode: (mode: ViewMode) => void
  setRankingVisible: (visible: boolean) => void
  setExtraRankingVisible: (visible: boolean) => void
  setMatchVisible: (visible: boolean) => void
  setRouletteVisible: (visible: boolean) => void
  setSlotMachineVisible: (visible: boolean) => void
  setVipCardVisible: (visible: boolean) => void

  updateRanking: (data: RankingData) => void
  updateExtraRanking: (data: ExtraGameData) => void
  updateMatch: (data: MatchData) => void
  updateRoulette: (data: RouletteData) => void
  updateSlotMachine: (data: SlotMachineData) => void
  updateVipCard: (data: VIPData) => void

  handleNewDonation: (donation: any) => void
  handleRouletteEvent: (event: any) => void
  handleMatchEvent: (event: any) => void
  handleExtraGameEvent: (event: any) => void
  showVIPCard: (data: VIPData) => void

  // Animation triggers
  triggerScoreAnimation: (playerId: string, type: 'spark' | 'bounce') => void
  clearAnimation: (playerId: string) => void
  addSparkParticle: (particle: { id: string; x: number; y: number; playerId: string }) => void
  removeSparkParticle: (id: string) => void
}

export const useOverlayStore = create<OverlayState>()(
  devtools(
    persist(
      (set, get) => ({
        // Initial view mode & visibility states
        viewMode: 'MAIN_RANKING',
        rankingVisible: true,
        extraRankingVisible: false,
        matchVisible: false,
        rouletteVisible: false,
        slotMachineVisible: false,
        vipCardVisible: false,

        // Initial data states
        rankingData: null,
        extraRankingData: null,
        matchData: null,
        rouletteData: null,
        slotMachineData: null,
        vipCardData: null,

        // Animation states
        rankingAnimations: new Map(),
        sparkParticles: [],

        // View Mode & Visibility actions
        setViewMode: (mode) => set({ 
          viewMode: mode,
          rankingVisible: mode === 'MAIN_RANKING',
          extraRankingVisible: mode === 'EXTRA_GAME',
          matchVisible: mode === 'MATCH_MODE',
        }),

        setRankingVisible: (visible) => set((state) => ({ 
          rankingVisible: visible,
          viewMode: visible ? 'MAIN_RANKING' : state.viewMode
        })),

        setExtraRankingVisible: (visible) => set({ 
          extraRankingVisible: visible,
          viewMode: visible ? 'EXTRA_GAME' : 'MAIN_RANKING',
        }),

        setMatchVisible: (visible) => set({ 
          matchVisible: visible,
          viewMode: visible ? 'MATCH_MODE' : 'MAIN_RANKING',
        }),

        setRouletteVisible: (visible) => set({ rouletteVisible: visible }),
        setSlotMachineVisible: (visible) => set({ slotMachineVisible: visible }),
        setVipCardVisible: (visible) => set({ vipCardVisible: visible }),

        // Data update actions
        updateRanking: (data) => set({ rankingData: data }),
        updateExtraRanking: (data) => set({ extraRankingData: data }),
        updateMatch: (data) => set({ matchData: data }),
        updateRoulette: (data) => set({ rouletteData: data }),
        updateSlotMachine: (data) => set({ slotMachineData: data }),
        updateVipCard: (data) => set({ vipCardData: data }),

        // Event handlers
        handleNewDonation: (donation) => {
          const { rankingData } = get()
          if (!rankingData) return

          const currentPlayers: Player[] = (rankingData as any).players || []
          const updatedPlayers = currentPlayers.map((player: Player) => {
            if (player.id === donation.player_id) {
              return {
                ...player,
                score: player.score + donation.amount,
                contribution: player.contribution + donation.amount,
              }
            }
            return player
          })

          updatedPlayers.sort((a: Player, b: Player) => 
            b.score - a.score || b.contribution - a.contribution
          )

          const rankedPlayers: Player[] = updatedPlayers.map((player: Player, index: number) => ({
            ...player,
            rank: index + 1,
            badge: (index === 0 ? 'gold' : index === 1 ? 'silver' : index === 2 ? 'bronze' : null) as Player['badge'],
          }))

          const totalScore = rankedPlayers.reduce((sum: number, p: Player) => sum + p.score, 0)
          const totalContribution = rankedPlayers.reduce((sum: number, p: Player) => sum + p.contribution, 0)

          set({
            rankingData: {
              ...rankingData,
              players: rankedPlayers,
              leftColumn: rankedPlayers.slice(0, 8),
              rightColumn: rankedPlayers.slice(8, 16),
              bottomFixed: {
                ...rankingData.bottomFixed,
                totalScore,
                totalContribution,
              }
            } as any
          })

          // 점수 상승 애니메이션 트리거
          get().triggerScoreAnimation(donation.player_id, 'spark')
        },

        handleRouletteEvent: (event) => {
          const { type, payload } = event
          if (type === 'roulette:spin') {
            set({ 
              rouletteData: payload,
              rouletteVisible: true 
            })
          } else if (type === 'roulette:result') {
            set({ rouletteData: payload })
            // 3초 후 룰렛 숨김
            setTimeout(() => {
              set({ rouletteVisible: false })
            }, 3000)
          }
        },

        handleMatchEvent: (event) => {
          const { type, payload } = event
          if (type === 'match:start' || type === 'match:update') {
            set({ 
              matchData: payload,
              matchVisible: true,
              viewMode: 'MATCH_MODE',
            })
          } else if (type === 'match:end' || type === 'match:cancel') {
            set({
              matchVisible: false,
              viewMode: 'MAIN_RANKING',
            })
          } else if (type === 'match:timer') {
            set((state) => ({
              matchData: state.matchData ? { ...state.matchData, ...payload } : payload
            }))
          }
        },

        handleExtraGameEvent: (event) => {
          const { type, payload } = event
          if (type === 'extra:start' || type === 'extra:update') {
            set({
              extraRankingData: payload,
              extraRankingVisible: true,
              viewMode: 'EXTRA_GAME',
            })
          } else if (type === 'extra:end' || type === 'extra:cancel') {
            set({
              extraRankingVisible: false,
              viewMode: 'MAIN_RANKING',
            })
          }
        },

        showVIPCard: (data) => {
          set({ 
            vipCardData: data,
            vipCardVisible: true 
          })
          // 8초 후 자동 숨김
          setTimeout(() => {
            set({ vipCardVisible: false })
          }, 8000)
        },

        // Animation triggers
        triggerScoreAnimation: (playerId, type) => {
          set((state) => {
            const newAnimations = new Map(state.rankingAnimations)
            newAnimations.set(playerId, type)
            // 1초 후 애니메이션 초기화
            setTimeout(() => {
              const currentAnimations = new Map(get().rankingAnimations)
              currentAnimations.set(playerId, 'idle')
              set({ rankingAnimations: currentAnimations })
            }, 1000)
            return { rankingAnimations: newAnimations }
          })
        },

        clearAnimation: (playerId) => {
          set((state) => {
            const newAnimations = new Map(state.rankingAnimations)
            newAnimations.delete(playerId)
            return { rankingAnimations: newAnimations }
          })
        },

        addSparkParticle: (particle) => {
          set((state) => ({
            sparkParticles: [...state.sparkParticles, particle]
          }))
          // 2초 후 파티클 제거
          setTimeout(() => {
            get().removeSparkParticle(particle.id)
          }, 2000)
        },

        removeSparkParticle: (id) => {
          set((state) => ({
            sparkParticles: state.sparkParticles.filter((p) => p.id !== id)
          }))
        },
      }),
      {
        name: 'overlay-store',
        partialize: (state) => ({
          rankingVisible: state.rankingVisible,
          extraRankingVisible: state.extraRankingVisible,
          matchVisible: state.matchVisible,
          rouletteVisible: state.rouletteVisible,
          slotMachineVisible: state.slotMachineVisible,
          vipCardVisible: state.vipCardVisible,
        }),
      }
    ),
    { name: 'overlay-store' }
  )
)