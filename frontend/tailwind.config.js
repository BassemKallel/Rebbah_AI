/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/**/*.{js,jsx,ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          DEFAULT:  '#0f6885',
          dark:     '#0d5a72',
          darker:   '#0a4a5e',
          light:    '#eef6f9',
          muted:    '#dceef5',
        },
      },
      fontFamily: {
        sans: ['Inter', 'ui-sans-serif', 'system-ui', '-apple-system', 'sans-serif'],
      },
      screens: {
        xs: '375px',
      },
      boxShadow: {
        'card': '0 1px 3px rgba(0,0,0,0.06), 0 1px 2px rgba(0,0,0,0.04)',
        'panel': '0 4px 24px rgba(0,0,0,0.08)',
        'sidebar': '2px 0 8px rgba(0,0,0,0.04)',
      },
      transitionDuration: {
        '200': '200ms',
      },
    },
  },
  plugins: [],
}

