/** @type {import('tailwindcss').Config} */

/**
 * Industrial control-room design tokens.
 *
 * Two decisions drive the whole palette:
 *
 * 1. Surfaces are neutral graphite, not blue-tinted slate. A cool cast
 *    competes with the status colours; a true neutral lets emerald,
 *    amber and red read as the only saturated things on screen.
 *
 * 2. Status colour is reserved exclusively for state. Nothing decorative
 *    is ever emerald, amber or red — so when an operator sees one, it
 *    always means something.
 */
export default {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        // Page background — the darkest value in the system.
        void: '#070809',

        // Panel surfaces: charcoal → graphite → gunmetal as elevation
        // rises. Steps are deliberately small; large jumps read as
        // consumer software rather than instrumentation.
        panel: {
          DEFAULT: '#0E1013',
          raised: '#131619',
          inset: '#0A0C0E',
          rail: '#16191D',
        },
        edge: {
          DEFAULT: '#1F2429',
          strong: '#2A3138',
          soft: '#171B1F',
        },
        ink: {
          DEFAULT: '#E6E9EC',
          dim: '#98A2AC',
          faint: '#5E6873',
          ghost: '#3C444D',
        },

        // Status vocabulary. `safe` is never used decoratively.
        safe: {
          DEFAULT: '#10B981',
          dim: '#059669',
          glow: 'rgba(16,185,129,0.14)',
        },
        warn: {
          DEFAULT: '#F59E0B',
          dim: '#D97706',
          glow: 'rgba(245,158,11,0.14)',
        },
        crit: {
          DEFAULT: '#EF4444',
          dim: '#DC2626',
          glow: 'rgba(239,68,68,0.16)',
        },
        info: {
          DEFAULT: '#3B82F6',
          dim: '#2563EB',
          glow: 'rgba(59,130,246,0.14)',
        },
      },

      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'Segoe UI', 'sans-serif'],
        mono: ['JetBrains Mono Variable', 'JetBrains Mono', 'Consolas', 'monospace'],
      },

      fontSize: {
        // Dense instrumentation type ramp.
        '2xs': ['0.6875rem', { lineHeight: '1rem', letterSpacing: '0.04em' }],
        kpi: ['2.25rem', { lineHeight: '1', letterSpacing: '-0.03em' }],
        'kpi-lg': ['2.75rem', { lineHeight: '1', letterSpacing: '-0.035em' }],
      },

      borderRadius: {
        // Restrained radii: industrial equipment has tight corners.
        panel: '4px',
        control: '3px',
      },

      boxShadow: {
        panel: '0 1px 0 0 rgba(255,255,255,0.03) inset, 0 8px 24px -16px rgba(0,0,0,0.9)',
        well: 'inset 0 1px 3px rgba(0,0,0,0.55)',
        'rail-safe': 'inset 2px 0 0 0 #10B981',
        'rail-warn': 'inset 2px 0 0 0 #F59E0B',
        'rail-crit': 'inset 2px 0 0 0 #EF4444',
        'rail-info': 'inset 2px 0 0 0 #3B82F6',
      },

      backgroundImage: {
        // Faint scan lines for recessed data wells.
        scanlines:
          'repeating-linear-gradient(0deg, rgba(255,255,255,0.014) 0px, rgba(255,255,255,0.014) 1px, transparent 1px, transparent 3px)',
      },

      keyframes: {
        sweep: { '100%': { transform: 'translateX(100%)' } },
        'led-pulse': {
          '0%,100%': { opacity: '1' },
          '50%': { opacity: '0.35' },
        },
        'ring-out': {
          '0%': { transform: 'scale(0.8)', opacity: '0.7' },
          '100%': { transform: 'scale(2.4)', opacity: '0' },
        },
        'rise-in': {
          from: { opacity: '0', transform: 'translateY(6px)' },
          to: { opacity: '1', transform: 'none' },
        },
        'row-in': {
          from: { opacity: '0', transform: 'translateX(-4px)' },
          to: { opacity: '1', transform: 'none' },
        },
        ticker: {
          '0%': { opacity: '0.45' },
          '50%': { opacity: '1' },
          '100%': { opacity: '0.45' },
        },
      },
      animation: {
        sweep: 'sweep 1.4s cubic-bezier(0.4,0,0.2,1) infinite',
        'led-pulse': 'led-pulse 1.8s ease-in-out infinite',
        'ring-out': 'ring-out 1.8s cubic-bezier(0.4,0,0.6,1) infinite',
        'rise-in': 'rise-in 0.28s cubic-bezier(0.16,1,0.3,1) both',
        'row-in': 'row-in 0.22s ease-out both',
        ticker: 'ticker 2.4s ease-in-out infinite',
      },

      transitionTimingFunction: {
        instrument: 'cubic-bezier(0.16, 1, 0.3, 1)',
      },
    },
  },
  plugins: [],
};
