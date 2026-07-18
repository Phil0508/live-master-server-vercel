// Shared utility functions for Live Master Server

import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'
import { NeonColor, Player, RouletteSegment, SlotItem, Donation } from '../types'

/**
 * Combines class names with tailwind-merge for proper Tailwind CSS handling
 */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/**
 * Formats a number with Korean number formatting (만, 억 단위)
 */
export function formatKoreanNumber(num: number): string {
  if (num >= 100000000) {
    return `${(num / 100000000).toFixed(1).replace(/\.0$/, '')}억`
  }
  if (num >= 10000) {
    return `${(num / 10000).toFixed(1).replace(/\.0$/, '')}만`
  }
  return num.toLocaleString()
}

/**
 * Formats currency in Korean Won
 */
export function formatCurrency(amount: number): string {
  return `${formatKoreanNumber(amount)}원`
}

/**
 * Calculates rank badge based on rank position
 */
export function getRankBadge(rank: number): 'gold' | 'silver' | 'bronze' | null {
  if (rank === 1) return 'gold'
  if (rank === 2) return 'silver'
  if (rank === 3) return 'bronze'
  return null
}

/**
 * Generates a unique ID
 */
export function generateId(prefix = ''): string {
  return `${prefix}${Date.now()}-${Math.random().toString(36).substring(2, 9)}`
}

/**
 * Extracts dominant color from an image (HSL)
 * Uses Canvas API to sample pixels
 */
export async function getDominantNeonColor(imageUrl: string): Promise<NeonColor> {
  return new Promise((resolve, reject) => {
    const img = new Image()
    img.crossOrigin = 'anonymous'
    img.onload = () => {
      const canvas = document.createElement('canvas')
      const ctx = canvas.getContext('2d')
      if (!ctx) return reject(new Error('Canvas context not available'))

      canvas.width = img.width
      canvas.height = img.height
      ctx.drawImage(img, 0, 0)

      const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height)
      const data = imageData.data

      // Simple color quantization - sample every 10th pixel
      const colorCounts: Record<string, number> = {}
      for (let i = 0; i < data.length; i += 40) {
        const r = data[i]
        const g = data[i + 1]
        const b = data[i + 2]
        const a = data[i + 3]
        if (a < 128) continue // Skip transparent

        // Quantize to reduce color space
        const qr = Math.round(r / 32) * 32
        const qg = Math.round(g / 32) * 32
        const qb = Math.round(b / 32) * 32
        const key = `${qr},${qg},${qb}`
        colorCounts[key] = (colorCounts[key] || 0) + 1
      }

      // Find dominant color
      let maxCount = 0
      let dominantR = 0, dominantG = 0, dominantB = 0
      for (const [key, count] of Object.entries(colorCounts)) {
        if (count > maxCount) {
          maxCount = count
          const parts = key.split(',')
          dominantR = parseInt(parts[0], 10)
          dominantG = parseInt(parts[1], 10)
          dominantB = parseInt(parts[2], 10)
        }
      }

      // Convert to HSL
      const hsl = rgbToHsl(dominantR, dominantG, dominantB)
      const neonColor: NeonColor = {
        h: hsl.h,
        s: Math.min(100, hsl.s + 20), // Boost saturation for neon effect
        l: Math.max(40, Math.min(70, hsl.l)), // Clamp lightness for visibility
        hex: rgbToHex(dominantR, dominantG, dominantB),
      }
      resolve(neonColor)
    }
    img.onerror = () => reject(new Error('Failed to load image'))
    img.src = imageUrl
  })
}

/**
 * RGB to HSL conversion
 */
function rgbToHsl(r: number, g: number, b: number): { h: number; s: number; l: number } {
  r /= 255
  g /= 255
  b /= 255
  const max = Math.max(r, g, b)
  const min = Math.min(r, g, b)
  let h = 0, s = 0, l = (max + min) / 2

  if (max !== min) {
    const d = max - min
    s = l > 0.5 ? d / (2 - max - min) : d / (max + min)
    switch (max) {
      case r: h = (g - b) / d + (g < b ? 6 : 0); break
      case g: h = (b - r) / d + 2; break
      case b: h = (r - g) / d + 4; break
    }
    h /= 6
  }

  return { h: Math.round(h * 360), s: Math.round(s * 100), l: Math.round(l * 100) }
}

/**
 * RGB to Hex conversion
 */
function rgbToHex(r: number, g: number, b: number): string {
  return `#${[r, g, b].map(x => x.toString(16).padStart(2, '0')).join('')}`
}

/**
 * Converts HSL to CSS color string
 */
export function hslToString(hsl: NeonColor): string {
  return `hsl(${hsl.h}, ${hsl.s}%, ${hsl.l}%)`
}

/**
 * Calculates roulette segment angles based on weights
 */
export function calculateRouletteAngles(segments: RouletteSegment[]): RouletteSegment[] {
  const totalWeight = segments.reduce((sum, s) => sum + s.weight, 0)
  let currentAngle = -Math.PI / 2 // Start at top (12 o'clock)

  return segments.map(segment => {
    const angle = (segment.weight / totalWeight) * 2 * Math.PI
    const startAngle = currentAngle
    const endAngle = currentAngle + angle
    const midAngle = (startAngle + endAngle) / 2
    currentAngle = endAngle
    return { ...segment, startAngle, endAngle, midAngle }
  })
}

/**
 * Calculates slot reel stop position for rigged result
 */
export function calculateRiggedStopPosition(
  reelItems: SlotItem[],
  targetItemId: string
): number {
  const targetIndex = reelItems.findIndex(item => item.id === targetItemId)
  if (targetIndex === -1) return 0
  // Add full rotations for visual effect
  return targetIndex + reelItems.length * 3
}

/**
 * Generates confetti particles for celebrations
 */
export function createConfettiConfig(colors: string[] = ['#ff6b6b', '#4ecdc4', '#ffe66d', '#a8e6cf', '#ffd3b6']) {
  return {
    particleCount: 200,
    spread: 90,
    origin: { y: 0.6 },
    colors,
    scalar: 1.2,
    zIndex: 9999,
  }
}

/**
 * Debounce function for performance optimization
 */
export function debounce<T extends (...args: unknown[]) => unknown>(
  func: T,
  wait: number
): (...args: Parameters<T>) => void {
  let timeout: NodeJS.Timeout | null = null
  return (...args: Parameters<T>) => {
    if (timeout) clearTimeout(timeout)
    timeout = setTimeout(() => func(...args), wait)
  }
}

/**
 * Throttle function for rate limiting
 */
export function throttle<T extends (...args: unknown[]) => unknown>(
  func: T,
  limit: number
): (...args: Parameters<T>) => void {
  let inThrottle = false
  return (...args: Parameters<T>) => {
    if (!inThrottle) {
      func(...args)
      inThrottle = true
      setTimeout(() => (inThrottle = false), limit)
    }
  }
}

/**
 * Formats time as MM:SS
 */
export function formatTime(seconds: number): string {
  const mins = Math.floor(seconds / 60)
  const secs = seconds % 60
  return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
}

/**
 * Calculates contribution weight for roulette segments
 */
export function calculateContributionWeight(
  player: Player,
  allPlayers: Player[]
): number {
  const totalContribution = allPlayers.reduce((sum, p) => sum + p.contribution, 0)
  if (totalContribution === 0) return 1 / allPlayers.length
  return player.contribution / totalContribution
}

/**
 * Validates donation data
 */
export function validateDonation(data: Partial<Donation>): { valid: boolean; errors: string[] } {
  const errors: string[] = []
  if (!data.donorName?.trim()) errors.push('후원자 이름이 필요합니다')
  if (!data.amount || data.amount <= 0) errors.push('유효한 후원 금액이 필요합니다')
  return { valid: errors.length === 0, errors }
}

/**
 * Deep clones an object
 */
export function deepClone<T>(obj: T): T {
  return JSON.parse(JSON.stringify(obj))
}

/**
 * Checks if two objects are deeply equal
 */
export function deepEqual(a: unknown, b: unknown): boolean {
  return JSON.stringify(a) === JSON.stringify(b)
}

/**
 * Groups array items by a key function
 */
export function groupBy<T>(array: T[], keyFn: (item: T) => string): Record<string, T[]> {
  return array.reduce((groups, item) => {
    const key = keyFn(item)
    groups[key] = groups[key] || []
    groups[key].push(item)
    return groups
  }, {} as Record<string, T[]>)
}

/**
 * Sorts players by rank (score desc, then contribution desc)
 */
export function sortPlayersByRank(players: Player[]): Player[] {
  return [...players].sort((a, b) => {
    if (b.score !== a.score) return b.score - a.score
    return b.contribution - a.contribution
  })
}