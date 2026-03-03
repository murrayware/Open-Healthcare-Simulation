// useTheme hook for easy access to centralized theme
import { useContext } from 'react';
import { useTheme as useMuiTheme } from '@mui/material/styles';
import { themeColors, getChartConfig, apexChartsTheme } from './index';

export const useAppTheme = () => {
  const muiTheme = useMuiTheme();
  
  return {
    // Material UI theme
    mui: muiTheme,
    
    // Color palette
    colors: themeColors,
    
    // Chart configurations
    charts: {
      getConfig: getChartConfig,
      baseConfig: apexChartsTheme.baseConfig,
      lineConfig: (customOptions = {}) => getChartConfig('line', customOptions),
      barConfig: (customOptions = {}) => getChartConfig('bar', customOptions),
      ganttConfig: (customOptions = {}) => getChartConfig('gantt', customOptions),
    },
    
    // Utility functions for styling
    utils: {
      // Get CSS custom property value
      getCSSVar: (varName) => {
        return getComputedStyle(document.documentElement)
          .getPropertyValue(varName)
          .trim();
      },
      
      // Set CSS custom property value
      setCSSVar: (varName, value) => {
        document.documentElement.style.setProperty(varName, value);
      },
      
      // Get semantic color based on theme
      getSemanticColor: (semantic, variant = 'main') => {
        const colorMap = {
          primary: themeColors.primary[variant],
          secondary: themeColors.secondary[variant],
          success: themeColors.success[variant],
          error: themeColors.error[variant],
          warning: themeColors.warning[variant],
          info: themeColors.info[variant],
        };
        return colorMap[semantic] || themeColors.primary[variant];
      },
      
      // Get chart color by index
      getChartColor: (index) => {
        return themeColors.chart.series[index % themeColors.chart.series.length];
      },
      
      // Generate Tailwind classes with theme colors
      getTailwindClass: (property, color, variant = 'main') => {
        const value = themeColors[color]?.[variant] || color;
        return `${property}-[${value}]`;
      },
    },
    
    // Theme switching utilities (for future light/dark mode toggle)
    mode: {
      current: 'dark',
      toggle: () => {
        // Future implementation for theme switching
        console.warn('Theme switching not yet implemented');
      },
    },
  };
};

export default useAppTheme;