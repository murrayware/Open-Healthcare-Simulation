import React from "react";
import { Box, Typography, Grid } from "@mui/material";
import StatsTable from "./StatsTable";
import DistributionChart from "./DistributionChart";

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
  
  if (!defaultMetrics && !adjustedMetrics) {
    return (
      <div className="flex items-center justify-center h-64">
        <Typography variant="body1" color="text.secondary">
          No data available
        </Typography>
      </div>
    );
  }

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
                {metricsConfig.slice(rowIndex * 2, rowIndex * 2 + 2).map((metric) => (
                  <DistributionChart
                    key={metric.key}
                    metric={metric}
                    defaultMetrics={defaultMetrics}
                    adjustedMetrics={adjustedMetrics}
                    filterFunction={filterFunction}
                    title={`${metric.label}`}
                  />
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