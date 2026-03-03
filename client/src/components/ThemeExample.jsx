// Example component demonstrating centralized theme usage
import React from 'react';
import { Card, CardContent, Typography, Button } from '@mui/material';
import Chart from 'react-apexcharts';
import { useAppTheme } from '../theme';

const ThemeExample = () => {
  const theme = useAppTheme();
  
  // Example chart configuration using centralized theme
  const chartConfig = theme.charts.lineConfig({
    title: { text: 'Sample Chart' },
    xaxis: { title: { text: 'Time' } },
    yaxis: { title: { text: 'Value' } },
  });
  
  const sampleData = [
    { name: 'Series 1', data: [30, 40, 35, 50, 49, 60, 70, 91, 125] }
  ];

  return (
    <div className="p-lg space-y-lg">
      <Typography variant="h4" className="text-primary">
        Centralized Theme Example
      </Typography>
      
      {/* Material UI Card using theme */}
      <Card className="surface-elevated">
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Material UI Components
          </Typography>
          <Typography className="text-secondary" paragraph>
            These components automatically use the centralized theme.
          </Typography>
          <div className="space-x-sm">
            <Button variant="contained" color="primary">
              Primary Button
            </Button>
            <Button variant="outlined" color="secondary">
              Secondary Button
            </Button>
          </div>
        </CardContent>
      </Card>
      
      {/* Chart using centralized theme */}
      <Card className="surface">
        <CardContent>
          <Typography variant="h6" gutterBottom>
            ApexCharts with Centralized Theme
          </Typography>
          <Chart
            options={chartConfig}
            series={sampleData}
            type="line"
            height={350}
          />
        </CardContent>
      </Card>
      
      {/* Custom styled elements using theme */}
      <div className="card">
        <Typography variant="h6" gutterBottom>
          Custom Styling with Theme
        </Typography>
        <div className="grid grid-cols-3 gap-md">
          {theme.colors.chart.series.slice(0, 3).map((color, index) => (
            <div
              key={index}
              className="p-md rounded-lg text-center"
              style={{ backgroundColor: color }}
            >
              <Typography variant="body2" style={{ color: '#ffffff' }}>
                Color {index + 1}
              </Typography>
              <Typography variant="caption" style={{ color: '#ffffff', opacity: 0.8 }}>
                {color}
              </Typography>
            </div>
          ))}
        </div>
      </div>
      
      {/* Tailwind utilities with theme */}
      <div className="surface p-lg rounded-lg">
        <Typography variant="h6" className="text-primary mb-md">
          Tailwind CSS with Theme Variables
        </Typography>
        <div className="space-y-sm">
          <div className="btn-primary inline-block">
            Primary Button (Tailwind)
          </div>
          <div className="btn-secondary inline-block ml-sm">
            Secondary Button (Tailwind)
          </div>
        </div>
      </div>
      
      {/* Theme information display */}
      <Card className="surface">
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Theme Information
          </Typography>
          <div className="grid grid-cols-2 gap-md text-sm">
            <div>
              <Typography variant="subtitle2" className="text-primary">
                Primary Color:
              </Typography>
              <Typography className="text-secondary font-mono">
                {theme.colors.primary.main}
              </Typography>
            </div>
            <div>
              <Typography variant="subtitle2" className="text-primary">
                Background:
              </Typography>
              <Typography className="text-secondary font-mono">
                {theme.colors.background.default}
              </Typography>
            </div>
            <div>
              <Typography variant="subtitle2" className="text-primary">
                Surface:
              </Typography>
              <Typography className="text-secondary font-mono">
                {theme.colors.background.paper}
              </Typography>
            </div>
            <div>
              <Typography variant="subtitle2" className="text-primary">
                Chart Colors:
              </Typography>
              <Typography className="text-secondary font-mono">
                {theme.colors.chart.series.length} colors defined
              </Typography>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default ThemeExample;