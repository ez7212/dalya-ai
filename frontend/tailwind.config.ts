import type { Config } from 'tailwindcss'

const config: Config = {
  content: ['./src/**/*.{js,ts,jsx,tsx,mdx}'],
  theme: {
    extend: {
      colors: {
        // Legacy gold palette — kept for backward compatibility with dashboard
        // and consumer marketing surfaces that have not migrated yet.
        gold:       '#C9A96E',
        'gold-lt':  '#DFC49A',
        'gold-dk':  '#B08848',
        copper:     '#B87333',
        ink:        '#1A2B3C',
        slate:      '#2E4057',
        deep:       '#0F1923',
        sage:       '#4A7C6F',
        'sage-lt':  '#6BA898',
        sand:       '#F5EFE6',
        'n-50':     '#FAFAF8',
        'n-200':    '#E8E0D5',
        'n-300':    '#C9BFB3',
        'n-500':    '#8A8078',
        'n-700':    '#4A4540',

        // B2B brand palette — slate blue, Phase 1-3 locked.
        // Wired to CSS vars defined in src/app/globals.css :root.
        brand: {
          50:  'var(--color-brand-50)',
          100: 'var(--color-brand-100)',
          200: 'var(--color-brand-200)',
          300: 'var(--color-brand-300)',
          400: 'var(--color-brand-400)',
          500: 'var(--color-brand-500)',
          600: 'var(--color-brand-600)',
          700: 'var(--color-brand-700)',
          800: 'var(--color-brand-800)',
          900: 'var(--color-brand-900)',
        },
        surface: {
          0:       'var(--color-surface-0)',
          1:       'var(--color-surface-1)',
          2:       'var(--color-surface-2)',
          overlay: 'var(--color-surface-overlay)',
        },
        text: {
          1: 'var(--color-text-1)',
          2: 'var(--color-text-2)',
          3: 'var(--color-text-3)',
        },
        neutral: {
          0:   '#FFFFFF',
          50:  '#FAFAF9',
          100: '#F4F4F2',
          200: '#E8E8E5',
          300: '#D6D6D2',
          400: '#A8A8A2',
          500: '#7B7B76',
          600: '#5C5C57',
          700: '#3D3D39',
          800: '#232320',
          900: '#161613',
        },
        success: {
          50:  '#E8F0EE',
          100: '#D0E1DD',
          500: '#4A7C6F',
          600: '#3D6A5E',
          700: '#2F5048',
          800: '#1F3530',
        },
        warning: {
          50:  '#FBF1E8',
          100: '#F4DFC8',
          500: '#B7793A',
          700: '#7A4F25',
          800: '#503517',
        },
        error: {
          50:  '#F7E8E5',
          100: '#EFCFC8',
          500: '#B84838',
          600: '#9D3829',
          700: '#7A2A1F',
          800: '#50180F',
        },
      },
      fontFamily: {
        sans: ['var(--font-jakarta)', 'system-ui', 'sans-serif'],
        mono: ['var(--font-jetbrains)', 'monospace'],
      },
      borderRadius: {
        DEFAULT: '4px',
        md: '8px',
        lg: '12px',
        xl: '16px',
        full: '9999px',
      },
    },
  },
  plugins: [],
}
export default config
