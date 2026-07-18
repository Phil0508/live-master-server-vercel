import React from 'react'
import { motion } from 'framer-motion'

interface SparkParticle {
  id: string
  x: number
  y: number
  playerId: string
}

interface SparkParticlesProps {
  particle: SparkParticle
}

export function SparkParticles({ particle }: SparkParticlesProps) {
  const sparkCount = 12
  const sparks = Array.from({ length: sparkCount }, (_, i) => {
    const angle = (Math.PI * 2 * i) / sparkCount
    const distance = 60 + Math.random() * 40
    const delay = Math.random() * 0.2
    return {
      x: Math.cos(angle) * distance,
      y: Math.sin(angle) * distance,
      delay,
      scale: 0.5 + Math.random() * 0.5,
      color: ['#FFD700', '#00D4FF', '#FF6B9D', '#00FF88'][Math.floor(Math.random() * 4)],
    }
  })

  const containerStyle: React.CSSProperties = {
    position: 'absolute',
    left: particle.x,
    top: particle.y,
    transform: 'translate(-50%, -50%)',
    pointerEvents: 'none',
    zIndex: 1000,
  }

  return (
    <motion.div
      style={containerStyle}
      initial={{ opacity: 1, scale: 1 }}
      animate={{ opacity: 0, scale: 0 }}
      transition={{ duration: 0.8, ease: 'easeOut' }}
      onAnimationComplete={() => {}}
    >
      {sparks.map((spark, i) => (
        <motion.div
          key={i}
          style={{
            position: 'absolute',
            width: '6px',
            height: '6px',
            borderRadius: '50%',
            background: spark.color,
            boxShadow: `0 0 10px ${spark.color}, 0 0 20px ${spark.color}`,
            transform: 'translate(-50%, -50%)',
          }}
          initial={{ x: 0, y: 0, opacity: 1, scale: spark.scale }}
          animate={{ 
            x: spark.x, 
            y: spark.y, 
            opacity: 0, 
            scale: 0 
          }}
          transition={{
            duration: 0.6 + Math.random() * 0.4,
            delay: spark.delay,
            ease: 'easeOut',
          }}
        />
      ))}
    </motion.div>
  )
}