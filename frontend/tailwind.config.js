/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        obsidian: {
          DEFAULT: '#070b0a',
          900: '#070b0a',
          800: '#0c1210',
          700: '#141c19',
          600: '#1d2925'
        },
        cyber: {
          cyan: '#38bdf8',
          blue: '#3b82f6',
          emerald: '#10b981',
          violet: '#8b5cf6',
          amber: '#f59e0b'
        }
      },
      fontFamily: {
        sans: ['Inter', 'Plus Jakarta Sans', '-apple-system', 'BlinkMacSystemFont', 'sans-serif'],
        serif: ['"Instrument Serif"', 'Georgia', 'serif'],
        mono: ['"JetBrains Mono"', 'Menlo', 'monospace']
      },
      boxShadow: {
        'glow-cyan': '0 0 25px -5px rgba(56, 189, 248, 0.25)',
        'glow-emerald': '0 0 25px -5px rgba(16, 185, 129, 0.25)',
        'glass-inset': 'inset 0 1px 1px 0 rgba(255, 255, 255, 0.12)'
      }
    },
  },
  plugins: [],
}
