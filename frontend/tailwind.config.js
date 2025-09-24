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
          'primary': '#0066CC',    // Per Scholas blue
          'secondary': '#004499',  // Darker blue
          'accent': '#FF9900',     // Orange accent
          'light': '#f8fafc',      // Light background
        }
      },
    },
  },
  plugins: [],
}