/** @type {import('tailwindcss').Config} */

/**
 * Design tokens for the control-room aesthetic.
 *
 * The palette is a cool, desaturated slate so that status colour — the
 * only thing an operator needs to react to — is the brightest element
 * on screen. Severity hues are deliberately spaced far apart in hue and
 * luminance so they remain distinguishable at a glance, on a wall
 * display, and for the most common forms of colour blindness.
 */
export default {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        surface: {
          950: '#070A0F',
          900: '#0B1017',
          850: '#101722',
          800: '#151E2B',
          750: '#1B2634',
          700: '#22303F',
          600: '#2E3F52',
        },
        content: {
          primary: '#E8EEF6',
          secondary: '#9AAABF',
          muted: '#64748B',
        },
        severity: {
          info: '#38BDF8',
          low: '#22D3EE',
          medium: '#FBBF24',
          high: '#FB7185',
          critical: '#EF4444',
        },
        status: {
          active: '#FB7185',
          acknowledged: '#FBBF24',
          resolved: '#34D399',
          expired: '#64748B',
        },
        accent: {
          DEFAULT: '#22D3EE',
          soft: '#0E7490',
        },
      },
      fontFamily: {
        sans: ['Inter', 'Segoe UI', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Cascadia Mono', 'Consolas', 'monospace'],
      },
      boxShadow: {
        panel: '0 1px 2px rgba(0,0,0,.4), 0 8px 24px -12px rgba(0,0,0,.6)',
        glow: '0 0 0 1px rgba(34,211,238,.25), 0 0 24px -6px rgba(34,211,238,.35)',
      },
      keyframes: {
        shimmer: {
          '100%': { transform: 'translateX(100%)' },
        },
        'pulse-ring': {
          '0%': { transform: 'scale(.85)', opacity: '.8' },
          '70%': { transform: 'scale(1.6)', opacity: '0' },
          '100%': { opacity: '0' },
        },
        'fade-in': {
          from: { opacity: '0', transform: 'translateY(4px)' },
          to: { opacity: '1', transform: 'none' },
        },
      },
      animation: {
        shimmer: 'shimmer 1.6s infinite',
        'pulse-ring': 'pulse-ring 2s cubic-bezier(0.4,0,0.6,1) infinite',
        'fade-in': 'fade-in .25s ease-out both',
      },
    },
  },
  plugins: [],
};
