/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        'perscholas': {
          'primary': '#006fb4',    // Medium blue (buttons)
          'dark': '#00476e',       // Dark blue (tags)
          'secondary': '#009ee0',  // Light blue accent
          'accent': '#fec14f',     // Yellow
          'light': '#f8fafc',      // Light background
        }
      },
    },
  },
  plugins: [],
}