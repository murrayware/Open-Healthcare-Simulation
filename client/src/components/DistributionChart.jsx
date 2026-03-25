import React, { useEffect, useMemo, useRef, useState } from "react";
import { Box, Typography, Paper } from "@mui/material";
import Chart from "react-apexcharts";
import uPlot from "uplot";
import UplotReact from "uplot-react";
import "uplot/dist/uPlot.min.css";
import { useAppTheme } from "../theme/useTheme";

const MAX_HISTOGRAM_BINS = 250;
const HOUR_LABEL_BIN_SIZE = 60;
const AUTO_BIN_SIZE_OPTIONS = [1, 5, 10, 15, 30, 60];
const AUTO_TARGET_BIN_COUNT = 30;
const USE_UPLOT = (import.meta.env.VITE_CHART_ENGINE || "uplot") === "uplot";

const formatNumericTick = (value) => {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return "0";
  if (Number.isInteger(numeric)) return String(numeric);
  return numeric.toFixed(1).replace(/\.0$/, "");
};

const DEFAULT_CTAS_CATEGORIES = [1, 2, 3, 4, 5];

const resolveCategoricalConfig = (metric, data = []) => {
  const userConfig = metric?.categoricalConfig || {};
  const explicitCategories = Array.isArray(userConfig.categories) && userConfig.categories.length > 0
    ? userConfig.categories
    : null;
  const metricKey = String(metric?.key || "").toLowerCase();
  const isCtasMetric = metricKey.includes("ctas");

  const derivedCategories = Array.from(new Set(data.map((value) => String(value))))
    .sort((a, b) => Number(a) - Number(b));

  const categories = explicitCategories || (isCtasMetric ? DEFAULT_CTAS_CATEGORIES : derivedCategories);
  const labelPrefix = userConfig.labelPrefix ?? (isCtasMetric ? "CTAS-" : "");
  const labelMap = userConfig.labelMap && typeof userConfig.labelMap === "object"
    ? userConfig.labelMap
    : null;

  return {
    categories,
    getLabel: (value) => {
      const key = String(value);
      if (labelMap && Object.prototype.hasOwnProperty.call(labelMap, key)) {
        return String(labelMap[key]);
      }
      return `${labelPrefix}${key}`;
    }
  };
};

const UPlotHistogram = ({
  chartTitle,
  series,
  metric,
  theme,
  height,
  yMax,
  labelStep
}) => {
  const containerRef = useRef(null);
  const [plotWidth, setPlotWidth] = useState(720);
  const [hoverTooltip, setHoverTooltip] = useState({
    visible: false,
    text: "",
    left: 0,
    top: 0
  });

  useEffect(() => {
    if (!containerRef.current) return;

    const updateWidth = () => {
      if (!containerRef.current) return;
      setPlotWidth(Math.max(320, Math.floor(containerRef.current.clientWidth - 8)));
    };

    updateWidth();

    const observer = new ResizeObserver(() => updateWidth());
    observer.observe(containerRef.current);

    return () => observer.disconnect();
  }, []);

  const labels = useMemo(
    () => (series?.data || []).map((point) => String(point.x ?? "")),
    [series]
  );

  const tooltipLabels = useMemo(
    () => (series?.data || []).map((point) => String(point.tooltipLabel ?? point.x ?? "")),
    [series]
  );

  const yValues = useMemo(
    () => (series?.data || []).map((point) => Number(point.y) || 0),
    [series]
  );

  const xValues = useMemo(
    () => yValues.map((_, index) => index),
    [yValues]
  );

  const barPaths = useMemo(() => {
    const barAlign = metric.isCategorical ? 0 : 1;

    if (uPlot?.paths?.bars) {
      return uPlot.paths.bars({ size: [0.9, 100], align: barAlign });
    }
    if (uPlot?.paths?.stepped) {
      return uPlot.paths.stepped({ align: barAlign });
    }
    return uPlot.paths.linear();
  }, [metric.isCategorical]);

  const options = useMemo(() => {
    const topY = metric.showPercentage ? 100 : Math.max(1, yMax || 1);

    return {
      width: plotWidth,
      height,
      cursor: { drag: { x: false, y: false }, focus: { prox: 24 } },
      select: { show: false },
      legend: { show: false },
      scales: {
        x: {
          time: false,
          auto: false,
          range: () => {
            if (xValues.length <= 1) {
              return metric.isCategorical ? [-0.5, 0.5] : [0, 0.8];
            }
            if (metric.isCategorical) {
              return [-0.5, xValues.length - 0.5];
            }
            return [0, xValues.length - 0.2];
          }
        },
        y: {
          auto: false,
          range: () => [0, topY]
        }
      },
      series: [
        {},
        {
          label: series?.name || chartTitle,
          stroke: series?.color || theme.utils.getChartColor(0),
          fill: `${series?.color || theme.utils.getChartColor(0)}33`,
          width: 1,
          points: { show: false },
          paths: barPaths
        }
      ],
      axes: [
        {
          stroke: theme.colors.text.primary,
          rotate: metric.isCategorical ? 0 : 45,
          size: metric.isCategorical ? 38 : 52,
          gap: metric.isCategorical ? 6 : 8,
          grid: { stroke: theme.colors.divider || "rgba(255,255,255,0.12)" },
          splits: () => xValues,
          values: (_u, vals) =>
            vals.map((raw) => {
              const index = Math.round(raw);
              if (index < 0 || index >= labels.length) return "";
              return labels[index];
            })
        },
        {
          stroke: theme.colors.text.primary,
          grid: { stroke: theme.colors.divider || "rgba(255,255,255,0.12)" },
          values: (_u, vals) =>
            vals.map((value) =>
              metric.showPercentage ? `${Number(value).toFixed(1)}%` : formatNumericTick(value)
            )
        }
      ],
      hooks: {
        setCursor: [
          (u) => {
            const idx = u.cursor?.idx;
            if (idx == null || idx < 0 || idx >= yValues.length) {
              setHoverTooltip((prev) => (prev.visible ? { ...prev, visible: false } : prev));
              return;
            }

            const rangeLabel = tooltipLabels[idx] || labels[idx] || "";
            const yValue = Number(yValues[idx]) || 0;
            const valueLabel = metric.showPercentage
              ? `${yValue.toFixed(1)}%`
              : `${Math.round(yValue)} patients`;
            const nextText = `${rangeLabel}: ${valueLabel}`;
            const plotLeft = Number(u.bbox?.left) || 0;
            const plotTop = Number(u.bbox?.top) || 0;
            const nextLeft = Math.max(0, plotLeft + (Number(u.cursor?.left) || 0) + 2);
            const nextTop = Math.max(0, plotTop + (Number(u.cursor?.top) || 0) + 12);

            setHoverTooltip((prev) => {
              if (
                prev.visible &&
                prev.text === nextText &&
                prev.left === nextLeft &&
                prev.top === nextTop
              ) {
                return prev;
              }

              return {
                visible: true,
                text: nextText,
                left: nextLeft,
                top: nextTop
              };
            });
          }
        ]
      }
    };
  }, [plotWidth, height, metric, theme, yMax, labelStep, labels, tooltipLabels, yValues, xValues, series, barPaths, chartTitle]);

  const data = useMemo(() => [xValues, yValues], [xValues, yValues]);

  return (
    <Box ref={containerRef} sx={{ width: '100%', position: 'relative' }}>
      {xValues.length > 0 ? <UplotReact options={options} data={data} /> : null}
      {hoverTooltip.visible ? (
        <Box
          sx={{
            position: 'absolute',
            left: `${hoverTooltip.left}px`,
            top: `${hoverTooltip.top}px`,
            pointerEvents: 'none',
            px: 1,
            py: 0.5,
            borderRadius: 1,
            bgcolor: theme.colors.background.paper,
            border: `1px solid ${theme.colors.divider || 'rgba(255,255,255,0.2)'}`,
            color: theme.colors.text.primary,
            whiteSpace: 'nowrap',
            fontSize: '0.75rem',
            fontWeight: 500,
            zIndex: 3,
            boxShadow: theme.shadows?.small || 'none'
          }}
        >
          {hoverTooltip.text}
        </Box>
      ) : null}
    </Box>
  );
};

/**
 * Generic Distribution Chart Component
 * Shows histogram distribution of a specific metric
 */
const DistributionChart = ({ 
  metric, 
  defaultMetrics, 
  adjustedMetrics,
  defaultDataPoints = null,
  adjustedDataPoints = null,
  filterFunction = null,
  title,
  fixedBinSize = null
}) => {
  const theme = useAppTheme();
  const renderCountRef = useRef(0);
  renderCountRef.current += 1;
  const isDev = typeof import.meta !== 'undefined' && import.meta.env?.DEV;

  const profile = (label, callback) => {
    if (!isDev) return callback();
    const start = performance.now();
    const value = callback();
    const elapsed = performance.now() - start;
    if (elapsed >= 6) {
      console.debug(
        `[Perf][DistributionChart:${metric.key}] ${label}: ${elapsed.toFixed(1)}ms (render ${renderCountRef.current})`
      );
    }
    return value;
  };

  const resolveEffectiveBinSize = (requestedBinSize) => {
    if (!requestedBinSize || Number(requestedBinSize) <= 0) return null;
    return Number(requestedBinSize);
  };

  const resolveAutoBinSize = (maxValue) => {
    const max = Math.max(1, Number(maxValue) || 0);
    let bestOption = AUTO_BIN_SIZE_OPTIONS[0];
    let bestDifference = Number.POSITIVE_INFINITY;

    AUTO_BIN_SIZE_OPTIONS.forEach((option) => {
      const binCount = Math.max(1, Math.ceil(max / option));
      const difference = Math.abs(binCount - AUTO_TARGET_BIN_COUNT);

      if (difference < bestDifference || (difference === bestDifference && option > bestOption)) {
        bestDifference = difference;
        bestOption = option;
      }
    });

    return bestOption;
  };

  const clampBinsToMax = (bins) => {
    if (!Array.isArray(bins) || bins.length <= MAX_HISTOGRAM_BINS) {
      return bins;
    }

    const groupSize = Math.ceil(bins.length / MAX_HISTOGRAM_BINS);
    const compressed = [];

    for (let index = 0; index < bins.length; index += groupSize) {
      const group = bins.slice(index, index + groupSize);
      const first = group[0];
      compressed.push({
        x: first?.x != null ? String(first.x) : String(index),
        y: group.reduce((sum, point) => sum + (Number(point?.y) || 0), 0)
      });
    }

    return compressed;
  };

  const clampSeriesData = (series) => {
    if (!series || !Array.isArray(series.data)) return series;
    if (series.data.length <= MAX_HISTOGRAM_BINS) return series;

    return {
      ...series,
      data: clampBinsToMax(series.data)
    };
  };
  
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

  const defaultData = useMemo(
    () => {
      if (Array.isArray(defaultDataPoints)) {
        return defaultDataPoints;
      }
      return profile('extract default data', () => extractMetricData(defaultMetrics, metric.key));
    },
    [defaultDataPoints, defaultMetrics, metric.key, filterFunction]
  );

  const adjustedData = useMemo(
    () => {
      if (Array.isArray(adjustedDataPoints)) {
        return adjustedDataPoints;
      }
      return profile('extract adjusted data', () => (adjustedMetrics ? extractMetricData(adjustedMetrics, metric.key) : []));
    },
    [adjustedDataPoints, adjustedMetrics, metric.key, filterFunction]
  );

  const combinedMaxValue = useMemo(() => {
    let maxValue = 0;
    for (const value of defaultData) {
      if (value > maxValue) maxValue = value;
    }
    for (const value of adjustedData) {
      if (value > maxValue) maxValue = value;
    }
    return maxValue;
  }, [defaultData, adjustedData]);

  const effectiveBinSize = useMemo(() => {
    if (metric.isTimestamp === true || metric.isCategorical === true) {
      return null;
    }

    const overrideBinSize = resolveEffectiveBinSize(fixedBinSize);
    if (overrideBinSize) {
      return overrideBinSize;
    }

    return resolveAutoBinSize(combinedMaxValue);
  }, [metric.isTimestamp, metric.isCategorical, fixedBinSize, combinedMaxValue]);

  const shouldUseHourBinLabels = useMemo(
    () =>
      metric.isTimestamp !== true &&
      metric.isCategorical !== true &&
      effectiveBinSize === HOUR_LABEL_BIN_SIZE,
    [metric.isTimestamp, metric.isCategorical, effectiveBinSize]
  );

  // Calculate shared axis ranges for comparability
  const getSharedAxisRanges = (data1, data2) => {
    const allData = [...data1, ...data2];
    if (allData.length === 0) return null;
    
    const min = Math.min(...allData);
    const max = Math.max(...allData);
    const range = max - min;
    
    // Add 5% padding on each side (only for auto-bin mode)
    const padding = range * 0.05;
    let sharedMin = min - padding;
    let sharedMax = max + padding;
    
    // Calculate shared bin configuration
    let binCount = Math.min(15, Math.max(5, Math.ceil(Math.sqrt(allData.length))));
    let binSize = (sharedMax - sharedMin) / binCount;

    if (effectiveBinSize && Number(effectiveBinSize) > 0) {
      const desiredBinSize = effectiveBinSize;
      // Always anchor fixed-bin histograms at zero (0-60 first bin when binSize=60)
      sharedMin = 0;
      sharedMax = Math.max(sharedMin + desiredBinSize, Math.ceil(max / desiredBinSize) * desiredBinSize);
      const desiredBinCount = Math.max(1, Math.ceil((sharedMax - sharedMin) / desiredBinSize));

      if (desiredBinCount > MAX_HISTOGRAM_BINS) {
        const stepMultiplier = Math.ceil(desiredBinCount / MAX_HISTOGRAM_BINS);
        binSize = desiredBinSize * stepMultiplier;
        binCount = Math.max(1, Math.ceil((sharedMax - sharedMin) / binSize));
      } else {
        binSize = desiredBinSize;
        binCount = desiredBinCount;
      }
    }
    
    return {
      min: sharedMin,
      max: sharedMax,
      binCount,
      binSize,
      maxCount: 0 // Will be calculated after histograms are created
    };
  };

  const sharedRanges = useMemo(
    () =>
      profile('compute shared ranges', () =>
        adjustedData.length > 0
          ? getSharedAxisRanges(defaultData, adjustedData)
          : getSharedAxisRanges(defaultData, [])
      ),
    [defaultData, adjustedData, effectiveBinSize]
  );

  // Create histogram bins
  const createHistogram = (data, label, color, useSharedRanges = false) => {
    if (data.length === 0 && !useSharedRanges) return null;
    
    // Check if this is a timestamp metric (needs hourly bins)
    const isTimestamp = metric.isTimestamp === true;
    
    if (isTimestamp) {
      // Create 24 hour bins for timestamps (data in minutes from midnight)
      const hourBins = Array(24).fill(0).map((_, i) => ({
        x: `${i.toString().padStart(2, '0')}:00`,
        y: 0,
        hour: i
      }));
      
      // Fill bins with data
      data.forEach(minutes => {
        const hour = Math.floor(minutes / 60) % 24;
        if (hour >= 0 && hour < 24) {
          hourBins[hour].y++;
        }
      });
      
      return {
        name: label,
        data: hourBins.map(bin => ({ x: bin.x, y: bin.y })),
        color: color
      };
    }
    
    // Check if this is a discrete categorical metric (e.g., CTAS 1-5)
    const isCategorical = metric.isCategorical === true;
    
    if (isCategorical) {
      const { categories, getLabel } = resolveCategoricalConfig(metric, data);

      // Count occurrences of each discrete value
      const valueCounts = {};
      data.forEach(value => {
        const key = String(value);
        valueCounts[key] = (valueCounts[key] || 0) + 1;
      });

      const orderedCategories = categories.length > 0
        ? categories
        : Object.keys(valueCounts).sort((a, b) => Number(a) - Number(b));

      // Calculate percentages if showPercentage is enabled
      const total = data.length;
      const dataPoints = metric.showPercentage 
        ? orderedCategories.map((categoryValue) => {
            const key = String(categoryValue);
            const count = valueCounts[key] || 0;
            return {
              x: getLabel(categoryValue),
              y: total > 0 ? (count / total * 100) : 0,
              tooltipLabel: getLabel(categoryValue)
            };
          })
        : orderedCategories.map((categoryValue) => {
            const key = String(categoryValue);
            return {
              x: getLabel(categoryValue),
              y: valueCounts[key] || 0,
              tooltipLabel: getLabel(categoryValue)
            };
          });

      const clampedDataPoints = clampBinsToMax(dataPoints);
      
      return {
        name: label,
        data: clampedDataPoints,
        color: color
      };
    }
    
    // Standard duration metric bins
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
        const singleBinLabel = shouldUseHourBinLabels
          ? Math.round(min / HOUR_LABEL_BIN_SIZE)
          : Math.round(min);
        return {
          name: label,
          data: [{ x: String(singleBinLabel), y: data.length }],
          color: color
        };
      }
      
      if (effectiveBinSize && Number(effectiveBinSize) > 0) {
        const desiredBinSize = effectiveBinSize;
        // Always anchor fixed-bin histograms at zero (0-60 first bin when binSize=60)
        min = 0;
        max = Math.max(min + desiredBinSize, Math.ceil(max / desiredBinSize) * desiredBinSize);
        const alignedRange = max - min;
        const desiredBinCount = Math.max(1, Math.ceil(alignedRange / desiredBinSize));

        if (desiredBinCount > MAX_HISTOGRAM_BINS) {
          const stepMultiplier = Math.ceil(desiredBinCount / MAX_HISTOGRAM_BINS);
          binSize = desiredBinSize * stepMultiplier;
          binCount = Math.max(1, Math.ceil(alignedRange / binSize));
        } else {
          binSize = desiredBinSize;
          binCount = desiredBinCount;
        }
      } else {
        binCount = Math.min(15, Math.max(5, Math.ceil(Math.sqrt(data.length))));
        binSize = range / binCount;
      }
    }
    
    const bins = Array(binCount).fill(0).map((_, i) => {
      const binStart = min + i * binSize;
      const binEnd = min + (i + 1) * binSize;
      const xLabel = shouldUseHourBinLabels
        ? Math.round(binStart / HOUR_LABEL_BIN_SIZE)
        : Math.round(binStart);
      return {
        x: String(xLabel),
        y: 0,
        binStart,
        binEnd
      };
    });

    // Fill bins with data
    data.forEach(value => {
      const rawIndex = Math.floor((value - min) / binSize);
      const binIndex = Math.min(bins.length - 1, Math.max(0, rawIndex));
      if (binIndex >= 0 && binIndex < bins.length) {
        bins[binIndex].y++;
      }
    });

    const finalBins = bins.map(bin => ({ x: bin.x, y: bin.y }));
    const normalizedUnit = metric.unit && String(metric.unit).trim().length > 0
      ? String(metric.unit).trim()
      : 'mins';
    const unitLabel = /min/i.test(normalizedUnit) ? 'mins' : normalizedUnit;

    const finalBinsWithTooltip = bins.map(bin => ({
      x: bin.x,
      y: bin.y,
      tooltipLabel: `${Math.round(bin.binStart)}-${Math.round(bin.binEnd)} ${unitLabel}`
    }));

    const clampedBins = clampBinsToMax(finalBinsWithTooltip);

    return {
      name: label,
      data: clampedBins,
      color: color
    };
  };

  // Prepare chart series with theme colors and shared ranges
  const useShared = adjustedData.length > 0 && sharedRanges;
  const defaultSeries = useMemo(
    () => profile('build default histogram', () => clampSeriesData(createHistogram(defaultData, 'Default', theme.utils.getChartColor(0), useShared))),
    [defaultData, metric, effectiveBinSize, sharedRanges, useShared, shouldUseHourBinLabels, theme]
  );

  const adjustedSeries = useMemo(
    () =>
      profile('build adjusted histogram', () =>
        adjustedData.length > 0
          ? clampSeriesData(createHistogram(adjustedData, 'Adjusted', theme.utils.getChartColor(1), useShared))
          : null
      ),
    [adjustedData, metric, effectiveBinSize, sharedRanges, useShared, shouldUseHourBinLabels, theme]
  );

  const labelStep = useMemo(() => {
    const pointCount = Math.max(defaultSeries?.data?.length || 0, adjustedSeries?.data?.length || 0);
    if (pointCount <= 0) return 1;
    return Math.max(1, Math.ceil(pointCount / 16));
  }, [defaultSeries, adjustedSeries]);

  // Calculate maximum Y-axis value for both charts
  const yAxisMax = useMemo(() => {
    let maxYValue = 0;
    if (defaultSeries) {
      for (const point of defaultSeries.data) {
        if (point.y > maxYValue) maxYValue = point.y;
      }
    }
    if (adjustedSeries) {
      for (const point of adjustedSeries.data) {
        if (point.y > maxYValue) maxYValue = point.y;
      }
    }
    return Math.ceil(maxYValue * 1.1);
  }, [defaultSeries, adjustedSeries]);

  // Chart options using centralized theme
  const getChartOptions = (chartTitle, showLegend = false) => {
    const baseConfig = theme.charts.barConfig({
      chart: {
        height: adjustedSeries ? 200 : 300,
        toolbar: { show: false },
        animations: { enabled: false }
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
          text: metric.isTimestamp
            ? 'Hour'
            : metric.isCategorical
              ? metric.unit
              : shouldUseHourBinLabels
                ? 'Time (hours)'
                : `Time Range (${metric.unit || 'minutes'})`,
          style: { 
            fontSize: '12px',
            color: theme.colors.text.secondary
          }
        },
        tickPlacement: 'on',
        labels: { 
          style: { 
            fontSize: '10px',
            colors: theme.colors.text.primary
          },
          formatter: (value, _timestamp, options) => {
            if (metric.isCategorical) return value;
            return value;
          },
          rotate: metric.isCategorical ? 0 : -45,
          rotateAlways: metric.isCategorical ? false : true,
          hideOverlappingLabels: true,
          showDuplicates: false,
          trim: true,
          minHeight: metric.isCategorical ? undefined : 40,
          maxHeight: metric.isCategorical ? undefined : 80,
          offsetY: metric.isCategorical ? 0 : 8
        }
      },
      grid: {
        padding: {
          bottom: metric.isCategorical ? 8 : 22
        }
      },
      yaxis: {
        title: { 
          text: metric.showPercentage ? 'Percentage (%)' : 'Count',
          style: { 
            fontSize: '12px',
            color: theme.colors.text.secondary
          }
        },
        labels: { 
          style: { 
            fontSize: '10px',
            colors: theme.colors.text.primary
          },
          formatter: (value) => metric.showPercentage ? `${value.toFixed(1)}%` : formatNumericTick(value)
        },
        min: 0,
        max: adjustedSeries ? yAxisMax : metric.showPercentage ? 100 : undefined // Use shared max when comparing or 100 for percentage
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
        enabled: metric.showDataLabels === true,
        formatter: (value) => metric.showPercentage ? `${value.toFixed(1)}%` : Math.round(value),
        style: {
          fontSize: '11px',
          colors: [theme.colors.text.primary],
          fontWeight: 600
        },
        offsetY: -20
      },
      tooltip: {
        theme: theme.mode.current,
        y: {
          formatter: (value) => metric.showPercentage 
            ? `${value.toFixed(1)}%` 
            : `${value} ${metric.countLabel || 'items'}`
        }
      }
    });

    return baseConfig;
  };

  const defaultChartOptions = useMemo(
    () => profile('build default chart options', () => getChartOptions('Default Configuration')),
    [theme, metric, adjustedSeries, yAxisMax, shouldUseHourBinLabels]
  );

  const adjustedChartOptions = useMemo(
    () => profile('build adjusted chart options', () => getChartOptions('Tuned Configuration')),
    [theme, metric, adjustedSeries, yAxisMax, shouldUseHourBinLabels]
  );

  const singleChartOptions = useMemo(
    () => profile('build single chart options', () => getChartOptions('Distribution')),
    [theme, metric, adjustedSeries, yAxisMax, shouldUseHourBinLabels]
  );

  if (defaultData.length === 0 && adjustedData.length === 0) {
    return (
      <Paper elevation={0} sx={{ p: 2, mb: 2, backgroundColor: theme.colors.background.paper }}>
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
    <Paper elevation={0} sx={{ p: 2, mb: 2, backgroundColor: theme.colors.background.paper }}>
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
          {USE_UPLOT ? (
            <>
              <Typography variant="subtitle2" sx={{ mb: 1, color: 'text.secondary' }}>
                Default Configuration
              </Typography>
              <UPlotHistogram
                chartTitle="Default Configuration"
                series={defaultSeries}
                metric={metric}
                theme={theme}
                height={200}
                yMax={yAxisMax}
                labelStep={labelStep}
              />
              <Typography variant="subtitle2" sx={{ mt: 2, mb: 1, color: 'text.secondary' }}>
                Tuned Configuration
              </Typography>
              <UPlotHistogram
                chartTitle="Tuned Configuration"
                series={adjustedSeries}
                metric={metric}
                theme={theme}
                height={200}
                yMax={yAxisMax}
                labelStep={labelStep}
              />
            </>
          ) : (
            <>
              <Chart
                options={defaultChartOptions}
                series={[defaultSeries]}
                type="bar"
                height={200}
              />
              <Chart
                options={adjustedChartOptions}
                series={[adjustedSeries]}
                type="bar"
                height={200}
              />
            </>
          )}
        </Box>
      ) : (
        // Show single chart when only default data exists
        USE_UPLOT ? (
          <UPlotHistogram
            chartTitle="Distribution"
            series={defaultSeries}
            metric={metric}
            theme={theme}
            height={300}
            yMax={metric.showPercentage ? 100 : yAxisMax}
            labelStep={labelStep}
          />
        ) : (
          <Chart
            options={singleChartOptions}
            series={[defaultSeries]}
            type="bar"
            height={300}
          />
        )
      )}
    </Paper>
  );
};

export default React.memo(DistributionChart);