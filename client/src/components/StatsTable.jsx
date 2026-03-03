import React, { useState } from "react";
import { 
  Table, 
  TableBody, 
  TableCell, 
  TableContainer, 
  TableHead, 
  TableRow, 
  Paper,
  Typography,
  Tabs,
  Tab,
  Box
} from "@mui/material";

/**
 * Generic Statistics Table Component
 * Displays statistical summary for any set of metrics
 */
const StatsTable = ({ 
  defaultMetrics, 
  adjustedMetrics, 
  metricsConfig,
  filterFunction = null,
  title = "Statistics"
}) => {
  const [activeDataTab, setActiveDataTab] = useState(adjustedMetrics ? "adjusted" : "default");
  
  const handleDataTabChange = (event, newValue) => {
    setActiveDataTab(newValue);
  };

  const currentMetrics = activeDataTab === "adjusted" && adjustedMetrics ? adjustedMetrics : defaultMetrics;
  
  if (!currentMetrics || !currentMetrics.metrics_table) {
    return (
      <div className="flex items-center justify-center h-64">
        <Typography variant="body1" color="text.secondary">
          No data available
        </Typography>
      </div>
    );
  }

  // Extract data using provided filter function or use all data
  const filteredData = filterFunction 
    ? currentMetrics.metrics_table.filter(filterFunction)
    : currentMetrics.metrics_table;
  
  // Calculate statistics for each metric
  const calculateStats = (data, field) => {
    const values = data
      .map(row => row[field])
      .filter(val => val !== null && val !== undefined)
      .sort((a, b) => a - b);
    
    if (values.length === 0) return null;
    
    const mean = values.reduce((sum, val) => sum + val, 0) / values.length;
    const median = values[Math.floor(values.length / 2)];
    const p75 = values[Math.floor(values.length * 0.75)];
    const p90 = values[Math.floor(values.length * 0.90)];
    const min = values[0];
    const max = values[values.length - 1];
    
    return { mean, median, p75, p90, min, max };
  };

  // Calculate stats for both default and adjusted (if available) for comparison
  const defaultFilteredData = filterFunction && defaultMetrics?.metrics_table
    ? defaultMetrics.metrics_table.filter(filterFunction)
    : defaultMetrics?.metrics_table || [];
  
  const adjustedFilteredData = filterFunction && adjustedMetrics?.metrics_table
    ? adjustedMetrics.metrics_table.filter(filterFunction)
    : adjustedMetrics?.metrics_table || [];
  
  const statsData = metricsConfig.map(metric => {
    const currentStats = calculateStats(filteredData, metric.key);
    let defaultStats = null;
    let comparison = null;
    
    // If we're showing adjusted data, calculate default stats for comparison
    if (activeDataTab === "adjusted" && adjustedMetrics && defaultMetrics) {
      defaultStats = calculateStats(defaultFilteredData, metric.key);
      if (currentStats && defaultStats) {
        comparison = {
          mean: currentStats.mean - defaultStats.mean,
          median: currentStats.median - defaultStats.median,
          p75: currentStats.p75 - defaultStats.p75,
          p90: currentStats.p90 - defaultStats.p90,
          min: currentStats.min - defaultStats.min,
          max: currentStats.max - defaultStats.max
        };
      }
    }
    
    return {
      ...metric,
      stats: currentStats,
      comparison
    };
  });

  const formatValue = (value, unit = "min") => {
    if (value === null || value === undefined) return 'N/A';
    const roundedValue = Math.round(value * 10) / 10;
    return `${roundedValue} ${unit}`;
  };

  const renderValueWithComparison = (value, comparisonValue, unit = "min") => {
    if (value === null || value === undefined) return 'N/A';
    
    const formattedValue = formatValue(value, unit);
    
    // Only show comparison if we're on adjusted tab and have comparison data
    if (activeDataTab === "adjusted" && comparisonValue !== null && comparisonValue !== undefined) {
      const absChange = Math.abs(comparisonValue);
      const isSignificant = absChange >= 0.1; // Only show change if >= 0.1 units
      
      if (!isSignificant) {
        return (
          <Box textAlign="right">
            <Typography sx={{ fontFamily: 'monospace', fontSize: '0.875rem' }}>
              {formattedValue}
            </Typography>
            <Typography sx={{ 
              fontSize: '0.65rem', 
              color: 'text.disabled',
              lineHeight: 1
            }}>
              — no change
            </Typography>
          </Box>
        );
      }
      
      const isImprovement = comparisonValue < 0; // Lower values are generally better
      const changeAmount = Math.round(Math.abs(comparisonValue) * 10) / 10;
      const signSymbol = isImprovement ? '-' : '+';
      const changeColor = isImprovement ? 'success.main' : 'error.main';
      
      return (
        <Box textAlign="right">
          <Typography sx={{ fontFamily: 'monospace', fontSize: '0.875rem' }}>
            {formattedValue}
          </Typography>
          <Typography sx={{ 
            fontSize: '0.65rem', 
            color: changeColor,
            lineHeight: 1,
            fontWeight: 500
          }}>
            {signSymbol} {changeAmount} {unit}
          </Typography>
        </Box>
      );
    }
    
    return formattedValue;
  };

  return (
    <Box>
      {/* Data Source Tabs */}
      <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 2 }}>
        <Tabs 
          value={activeDataTab} 
          onChange={handleDataTabChange}
          variant="scrollable"
          scrollButtons="auto"
        >
          <Tab value="default" label="Default" />
          {adjustedMetrics && (
            <Tab value="adjusted" label="Adjusted" />
          )}
        </Tabs>
      </Box>

      {/* Statistics Table */}
      <TableContainer component={Paper} elevation={1} sx={{ maxHeight: 400 }}>
        <Table size="small" stickyHeader sx={{ '& .MuiTableCell-root': { py: 0.75, px: 2 } }}>
          <TableHead>
            <TableRow>
              <TableCell sx={{ 
                fontWeight: 'bold', 
                minWidth: 200, 
                backgroundColor: 'grey.500',
                borderBottom: 2,
                borderColor: 'divider'
              }}>
                Metric
              </TableCell>
              <TableCell align="right" sx={{ 
                fontWeight: 'bold', 
                minWidth: 70,
                backgroundColor: 'grey.500',
                borderBottom: 2,
                borderColor: 'divider'
              }}>
                Mean
              </TableCell>
              <TableCell align="right" sx={{ 
                fontWeight: 'bold', 
                minWidth: 70,
                backgroundColor: 'grey.500',
                borderBottom: 2,
                borderColor: 'divider'
              }}>
                Median
              </TableCell>
              <TableCell align="right" sx={{ 
                fontWeight: 'bold', 
                minWidth: 70,
                backgroundColor: 'grey.500',
                borderBottom: 2,
                borderColor: 'divider'
              }}>
                P75
              </TableCell>
              <TableCell align="right" sx={{ 
                fontWeight: 'bold', 
                minWidth: 70,
                backgroundColor: 'grey.500',
                borderBottom: 2,
                borderColor: 'divider'
              }}>
                P90
              </TableCell>
              <TableCell align="right" sx={{ 
                fontWeight: 'bold', 
                minWidth: 70,
                backgroundColor: 'grey.500',
                borderBottom: 2,
                borderColor: 'divider'
              }}>
                Min
              </TableCell>
              <TableCell align="right" sx={{ 
                fontWeight: 'bold', 
                minWidth: 70,
                backgroundColor: 'grey.500',
                borderBottom: 2,
                borderColor: 'divider'
              }}>
                Max
              </TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {statsData.map((row, index) => (
              <TableRow 
                key={row.key} 
                hover 
                sx={{ 
                  '&:hover': { backgroundColor: 'action.hover' }
                }}
              >
                <TableCell component="th" scope="row" sx={{ borderRight: 1, borderColor: 'divider' }}>
                  <Box>
                    <Typography variant="body2" fontWeight="medium" sx={{ 
                      lineHeight: 1.3,
                      fontSize: '0.875rem'
                    }}>
                      {row.label}
                    </Typography>
                    <Typography variant="caption" color="text.secondary" sx={{ 
                      lineHeight: 1.2,
                      fontSize: '0.75rem',
                      display: 'block'
                    }}>
                      {row.description}
                    </Typography>
                  </Box>
                </TableCell>
                {row.stats ? (
                  <>
                    <TableCell align="right" sx={{ fontWeight: 500 }}>
                      {renderValueWithComparison(
                        row.stats.mean, 
                        row.comparison?.mean,
                        row.unit || "min"
                      )}
                    </TableCell>
                    <TableCell align="right">
                      {renderValueWithComparison(
                        row.stats.median, 
                        row.comparison?.median,
                        row.unit || "min"
                      )}
                    </TableCell>
                    <TableCell align="right">
                      {renderValueWithComparison(
                        row.stats.p75, 
                        row.comparison?.p75,
                        row.unit || "min"
                      )}
                    </TableCell>
                    <TableCell align="right">
                      {renderValueWithComparison(
                        row.stats.p90, 
                        row.comparison?.p90,
                        row.unit || "min"
                      )}
                    </TableCell>
                    <TableCell align="right">
                      {renderValueWithComparison(
                        row.stats.min, 
                        row.comparison?.min,
                        row.unit || "min"
                      )}
                    </TableCell>
                    <TableCell align="right">
                      {renderValueWithComparison(
                        row.stats.max, 
                        row.comparison?.max,
                        row.unit || "min"
                      )}
                    </TableCell>
                  </>
                ) : (
                  <TableCell align="center" colSpan={6}>
                    <Typography variant="body2" color="text.secondary" sx={{ fontStyle: 'italic' }}>
                      No data available
                    </Typography>
                  </TableCell>
                )}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  );
};

export default StatsTable;