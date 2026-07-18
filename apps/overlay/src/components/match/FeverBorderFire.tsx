import React from 'react'
import { motion } from 'framer-motion'

export function FeverBorderFire() {
  const fireLayers = Array.from({ length: 4 }, (_, i) => ({
    id: i,
    delay: i * 0.15,
    scale: 1 + i * 0.15,
    opacity: 0.6 - i * 0.1,
    blur: 10 + i * 15,
    colors: [
      'rgba(255, 68, 102,',
      'rgba(255, 170, 0,',
      'rgba(255, 255, 0,',
      'rgba(255, 68, 102,',
    ][i],
  }))

  const containerStyle: React.CSSProperties = {
    position: 'absolute',
    inset: 0,
    pointerEvents: 'none',
    zIndex: 1000,
    overflow: 'hidden',
  }

  return (
    <div style={containerStyle} className="fever-border-fire">
      {/* 4방향 불꽃 레이어 */}
      {fireLayers.map((layer) => (
        <FireLayer key={layer.id} layer={layer} />
      ))}

      {/* 모서리 번개/스파크 */}
      <CornerSparks />

      {/* 중앙 펄스 링 */}
      <CenterPulseRing />

      <style>{`
        @keyframes fireRise {
          0% { 
            transform: translateY(0) scale(1); 
            opacity: 1; 
          }
          50% { 
            transform: translateY(-30px) scale(1.2); 
            opacity: 0.8; 
          }
          100% { 
            transform: translateY(-100px) scale(0.5); 
            opacity: 0; 
          }
        }
        @keyframes fireFlicker {
          0%, 100% { opacity: 1; filter: blur(10px) brightness(1); }
          25% { opacity: 0.7; filter: blur(15px) brightness(1.3); }
          50% { opacity: 0.9; filter: blur(8px) brightness(0.9); }
          75% { opacity: 0.6; filter: blur(20px) brightness(1.5); }
        }
        @keyframes cornerSpark {
          0% { transform: scale(0) rotate(0deg); opacity: 1; }
          50% { transform: scale(1.5) rotate(180deg); opacity: 0.8; }
          100% { transform: scale(0) rotate(360deg); opacity: 0; }
        }
        @keyframes pulseRing {
          0% { transform: scale(0.8); opacity: 0.8; }
          100% { transform: scale(1.5); opacity: 0; }
        }
        @keyframes screenShake {
          0%, 100% { transform: translate(0, 0) rotate(0deg); }
          25% { transform: translate(2px, -1px) rotate(0.1deg); }
          50% { transform: translate(-1px, 2px) rotate(-0.1deg); }
          75% { transform: translate(1px, 1px) rotate(0.05deg); }
        }
      `}</style>
    </div>
  )
}

interface FireLayerProps {
  layer: {
    id: number
    delay: number
    scale: number
    opacity: number
    blur: number
    colors: string
  }
}

function FireLayer({ layer }: FireLayerProps) {
  const particles = Array.from({ length: 20 }, (_, i) => ({
    id: i,
    left: `${Math.random() * 100}%`,
    bottom: '-50px',
    delay: Math.random() * 3 + layer.delay,
    duration: 2 + Math.random() * 2,
    size: 20 + Math.random() * 40 * layer.scale,
    opacity: layer.opacity * (0.5 + Math.random() * 0.5),
    color: `${layer.colors}${layer.opacity})`,
    blur: layer.blur,
  }))

  return (
    <div style={{
      position: 'absolute',
      inset: 0,
      animation: `fireFlicker 0.1s ease-in-out infinite alternate`,
      filter: `blur(${layer.blur}px)`,
    }}>
      {particles.map((p) => (
        <motion.div
          key={p.id}
          style={{
            position: 'absolute',
            left: p.left,
            bottom: p.bottom,
            width: p.size,
            height: p.size,
            borderRadius: '50%',
            background: `radial-gradient(circle at 50% 50%, ${p.color}, transparent 70%)`,
            filter: `blur(${p.blur}px)`,
            pointerEvents: 'none',
          }}
          animate={{
            y: [-2000, 0],
            scale: [0, 1, 0.5],
            opacity: [0, p.opacity, 0],
          }}
          transition={{
            duration: p.duration,
            delay: p.delay,
            repeat: Infinity,
            ease: 'easeOut',
          }}
        />
      ))}
    </div>
  )
}

function CornerSparks() {
  const corners = [
    { top: '0', left: '0', rotate: '45deg' },
    { top: '0', right: '0', rotate: '-45deg' },
    { bottom: '0', left: '0', rotate: '-45deg' },
    { bottom: '0', right: '0', rotate: '45deg' },
  ]

  return (
    <div style={{ position: 'absolute', inset: 0, pointerEvents: 'none' }}>
      {corners.map((corner, i) => (
        <motion.div
          key={i}
          style={{
            position: 'absolute',
            ...corner,
            width: '200px',
            height: '200px',
            borderRadius: '50%',
            background: `
              radial-gradient(circle at 50% 50%, 
                rgba(255,255,0,0.8) 0%, 
                rgba(255,170,0,0.6) 30%, 
                rgba(255,68,102,0.3) 60%, 
                transparent 100%
              )
            `,
            filter: 'blur(20px)',
            transform: `rotate(${corner.rotate})`,
            transformOrigin: 'center',
          }}
          animate={{
            scale: [0, 1.2, 0],
            opacity: [0.8, 0.4, 0],
            rotate: ['0deg', '90deg', '180deg'],
          }}
          transition={{
            duration: 1.5,
            delay: i * 0.2,
            repeat: Infinity,
            ease: 'easeInOut',
          }}
        />
      ))}
    </div>
  )
}

function CenterPulseRing() {
  const rings = [0, 1, 2].map(i => ({
    delay: i * 0.4,
    color: ['rgba(255,68,102,0.6)', 'rgba(255,170,0,0.4)', 'rgba(255,255,0,0.2)'][i],
  }))

  return (
    <div style={{ 
      position: 'absolute', 
      top: '50%', 
      left: '50%', 
      transform: 'translate(-50%, -50%)',
      pointerEvents: 'none',
    }}>
      {rings.map((ring, i) => (
        <motion.div
          key={i}
          style={{
            position: 'absolute',
            top: '50%',
            left: '50%',
            transform: 'translate(-50%, -50%)',
            width: '400px',
            height: '400px',
            borderRadius: '50%',
            border: `4px solid ${ring.color}`,
            boxShadow: `0 0 60px ${ring.color}, inset 0 0 60px ${ring.color}`,
            pointerEvents: 'none',
          }}
          animate={{
            scale: [0.3, 1.5],
            opacity: [0.8, 0],
            borderWidth: [8, 0],
          }}
          transition={{
            duration: 2,
            delay: ring.delay,
            repeat: Infinity,
            ease: 'easeOut',
          }}
        />
      ))}
    </div>
  )
}