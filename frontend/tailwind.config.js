/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/**/*.{html,ts}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Poppins', 'system-ui', 'sans-serif'],
      },
      colors: {
        brand: {
          50: '#effafb',
          100: '#d9f3f5',
          200: '#aee5e9',
          300: '#75cfd6',
          400: '#39b2be',
          500: '#1a98a2',
          600: '#147d87',
          700: '#12646e',
        },
        pet: {
          50: '#f1f4fa',
          100: '#e4eaf4',
          500: '#425298',
          600: '#273879',
          700: '#152665',
          900: '#0b1b6d',
        },
        primary: {
          50: '#eff6ff',
          100: '#dbeafe',
          200: '#bfdbfe',
          300: '#93c5fd',
          400: '#60a5fa',
          500: '#3b82f6',
          600: '#2563eb',
          700: '#1d4ed8',
          800: '#1e40af',
          900: '#1e3a8a',
        },
      },
    },
  },
  plugins: [],
}
