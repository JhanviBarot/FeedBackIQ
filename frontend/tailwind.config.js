/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        primary: { DEFAULT: '#0F6E56', dark: '#094D3C', light: '#E8F5F1' },
        error: '#C0392B',
        warning: '#E67E22',
        success: '#27AE60',
        muted: '#888888',
        border: '#CCCCCC',
        surface: '#FAFAF8',
      },
    },
  },
  plugins: [],
};
