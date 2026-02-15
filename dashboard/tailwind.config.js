/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Custom colors for trading dashboard
        profit: {
          light: '#dcfce7',
          DEFAULT: '#22c55e',
          dark: '#166534',
        },
        loss: {
          light: '#fee2e2',
          DEFAULT: '#ef4444',
          dark: '#991b1b',
        },
        neutral: {
          light: '#f3f4f6',
          DEFAULT: '#6b7280',
          dark: '#374151',
        },
      },
      fontFamily: {
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
    },
  },
  plugins: [],
}
