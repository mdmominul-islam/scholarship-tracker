/** @type {import('tailwindcss').Config} */
export default {
  darkMode: ['selector', '[data-theme="dark"]'],
  content: ['./src/**/*.{astro,html,js,jsx,ts,tsx}'],
  theme: { extend: { colors: { navy: '#173B57', teal: '#168C83' } } },
  plugins: []
};