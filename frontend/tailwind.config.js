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
          50: '#eaf8f9',
          100: '#d2f0f2',
          200: '#a5e1e6',
          300: '#71d0d8',
          400: '#32bac7',
          500: '#009ead',
          600: '#007e8a',
          700: '#006873',
        },
        pet: {
          50: '#f2f6f7',
          100: '#e3ecef',
          500: '#526e7e',
          600: '#405b6b',
          700: '#324d5c',
          900: '#243b49',
        },
        primary: {
          50: '#eaf8f9',
          100: '#d2f0f2',
          200: '#a5e1e6',
          300: '#71d0d8',
          400: '#32bac7',
          500: '#009ead',
          600: '#007e8a',
          700: '#006873',
          800: '#205460',
          900: '#243b49',
        },
      },
    },
  },
  plugins: [],
}
