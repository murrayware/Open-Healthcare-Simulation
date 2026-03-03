// Central Theme Configuration
// This file manages all styling for Material UI, ApexCharts, and CSS custom properties

import { createTheme,alpha } from '@mui/material/styles';

// Base color palette - modify these to change the entire app theme
export const themeColors = {
  // Primary colors
  primary: {
    // main: '#22c55e',      // Green accent
    // dark: '#16a34a',
    // light: '#4ade80',
    // contrastText: '#ffffff',
        main: '#3b82f6',      // Blue
    dark: '#2563eb',
    light: '#60a5fa',
    contrastText: '#ffffff',
  },
  
  // Secondary colors
  secondary: {
    main: '#3b82f6',      // Blue
    dark: '#2563eb',
    light: '#60a5fa',
    contrastText: '#ffffff',
  },
  
  // Background 
  background: {
    default: '#141a21',    // Main background
    paper: '#1c252e',      // Cards, panels
    surface: '#233140',    // Elevated surfaces
    elevated: '#2a3441',   // Higher elevation
    sidebar: '#141a21',    // Dedicated sidebar color
  },
  
  // Text colors
  text: {
    primary: '#ffffff',
    secondary: '#9ca3af',
    disabled: '#6b7280',
    hint: '#9ca3af',
  },
  
  // State colors
  success: {
    main: '#22c55e',
    dark: '#16a34a',
    light: '#4ade80',
    contrastText: '#ffffff',
  },
  
  error: {
    main: '#ef4444',
    dark: '#dc2626',
    light: '#f87171',
    contrastText: '#ffffff',
  },
  
  warning: {
    main: '#f59e0b',
    dark: '#d97706',
    light: '#fbbf24',
    contrastText: '#ffffff',
  },
  
  info: {
    main: '#3b82f6',
    dark: '#2563eb',
    light: '#60a5fa',
    contrastText: '#ffffff',
  },
  
  // Chart specific colors
  chart: {
    grid: 'rgba(255,255,255,0.06)',
    axis: '#9ca3af',
    tooltip: '#2a3441',
    series: ['#22c55e', '#3b82f6', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4', '#f97316', '#ec4899'],
  },
  
  // Border colors
  border: {
    primary: 'rgba(255,255,255,0.12)',
    secondary: 'rgba(255,255,255,0.06)',
    focus: '#22c55e',
  },
};

// Material UI Theme
export const muiTheme = createTheme({
  palette: {
    mode: 'dark',
    primary: themeColors.primary,
    secondary: themeColors.secondary,
    background: themeColors.background,
    text: themeColors.text,
    success: themeColors.success,
    error: themeColors.error,
    warning: themeColors.warning,
    info: themeColors.info,
    divider: themeColors.border.primary,
  },
  
  typography: {
    fontFamily: '"Inter", "Roboto", "Helvetica", "Arial", sans-serif',
    h1: { fontWeight: 600, color: themeColors.text.primary },
    h2: { fontWeight: 600, color: themeColors.text.primary },
    h3: { fontWeight: 600, color: themeColors.text.primary },
    h4: { fontWeight: 600, color: themeColors.text.primary },
    h5: { fontWeight: 600, color: themeColors.text.primary },
    h6: { fontWeight: 600, color: themeColors.text.primary },
    body1: { color: themeColors.text.primary },
    body2: { color: themeColors.text.secondary },
  },
  
  components: {
    MuiCssBaseline: {
      styleOverrides: {
        body: {
          backgroundColor: themeColors.background.default,
          color: themeColors.text.primary,
        },
      },
    },
    
    MuiAppBar: {
      styleOverrides: {
        root: {
          backgroundColor: themeColors.background.default,
          borderBottom: `1px solid ${themeColors.border.primary}`,
        },
      },
    },
    
    MuiDrawer: {
      styleOverrides: {
        paper: {
          backgroundColor: themeColors.background.sidebar,
          borderRight: `1px solid ${themeColors.border.primary}`,
        },
      },
    },
    
    MuiCard: {
      styleOverrides: {
        root: {
          backgroundColor: themeColors.background.paper,
          border: `1px solid ${themeColors.border.secondary}`,
          borderRadius: 2,
        },
      },
    },
    
    // MuiButton: {
    //   styleOverrides: {
    //     root: {
    //       borderRadius: 2,
    //       textTransform: 'none',
    //       fontWeight: 500,
    //     },
    //     contained: {
    //       boxShadow: 'none',
    //       '&:hover': {
    //         boxShadow: 'none',
    //       },
    //     },
    //   },
    // },
    
    MuiTextField: {
      styleOverrides: {
        root: {
          '& .MuiOutlinedInput-root': {
            '& fieldset': {
              borderColor: themeColors.border.primary,
            },
            '&:hover fieldset': {
              borderColor: themeColors.border.primary,
            },
            '&.Mui-focused fieldset': {
              borderColor: themeColors.primary.main,
            },
          },
        },
      },
    },
    
    MuiTab: {
      styleOverrides: {
        root: {
          textTransform: 'none',
          fontWeight: 500,
          '&.Mui-selected': {
            color: themeColors.primary.main,
          },
        },
      },
    },
    
    MuiTabs: {
      styleOverrides: {
        indicator: {
          backgroundColor: themeColors.primary.main,
        },
      },
    },
    
    MuiListItemButton: {
      styleOverrides: {
        root: {
          minHeight: 48,
          paddingLeft: 20,
          paddingRight: 20,
          borderRadius: 4,
          marginLeft: 8,
          marginRight: 8,
          marginBottom: 4,
          backgroundColor: alpha(themeColors.background.surface, 0),
          '&:hover': {
            backgroundColor: alpha(themeColors.background.elevated, 0.5),
          },
          '&.Mui-selected': {
            backgroundColor: alpha(themeColors.primary.main, 0.1),
            color: themeColors.primary.main,
            '& .MuiListItemIcon-root': {
              color: themeColors.primary.light,
            },
            '& .MuiListItemText-root .MuiTypography-root': {
              color: themeColors.primary.light,
            },
            '&:hover': {
              backgroundColor: alpha(themeColors.primary.main, 0.3),
            },
          },
          // Simulations nested items
          '&.simulation-item': {
            minHeight: 40,
            paddingLeft: 32,
            paddingRight: 8,
          },
        },
      },
    },
    
    MuiListItemIcon: {
      styleOverrides: {
        root: {
          minWidth: 0,
          marginRight: 24,
          justifyContent: 'center',
          color: themeColors.text.secondary,
        },
      },
    },
    
    MuiListItemText: {
      styleOverrides: {
        root: {
          '& .MuiTypography-root': {
            color: themeColors.text.secondary,
            fontWeight:550
          },
        },
      },
    },
  },
});

// ApexCharts Theme Configuration
export const apexChartsTheme = {
  // Base chart configuration that all charts should extend
  baseConfig: {
    chart: {
      background: 'transparent',
      toolbar: { show: false },
      zoom: { enabled: false },
      selection: { enabled: false },
      pan: { enabled: false },
      animations: {
        enabled: true,
        easing: 'easeinout',
        speed: 300,
      },
    },
    
    theme: { 
      mode: 'dark',
      palette: 'palette1',
    },
    
    colors: themeColors.chart.series,
    
    dataLabels: { 
      enabled: false,
      style: {
        colors: [themeColors.text.primary],
      },
    },
    
    grid: { 
      borderColor: themeColors.chart.grid,
      strokeDashArray: 3,
    },
    
    xaxis: { 
      labels: { 
        style: { 
          colors: themeColors.chart.axis,
          fontSize: '12px',
        }
      }, 
      title: { 
        style: { 
          color: themeColors.chart.axis,
          fontSize: '13px',
          fontWeight: 500,
        }
      },
      axisBorder: {
        color: themeColors.border.primary,
      },
      axisTicks: {
        color: themeColors.border.primary,
      },
    },
    
    yaxis: { 
      labels: { 
        style: { 
          colors: themeColors.chart.axis,
          fontSize: '12px',
        }
      }, 
      title: { 
        style: { 
          color: themeColors.chart.axis,
          fontSize: '13px',
          fontWeight: 500,
        }
      },
    },
    
    legend: {
      labels: {
        colors: themeColors.text.primary,
      },
    },
    
    tooltip: {
      theme: 'dark',
      style: {
        fontSize: '12px',
      },
      fillSeriesColor: false,
    },
    
    stroke: {
      width: 2,
    },
    
    fill: {
      opacity: 0.8,
    },
  },
  
  // Specific chart type configurations
  lineChart: {
    stroke: {
      curve: 'smooth',
      width: 3,
    },
    markers: {
      size: 4,
      hover: {
        size: 6,
      },
    },
  },
  
  barChart: {
    plotOptions: {
      bar: {
        borderRadius: 4,
        columnWidth: '60%',
      },
    },
  },
  
  ganttChart: {
    plotOptions: {
      bar: {
        horizontal: true,
        barHeight: '80%',
        rangeBarGroupRows: true,
      },
    },
    fill: {
      type: 'solid',
      opacity: 0.6,
    },
  },
};

// CSS Custom Properties for Tailwind
export const cssCustomProperties = {
  // Colors
  '--color-primary': themeColors.primary.main,
  '--color-primary-dark': themeColors.primary.dark,
  '--color-primary-light': themeColors.primary.light,
  
  '--color-secondary': themeColors.secondary.main,
  '--color-secondary-dark': themeColors.secondary.dark,
  '--color-secondary-light': themeColors.secondary.light,
  
  '--color-bg': themeColors.background.default,
  '--color-surface': themeColors.background.paper,
  '--color-surface-elevated': themeColors.background.surface,
  '--color-sidebar': themeColors.background.sidebar,
  
  '--color-text-primary': themeColors.text.primary,
  '--color-text-secondary': themeColors.text.secondary,
  '--color-text-disabled': themeColors.text.disabled,
  
  '--color-success': themeColors.success.main,
  '--color-error': themeColors.error.main,
  '--color-warning': themeColors.warning.main,
  '--color-info': themeColors.info.main,
  
  '--color-border': themeColors.border.primary,
  '--color-border-secondary': themeColors.border.secondary,
  '--color-border-focus': themeColors.border.focus,
  
  // Spacing (can be used with Tailwind arbitrary values)
  '--spacing-xs': '0.25rem',
  '--spacing-sm': '0.5rem',
  '--spacing-md': '1rem',
  '--spacing-lg': '1.5rem',
  '--spacing-xl': '2rem',
  '--spacing-2xl': '3rem',
  
  // Border radius
  '--radius-sm': '4px',
  '--radius-md': '6px',
  '--radius-lg': '8px',
  '--radius-xl': '12px',
  
  // Shadows
  '--shadow-sm': '0 1px 2px 0 rgba(0, 0, 0, 0.05)',
  '--shadow-md': '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
  '--shadow-lg': '0 10px 15px -3px rgba(0, 0, 0, 0.1)',
};

// Utility function to apply CSS custom properties
export const applyCSSCustomProperties = () => {
  const root = document.documentElement;
  Object.entries(cssCustomProperties).forEach(([property, value]) => {
    root.style.setProperty(property, value);
  });
};

// Helper functions for chart configurations
export const getChartConfig = (type = 'base', customOptions = {}) => {
  let config = { ...apexChartsTheme.baseConfig };
  
  // Apply type-specific configurations
  switch (type) {
    case 'line':
      config = { ...config, ...apexChartsTheme.lineChart };
      break;
    case 'bar':
      config = { ...config, ...apexChartsTheme.barChart };
      break;
    case 'gantt':
      config = { ...config, ...apexChartsTheme.ganttChart };
      break;
  }
  
  // Deep merge custom options
  return deepMerge(config, customOptions);
};

// Deep merge utility function
function deepMerge(target, source) {
  const output = { ...target };
  
  if (isObject(target) && isObject(source)) {
    Object.keys(source).forEach(key => {
      if (isObject(source[key])) {
        if (!(key in target)) {
          Object.assign(output, { [key]: source[key] });
        } else {
          output[key] = deepMerge(target[key], source[key]);
        }
      } else {
        Object.assign(output, { [key]: source[key] });
      }
    });
  }
  
  return output;
}

function isObject(item) {
  return item && typeof item === 'object' && !Array.isArray(item);
}

export default {
  muiTheme,
  apexChartsTheme,
  themeColors,
  cssCustomProperties,
  applyCSSCustomProperties,
  getChartConfig,
};

// Export the theme hook
export { default as useAppTheme } from './useTheme';