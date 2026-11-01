/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        // HR Buddy brand: a calm ink blue
        brand: {
          50: '#f1f4ff', 100: '#e2e8ff', 200: '#c9d4fe', 300: '#a3b4fc', 400: '#7a8cf7',
          500: '#5a68ef', 600: '#4450e3', 700: '#3840c8', 800: '#2f37a1', 900: '#2b337f',
        },
      },
      fontFamily: {
        sans: ['Inter', 'ui-sans-serif', 'system-ui', '-apple-system', '"Segoe UI"', 'Roboto', '"Helvetica Neue"', 'Arial', 'sans-serif'],
      },
      boxShadow: {
        card: '0 1px 2px 0 rgb(16 24 40 / 0.04)',
        pop: '0 8px 24px -6px rgb(16 24 40 / 0.12), 0 2px 6px -2px rgb(16 24 40 / 0.06)',
      },
    },
  },
  plugins: [],
}
