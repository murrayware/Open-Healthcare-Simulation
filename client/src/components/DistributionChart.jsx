import React from "react";
import { Box, Typography, Paper } from "@mui/material";
import Chart from "react-apexcharts";
import { useAppTheme } from "../theme/useTheme";

/**
 * Generic Distribution Chart Component
 * Shows histogram distribution of a specific metric
 */
const DistributionChart = ({ 
  metric, 
  defaultMetrics, 
  adjustedMetrics,
  filterFunction = null,
  title
}) => {
  const theme = useAppTheme();
  
  // Extract data for the specific metric
  const extractMetricData = (metrics, field) => {
    if (!metrics || !metrics.metrics_table) return [];
    
    let data = metrics.metrics_table;
    
    // Apply filter if provided
    if (filterFunction) {
      data = data.filter(filterFunction);
    }
    
    return data
      .filter(row => row[field] !== null && row[field] !== undefined)
      .map(row => row[field]);
  };

  const defaultData = extractMetricData(defaultMetrics, metric.key);
  const adjustedData = adjustedMetrics ? extractMetricData(adjustedMetrics, metric.key) : [];

  // Calculate shared axis ranges for comparability
  const getSharedAxisRanges = (data1, data2) => {
    const allData = [...data1, ...data2];
    if (allData.length === 0) return null;
    
    const min = Math.min(...allData);
    const max = Math.max(...allData);
    const range = max - min;
    
    // Add 5% padding on each side
    const padding = range * 0.05;
    const sharedMin = min - padding;
    const sharedMax = max + padding;
    
    // Calculate shared bin configuration
    const binCount = Math.min(15, Math.max(5, Math.ceil(Math.sqrt(allData.length))));
    const binSize = (sharedMax - sharedMin) / binCount;
    
    return {
      min: sharedMin,
      max: sharedMax,
      binCount,
      binSize,
      maxCount: 0 // Will be calculated after histograms are created
    };
  };

  const sharedRanges = adjustedData.length > 0 ? 
    getSharedAxisRanges(defaultData, adjustedData) : 
    getSharedAxisRanges(defaultData, []);

  // Create histogram bins
  const createHistogram = (data, label, color, useSharedRanges = false) => {
    if (data.length === 0 && !useSharedRanges) return null;
    
    let min, max, binCount, binSize;
    
    if (useSharedRanges && sharedRanges) {
      // Use shared ranges for comparability
      min = sharedRanges.min;
      max = sharedRanges.max;
      binCount = sharedRanges.binCount;
      binSize = sharedRanges.binSize;
    } else {
      // Calculate individual ranges (fallback)
      if (data.length === 0) return null;
      
      min = Math.min(...data);
      max = Math.max(...data);
      const range = max - min;
      
      // Handle case where all values are the same
      if (range === 0) {
        return {
          name: label,
          data: [{ x: min.toFixed(1), y: data.length }],
          color: color
        };
      }
      
      binCount = Math.min(15, Math.max(5, Math.ceil(Math.sqrt(data.length))));
      binSize = range / binCount;
    }
    
    const bins = Array(binCount).fill(0).map((_, i) => {
      const binStart = min + i * binSize;
      const binEnd = min + (i + 1) * binSize;
      return {
        x: `${binStart.toFixed(1)}-${binEnd.toFixed(1)}`,
        y: 0,
        binStart,
        binEnd
      };
    });

    // Fill bins with data
    data.forEach(value => {
      const binIndex = Math.floor((value - min) / binSize);
      if (binIndex >= 0 && binIndex < bins.length) {
        bins[binIndex].y++;
      }
    });

    return {
      name: label,
      data: bins.map(bin => ({ x: bin.x, y: bin.y })),
      color: color
    };
  };

  // Prepare chart series with theme colors and shared ranges
  const useShared = adjustedData.length > 0 && sharedRanges;
  const defaultSeries = createHistogram(defaultData, 'Default', theme.utils.getChartColor(0), useShared);
  const adjustedSeries = adjustedData.length > 0 ? 
    createHistogram(adjustedData, 'Adjusted', theme.utils.getChartColor(1), useShared) : null;

  // Calculate maximum Y-axis value for both charts
  const maxYValue = Math.max(
    defaultSeries ? Math.max(...defaultSeries.data.map(d => d.y)) : 0,
    adjustedSeries ? Math.max(...adjustedSeries.data.map(d => d.y)) : 0
  );
  const yAxisMax = Math.ceil(maxYValue * 1.1); // Add 10% padding

  // Chart options using centralized theme
  const getChartOptions = (chartTitle, showLegend = false) => {
    const baseConfig = theme.charts.barConfig({
      chart: {
        height: adjustedSeries ? 200 : 300,
        toolbar: { show: false }
      },
      title: {
        text: chartTitle,
        style: { 
          fontSize: '14px', 
          fontWeight: 600,
          color: theme.colors.text.primary
        }
      },
      xaxis: {
        type: 'category',
        title: { 
          text: `Time Range (${metric.unit || 'minutes'})`,
          style: { 
            fontSize: '12px',
            color: theme.colors.text.secondary
          }
        },
        labels: { 
          style: { 
            fontSize: '10px',
            colors: theme.colors.text.secondary
          },
          rotate: -45
        }
      },
      yaxis: {
        title: { 
          text: 'Count',
          style: { 
            fontSize: '12px',
            color: theme.colors.text.secondary
          }
        },
        labels: { 
          style: { 
            fontSize: '10px',
            colors: theme.colors.text.secondary
          },
          formatter: (value) => Math.round(value)
        },
        min: 0,
        max: adjustedSeries ? yAxisMax : undefined // Use shared max when comparing
      },
      legend: { 
        show: showLegend,
        position: 'top',
        fontSize: '11px',
        labels: {
          colors: theme.colors.text.primary
        }
      },
      plotOptions: {
        bar: {
          columnWidth: '70%',
          borderRadius: 2,
          dataLabels: {
            position: 'top'
          }
        }
      },
      dataLabels: {
        enabled: false
      },
      tooltip: {
        theme: theme.mode.current,
        y: {
          formatter: (value) => `${value} ${metric.countLabel || 'items'}`
        }
      }
    });

    return baseConfig;
  };

  if (defaultData.length === 0) {
    return (
      <Paper elevation={1} sx={{ p: 2, mb: 2 }}>
        <Typography variant="h6" gutterBottom>
          {title || metric.label}
        </Typography>
        <Box sx={{ 
          height: 200, 
          display: 'flex', 
          alignItems: 'center', 
          justifyContent: 'center' 
        }}>
          <Typography variant="body2" color="text.secondary">
            No data available for {(title || metric.label).toLowerCase()}
          </Typography>
        </Box>
      </Paper>
    );
  }

  return (
    <Paper elevation={1} sx={{ p: 2, mb: 2 }}>
      <Typography variant="h6" gutterBottom>
        {title || `${metric.label} Distribution`}
      </Typography>
      {metric.description && (
        <Typography variant="caption" color="text.secondary" display="block" sx={{ mb: 2 }}>
          {metric.description}
        </Typography>
      )}

      {adjustedSeries ? (
        // Show both charts when adjusted data exists
        <Box>
          <Chart
            options={getChartOptions('Default Configuration')}
            series={[defaultSeries]}
            type="bar"
            height={200}
          />
          <Chart
            options={getChartOptions('Adjusted Configuration')}
            series={[adjustedSeries]}
            type="bar"
            height={200}
          />
        </Box>
      ) : (
        // Show single chart when only default data exists
        <Chart
          options={getChartOptions('Distribution')}
          series={[defaultSeries]}
          type="bar"
          height={300}
        />
      )}
    </Paper>
  );
};

export default DistributionChart;