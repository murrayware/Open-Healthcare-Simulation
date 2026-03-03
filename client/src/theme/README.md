# Centralized Theme System

This project uses a centralized theme system that manages styling for Material UI, ApexCharts, and CSS custom properties. All styling is configured in one place to ensure consistency and easy maintenance.

## Overview

The theme system provides:
- **Material UI Theme** - Complete dark theme configuration
- **ApexCharts Theme** - Consistent chart styling across all charts
- **CSS Custom Properties** - For Tailwind CSS and custom styling
- **Theme Hook** - Easy access to theme values in components

## File Structure

```
src/theme/
├── index.js          # Main theme configuration
├── useTheme.js       # Theme hook for components
└── README.md         # This documentation
```

## Usage

### 1. Material UI Components

Material UI components automatically use the centralized theme. No additional configuration needed.

```jsx
import { Button, Card, TextField } from '@mui/material';

// These will automatically use the centralized theme
<Button variant="contained">Primary Button</Button>
<Card>Content</Card>
<TextField label="Input" />
```

### 2. ApexCharts

Import and use the `getChartConfig` function for consistent chart styling:

```jsx
import { getChartConfig } from '../theme';

// Basic chart configuration
const chartOptions = getChartConfig('line');

// Chart with custom options (merged with theme)
const customChartOptions = getChartConfig('bar', {
  chart: { height: 400 },
  title: { text: 'Custom Title' }
});

// Available chart types: 'base', 'line', 'bar', 'gantt'
```

### 3. CSS Custom Properties (Tailwind)

Use CSS custom properties in your styles:

```css
.my-component {
  background-color: var(--color-surface);
  color: var(--color-text-primary);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
}
```

### 4. Tailwind CSS Classes

Use the extended Tailwind classes:

```jsx
<div className="surface p-lg rounded-lg">
  <h2 className="text-primary">Title</h2>
  <p className="text-secondary">Description</p>
  <button className="btn-primary">Action</button>
</div>
```

### 5. Theme Hook

Use the `useAppTheme` hook for programmatic access:

```jsx
import { useAppTheme } from '../theme/useTheme';

function MyComponent() {
  const theme = useAppTheme();
  
  // Access colors
  const primaryColor = theme.colors.primary.main;
  
  // Get chart configuration
  const chartConfig = theme.charts.lineConfig({ title: { text: 'My Chart' } });
  
  // Use utilities
  const chartColor = theme.utils.getChartColor(0);
  const cssValue = theme.utils.getCSSVar('--color-primary');
  
  return (
    <div style={{ backgroundColor: primaryColor }}>
      {/* Component content */}
    </div>
  );
}
```

## Theme Configuration

### Colors

All colors are defined in `src/theme/index.js` in the `themeColors` object:

```javascript
export const themeColors = {
  primary: { main: '#22c55e', dark: '#16a34a', light: '#4ade80' },
  secondary: { main: '#3b82f6', dark: '#2563eb', light: '#60a5fa' },
  background: { default: '#141a21', paper: '#1c252e', surface: '#233140' },
  // ... more colors
};
```

### Chart Colors

Chart series colors are defined in `themeColors.chart.series`:

```javascript
chart: {
  series: ['#22c55e', '#3b82f6', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4'],
}
```

### Spacing and Sizing

Consistent spacing is defined in `cssCustomProperties`:

```javascript
'--spacing-xs': '0.25rem',
'--spacing-sm': '0.5rem',
'--spacing-md': '1rem',
// ... more spacing
```

## Customizing the Theme

### 1. Change Colors

Edit the `themeColors` object in `src/theme/index.js`:

```javascript
export const themeColors = {
  primary: {
    main: '#your-color',    // Change this
    dark: '#darker-shade',
    light: '#lighter-shade',
  },
  // ... other colors
};
```

### 2. Add New Colors

Add new color definitions:

```javascript
export const themeColors = {
  // ... existing colors
  accent: {
    main: '#ff6b6b',
    dark: '#ee5a52',
    light: '#ff8a80',
  },
};
```

Then add corresponding CSS custom properties:

```javascript
export const cssCustomProperties = {
  // ... existing properties
  '--color-accent': themeColors.accent.main,
  '--color-accent-dark': themeColors.accent.dark,
};
```

### 3. Modify Chart Defaults

Edit the `apexChartsTheme.baseConfig` object:

```javascript
export const apexChartsTheme = {
  baseConfig: {
    // ... existing config
    stroke: {
      width: 3,  // Change default stroke width
    },
  },
};
```

### 4. Add Material UI Component Overrides

Edit the `muiTheme.components` object:

```javascript
export const muiTheme = createTheme({
  // ... existing config
  components: {
    // ... existing components
    MuiChip: {
      styleOverrides: {
        root: {
          backgroundColor: themeColors.surface.elevated,
        },
      },
    },
  },
});
```

## Available Theme Values

### Colors
- `primary`, `secondary` - Brand colors
- `background` - Page and surface backgrounds
- `text` - Text colors (primary, secondary, disabled)
- `success`, `error`, `warning`, `info` - State colors
- `border` - Border colors
- `chart` - Chart-specific colors

### Spacing
- `xs`, `sm`, `md`, `lg`, `xl`, `2xl` - Consistent spacing scale

### Border Radius
- `sm`, `md`, `lg`, `xl` - Consistent border radius scale

### Shadows
- `sm`, `md`, `lg` - Consistent shadow scale

## Best Practices

1. **Always use the centralized theme** - Don't hardcode colors or spacing
2. **Use semantic color names** - Use `primary`, `success`, etc. instead of specific color values
3. **Leverage the chart helper functions** - Use `getChartConfig()` for all charts
4. **Use the theme hook** - Access theme values programmatically when needed
5. **Test theme changes** - Changes affect the entire application
6. **Document custom additions** - Add new theme values to this documentation

## Examples

### Complete Chart Setup
```jsx
import { getChartConfig } from '../theme';

function MyChart() {
  const chartConfig = getChartConfig('line', {
    title: { text: 'Sales Over Time' },
    xaxis: { title: { text: 'Date' } },
    yaxis: { title: { text: 'Sales ($)' } },
  });

  return (
    <Chart
      options={chartConfig}
      series={[{ name: 'Sales', data: [...] }]}
      type="line"
      height={350}
    />
  );
}
```

### Custom Styled Component
```jsx
import { useAppTheme } from '../theme/useTheme';

function StatusCard({ status, children }) {
  const theme = useAppTheme();
  
  const getStatusColor = (status) => {
    switch (status) {
      case 'success': return theme.colors.success.main;
      case 'error': return theme.colors.error.main;
      case 'warning': return theme.colors.warning.main;
      default: return theme.colors.info.main;
    }
  };

  return (
    <div
      className="surface p-lg rounded-lg"
      style={{ borderLeft: `4px solid ${getStatusColor(status)}` }}
    >
      {children}
    </div>
  );
}
```

This centralized theme system ensures consistent styling across your entire application while making it easy to maintain and modify the design system.