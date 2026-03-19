import React, { useEffect, useMemo, useRef, useState } from "react";
import { Box, Typography, CircularProgress } from "@mui/material";
import StatsTable from "./StatsTable";
import DistributionChart from "./DistributionChart";

const LazyChartMount = ({ children, eager = false, canMount = true, minHeight = 360 }) => {
  const containerRef = useRef(null);
  const [isVisible, setIsVisible] = useState(eager);

  useEffect(() => {
    if (!canMount) return;
    if (isVisible) return;

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            setIsVisible(true);
            observer.disconnect();
          }
        });
      },
      {
        root: null,
        rootMargin: "300px",
        threshold: 0.01
      }
    );

    if (containerRef.current) {
      observer.observe(containerRef.current);
    }

    return () => observer.disconnect();
  }, [isVisible, canMount]);

  const shouldRender = canMount && isVisible;

  return (
    <Box ref={containerRef} sx={{ minHeight }}>
      {shouldRender ? (
        children
      ) : (
        <Box
          sx={{
            height: minHeight,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 1,
            borderRadius: 1,
            bgcolor: 'background.paper'
          }}
        >
          <CircularProgress size={20} />
          <Typography variant="caption" color="text.secondary">
            Loading chart...
          </Typography>
        </Box>
      )}
    </Box>
  );
};

/**
 * Generic Metrics Tab Component
 * Displays both statistics table and distribution charts for any set of metrics
 */
const MetricsTab = ({ 
  title,
  defaultMetrics, 
  adjustedMetrics, 
  metricsConfig,
  filterFunction = null,
  showTable = true,
  showCharts = true
}) => {
  const CHARTS_PER_INITIAL_BATCH = 2;
  const CHART_MOUNT_INTERVAL_MS = 120;
  
  if (!defaultMetrics && !adjustedMetrics) {
    return (
      <div className="flex items-center justify-center h-64">
        <Typography variant="body1" color="text.secondary">
          No data available
        </Typography>
      </div>
    );
  }

  const defaultFilteredRows = useMemo(() => {
    const rows = defaultMetrics?.metrics_table || [];
    if (!filterFunction) return rows;
    return rows.filter(filterFunction);
  }, [defaultMetrics, filterFunction]);

  const adjustedFilteredRows = useMemo(() => {
    const rows = adjustedMetrics?.metrics_table || [];
    if (!filterFunction) return rows;
    return rows.filter(filterFunction);
  }, [adjustedMetrics, filterFunction]);

  const metricSeriesByKey = useMemo(() => {
    const result = {};
    if (!metricsConfig || metricsConfig.length === 0) return result;

    metricsConfig.forEach((metric) => {
      const defaultData = defaultFilteredRows
        .map((row) => row[metric.key])
        .filter((value) => value !== null && value !== undefined);

      const adjustedData = adjustedFilteredRows
        .map((row) => row[metric.key])
        .filter((value) => value !== null && value !== undefined);

      result[metric.key] = {
        defaultData,
        adjustedData
      };
    });

    return result;
  }, [metricsConfig, defaultFilteredRows, adjustedFilteredRows]);

  const totalCharts = metricsConfig?.length || 0;
  const [mountedChartCount, setMountedChartCount] = useState(
    Math.min(CHARTS_PER_INITIAL_BATCH, totalCharts)
  );

  useEffect(() => {
    const initialCount = Math.min(CHARTS_PER_INITIAL_BATCH, totalCharts);
    setMountedChartCount(initialCount);

    if (totalCharts <= initialCount) {
      return;
    }

    const intervalId = setInterval(() => {
      setMountedChartCount((current) => {
        if (current >= totalCharts) {
          clearInterval(intervalId);
          return current;
        }
        return Math.min(totalCharts, current + 1);
      });
    }, CHART_MOUNT_INTERVAL_MS);

    return () => clearInterval(intervalId);
  }, [totalCharts, defaultMetrics, adjustedMetrics, filterFunction]);

  return (
    <Box>
      {/* Statistics Table */}
      {showTable && (
        <Box sx={{ mb: 4 }}>
          <StatsTable
            defaultMetrics={defaultMetrics}
            adjustedMetrics={adjustedMetrics}
            metricsConfig={metricsConfig}
            filterFunction={filterFunction}
            title={title}
          />
        </Box>
      )}

      {/* Distribution Charts */}
      {showCharts && metricsConfig && metricsConfig.length > 0 && (
        <Box>
          <Typography variant="h6" gutterBottom sx={{ mb: 3 }}>
            Distribution Charts
          </Typography>
          <Box sx={{ 
            display: 'flex', 
            flexDirection: 'column', 
            gap: 3 
          }}>
            {Array.from({ length: Math.ceil(metricsConfig.length / 2) }).map((_, rowIndex) => (
              <Box key={rowIndex} sx={{ 
                display: 'flex', 
                gap: 3, 
                '& > *': { flex: 1 }
              }}>
                {metricsConfig.slice(rowIndex * 2, rowIndex * 2 + 2).map((metric, metricIndex) => (
                  (() => {
                    const chartIndex = rowIndex * 2 + metricIndex;
                    return (
                  <LazyChartMount
                    key={metric.key}
                    eager={rowIndex === 0}
                    canMount={chartIndex < mountedChartCount}
                  >
                    <DistributionChart
                      metric={metric}
                      defaultMetrics={defaultMetrics}
                      adjustedMetrics={adjustedMetrics}
                      filterFunction={filterFunction}
                      defaultDataPoints={metricSeriesByKey[metric.key]?.defaultData || []}
                      adjustedDataPoints={metricSeriesByKey[metric.key]?.adjustedData || []}
                      title={`${metric.label}`}
                      fixedBinSize={metric.histogramBinSize ?? null}
                    />
                  </LazyChartMount>
                    );
                  })()
                ))}
              </Box>
            ))}
          </Box>
        </Box>
      )}
    </Box>
  );
};

export default MetricsTab;