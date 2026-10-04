// Agent 1: Animation Part — Motion Variants & Interactive Physics

export const headingContainer = {
  hidden: { opacity: 0 },
  visible: (i = 1) => ({
    opacity: 1,
    transition: { staggerChildren: 0.08, delayChildren: 0.05 * i },
  }),
};

export const headingLetter = {
  hidden: {
    opacity: 0,
    y: 28,
    rotateX: -60,
    filter: 'blur(8px)',
  },
  visible: {
    opacity: 1,
    y: 0,
    rotateX: 0,
    filter: 'blur(0px)',
    transition: {
      type: 'spring',
      damping: 14,
      stiffness: 120,
    },
  },
};

export const fadeInUp = {
  hidden: { opacity: 0, y: 24 },
  visible: {
    opacity: 1,
    y: 0,
    transition: {
      duration: 0.6,
      ease: [0.22, 1, 0.36, 1],
    },
  },
};

export const popButtonVariants = {
  initial: { scale: 1, y: 0 },
  hover: {
    scale: 1.05,
    y: -3,
    boxShadow: '0 20px 30px -10px rgba(13, 148, 136, 0.45), 0 10px 15px -5px rgba(13, 148, 136, 0.3)',
    transition: {
      type: 'spring',
      stiffness: 400,
      damping: 17,
    },
  },
  tap: {
    scale: 0.94,
    y: 1,
    boxShadow: '0 4px 10px -2px rgba(13, 148, 136, 0.3)',
    transition: {
      type: 'spring',
      stiffness: 500,
      damping: 15,
    },
  },
};

export const floatingFoodContainer = {
  initial: { opacity: 0, scale: 0.92, x: 50 },
  animate: {
    opacity: 1,
    scale: 1,
    x: 0,
    transition: {
      duration: 0.9,
      ease: [0.16, 1, 0.3, 1],
    },
  },
};

export const floatKeyframes = {
  animate: {
    y: [0, -14, 0],
    rotate: [0, 1.2, 0],
    transition: {
      duration: 6,
      repeat: Infinity,
      repeatType: 'reverse',
      ease: 'easeInOut',
    },
  },
};

export const floatingBadge = (delay = 0, yOffset = 10) => ({
  animate: {
    y: [0, -yOffset, 0],
    transition: {
      duration: 4,
      delay: delay,
      repeat: Infinity,
      repeatType: 'reverse',
      ease: 'easeInOut',
    },
  },
});

export const scannerBeamVariants = {
  animate: {
    top: ['2%', '94%', '2%'],
    transition: {
      duration: 2.2,
      repeat: Infinity,
      ease: 'easeInOut',
    },
  },
};

export const cardStagger = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.12,
      delayChildren: 0.3,
    },
  },
};

export const cardItem = {
  hidden: { opacity: 0, y: 20, scale: 0.96 },
  visible: {
    opacity: 1,
    y: 0,
    scale: 1,
    transition: {
      type: 'spring',
      stiffness: 260,
      damping: 20,
    },
  },
};
