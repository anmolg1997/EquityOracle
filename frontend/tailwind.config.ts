import type { Config } from 'tailwindcss';

const config: Config = {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        brand: {
          50: '#f0f7ff',
          100: '#e0effe',
          200: '#b9dffd',
          300: '#7cc5fb',
          400: '#36a8f6',
          500: '#0c8de7',
          600: '#006fc5',
          700: '#0059a0',
          800: '#054c84',
          900: '#0a406e',
        },
        circuit: {
          green: '#22c55e',
          amber: '#f59e0b',
          red: '#ef4444',
          black: '#1f2937',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
    },
  },
  plugins: [],
};

export default config;
