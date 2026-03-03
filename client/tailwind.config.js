/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      // Colors using CSS custom properties from our centralized theme
      colors: {
        primary: {
          DEFAULT: 'var(--color-primary)',
          dark: 'var(--color-primary-dark)',
          light: 'var(--color-primary-light)',
        },
        secondary: {
          DEFAULT: 'var(--color-secondary)',
          dark: 'var(--color-secondary-dark)',
          light: 'var(--color-secondary-light)',
        },
        background: {
          DEFAULT: 'var(--color-bg)',
          surface: 'var(--color-surface)',
          elevated: 'var(--color-surface-elevated)',
        },
        text: {
          primary: 'var(--color-text-primary)',
          secondary: 'var(--color-text-secondary)',
          disabled: 'var(--color-text-disabled)',
        },
        success: 'var(--color-success)',
        error: 'var(--color-error)',
        warning: 'var(--color-warning)',
        info: 'var(--color-info)',
        border: {
          DEFAULT: 'var(--color-border)',
          secondary: 'var(--color-border-secondary)',
          focus: 'var(--color-border-focus)',
        },
      },
      
      // Spacing using CSS custom properties
      spacing: {
        'xs': 'var(--spacing-xs)',
        'sm': 'var(--spacing-sm)',
        'md': 'var(--spacing-md)',
        'lg': 'var(--spacing-lg)',
        'xl': 'var(--spacing-xl)',
        '2xl': 'var(--spacing-2xl)',
      },
      
      // Border radius using CSS custom properties
      borderRadius: {
        'sm': 'var(--radius-sm)',
        'md': 'var(--radius-md)',
        'lg': 'var(--radius-lg)',
        'xl': 'var(--radius-xl)',
      },
      
      // Box shadows using CSS custom properties
      boxShadow: {
        'sm': 'var(--shadow-sm)',
        'md': 'var(--shadow-md)',
        'lg': 'var(--shadow-lg)',
      },
      
      // Font family
      fontFamily: {
        sans: ['"Inter"', '"Roboto"', '"Helvetica"', '"Arial"', 'sans-serif'],
      },
      
      // Animation and transitions
      animation: {
        'fade-in': 'fadeIn 0.3s ease-in-out',
        'slide-in': 'slideIn 0.3s ease-out',
        'scale-in': 'scaleIn 0.2s ease-out',
      },
      
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideIn: {
          '0%': { transform: 'translateY(-10px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
        scaleIn: {
          '0%': { transform: 'scale(0.95)', opacity: '0' },
          '100%': { transform: 'scale(1)', opacity: '1' },
        },
      },
    },
  },
  plugins: [
    // Custom plugin for additional utilities
    function({ addUtilities, theme }) {
      addUtilities({
        // Surface utilities
        '.surface': {
          backgroundColor: 'var(--color-surface)',
          border: '1px solid var(--color-border-secondary)',
          borderRadius: 'var(--radius-lg)',
        },
        '.surface-elevated': {
          backgroundColor: 'var(--color-surface-elevated)',
          border: '1px solid var(--color-border)',
          borderRadius: 'var(--radius-lg)',
          boxShadow: 'var(--shadow-md)',
        },
        
        // Text utilities
        '.text-primary': {
          color: 'var(--color-text-primary)',
        },
        '.text-secondary': {
          color: 'var(--color-text-secondary)',
        },
        '.text-disabled': {
          color: 'var(--color-text-disabled)',
        },
        
        // Button utilities
        '.btn-primary': {
          backgroundColor: 'var(--color-primary)',
          color: 'var(--color-text-primary)',
          borderRadius: 'var(--radius-md)',
          padding: 'var(--spacing-sm) var(--spacing-md)',
          fontWeight: '500',
          transition: 'all 0.2s ease',
          '&:hover': {
            backgroundColor: 'var(--color-primary-dark)',
          },
        },
        '.btn-secondary': {
          backgroundColor: 'transparent',
          color: 'var(--color-primary)',
          border: '1px solid var(--color-primary)',
          borderRadius: 'var(--radius-md)',
          padding: 'var(--spacing-sm) var(--spacing-md)',
          fontWeight: '500',
          transition: 'all 0.2s ease',
          '&:hover': {
            backgroundColor: 'var(--color-primary)',
            color: 'var(--color-text-primary)',
          },
        },
        
        // Card utilities
        '.card': {
          backgroundColor: 'var(--color-surface)',
          border: '1px solid var(--color-border-secondary)',
          borderRadius: 'var(--radius-lg)',
          padding: 'var(--spacing-lg)',
        },
        '.card-elevated': {
          backgroundColor: 'var(--color-surface-elevated)',
          border: '1px solid var(--color-border)',
          borderRadius: 'var(--radius-lg)',
          padding: 'var(--spacing-lg)',
          boxShadow: 'var(--shadow-md)',
        },
        
        // Input utilities
        '.input': {
          backgroundColor: 'var(--color-surface)',
          border: '1px solid var(--color-border)',
          borderRadius: 'var(--radius-md)',
          padding: 'var(--spacing-sm) var(--spacing-md)',
          color: 'var(--color-text-primary)',
          '&:focus': {
            outline: 'none',
            borderColor: 'var(--color-border-focus)',
            boxShadow: '0 0 0 2px var(--color-primary)',
          },
        },
        
        // Scrollbar utilities
        '.scrollbar-thin': {
          '&::-webkit-scrollbar': {
            width: '8px',
            height: '8px',
          },
          '&::-webkit-scrollbar-track': {
            background: 'var(--color-surface)',
          },
          '&::-webkit-scrollbar-thumb': {
            background: 'var(--color-border)',
            borderRadius: 'var(--radius-sm)',
          },
          '&::-webkit-scrollbar-thumb:hover': {
            background: 'var(--color-text-secondary)',
          },
        },
      });
    },
  ],
};