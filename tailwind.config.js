/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        teal: {
          50: '#f1faf7',
          100: '#ddf7f3',
          200: '#b8e8df',
          300: '#9eddd2',
          400: '#74c0b2',
          500: '#519f92',
          600: '#367f75',
          700: '#28665f',
          800: '#205550',
          900: '#174a47',
          950: '#103834',
        },
      },
      fontFamily: {
        sans: ['Plus Jakarta Sans', 'Inter', 'system-ui', 'sans-serif'],
        display: ['Outfit', 'Cabinet Grotesk', 'sans-serif'],
      },
      boxShadow: {
        'pop': '0 10px 25px -5px rgba(54, 127, 117, 0.2), 0 8px 10px -6px rgba(54, 127, 117, 0.14)',
        'pop-lg': '0 20px 35px -10px rgba(54, 127, 117, 0.28), 0 10px 15px -5px rgba(54, 127, 117, 0.18)',
        'glow-teal': '0 0 30px rgba(116, 192, 178, 0.24)',
        'card-soft': '0 8px 28px rgba(23, 74, 71, 0.07)',
      },
      animation: {
        'float-slow': 'float 6s ease-in-out infinite',
        'float-medium': 'float 4s ease-in-out infinite 1s',
        'float-reverse': 'floatRev 5s ease-in-out infinite 0.5s',
        'pulse-subtle': 'pulseSubtle 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'shimmer': 'shimmer 2.5s infinite linear',
        'scan': 'scanLine 2s ease-in-out infinite',
      },
      keyframes: {
        float: {
          '0%, 100%': { transform: 'translateY(0px) rotate(0deg)' },
          '50%': { transform: 'translateY(-12px) rotate(1deg)' },
        },
        floatRev: {
          '0%, 100%': { transform: 'translateY(0px) rotate(0deg)' },
          '50%': { transform: 'translateY(10px) rotate(-1deg)' },
        },
        pulseSubtle: {
          '0%, 100%': { opacity: '1', transform: 'scale(1)' },
          '50%': { opacity: '0.9', transform: 'scale(1.02)' },
        },
        shimmer: {
          '0%': { backgroundPosition: '-200% 0' },
          '100%': { backgroundPosition: '200% 0' },
        },
        scanLine: {
          '0%': { top: '0%' },
          '50%': { top: '90%' },
          '100%': { top: '0%' },
        }
      }
    },
  },
  plugins: [],
}
