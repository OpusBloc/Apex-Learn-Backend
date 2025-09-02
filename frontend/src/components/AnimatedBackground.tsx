import React from 'react';
import { motion } from 'framer-motion';

const AnimatedBackground: React.FC = () => {
  return (
    <div className="absolute inset-0 overflow-hidden pointer-events-none">
      {/* Floating geometric shapes */}
      <motion.div
        className="absolute top-20 left-20 w-32 h-32 bg-primary-200 rounded-full opacity-30"
        animate={{
          y: [0, -30, 0],
          x: [0, 15, 0],
          rotate: [0, 180, 360],
        }}
        transition={{
          duration: 20,
          repeat: Infinity,
          ease: "easeInOut",
        }}
      />
      
      <motion.div
        className="absolute top-40 right-32 w-24 h-24 bg-secondary-300 rounded-lg opacity-25"
        animate={{
          y: [0, 40, 0],
          x: [0, -20, 0],
          rotate: [0, -180, -360],
        }}
        transition={{
          duration: 15,
          repeat: Infinity,
          ease: "easeInOut",
        }}
      />
      
      <motion.div
        className="absolute bottom-32 left-1/4 w-20 h-20 bg-accent-300 rounded-full opacity-20"
        animate={{
          y: [0, -25, 0],
          x: [0, 30, 0],
          scale: [1, 1.2, 1],
        }}
        transition={{
          duration: 12,
          repeat: Infinity,
          ease: "easeInOut",
        }}
      />
      
      <motion.div
        className="absolute top-1/2 right-20 w-16 h-16 bg-purple-300 rounded-lg opacity-30"
        animate={{
          y: [0, 20, 0],
          x: [0, -15, 0],
          rotate: [0, 90, 180],
        }}
        transition={{
          duration: 18,
          repeat: Infinity,
          ease: "easeInOut",
        }}
      />
      
      {/* Mathematical symbols floating */}
      <motion.div
        className="absolute top-1/3 left-1/2 text-4xl text-primary-300 opacity-20 font-bold"
        animate={{
          y: [0, -50, 0],
          rotate: [0, 360],
        }}
        transition={{
          duration: 25,
          repeat: Infinity,
          ease: "easeInOut",
        }}
      >
        ∑
      </motion.div>
      
      <motion.div
        className="absolute bottom-1/4 right-1/3 text-3xl text-secondary-400 opacity-25 font-bold"
        animate={{
          y: [0, 35, 0],
          x: [0, 20, 0],
          rotate: [0, -360],
        }}
        transition={{
          duration: 20,
          repeat: Infinity,
          ease: "easeInOut",
        }}
      >
        π
      </motion.div>
      
      <motion.div
        className="absolute top-2/3 left-1/3 text-2xl text-accent-400 opacity-20 font-bold"
        animate={{
          y: [0, -30, 0],
          x: [0, -25, 0],
        }}
        transition={{
          duration: 16,
          repeat: Infinity,
          ease: "easeInOut",
        }}
      >
        √
      </motion.div>
    </div>
  );
};

export default AnimatedBackground;