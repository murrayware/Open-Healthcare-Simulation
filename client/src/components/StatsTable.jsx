import React from "react";
import { 
  Table, 
  TableBody, 
  TableCell, 
  TableContainer, 
  TableHead, 
  TableRow, 
  Paper,
  Typography,
  Box
} from "@mui/material";
import { useAppTheme } from "../theme/useTheme";

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
  const theme = useAppTheme();
  if ((!defaultMetrics || !defaultMetrics.metrics_table) && (!adjustedMetrics || !adjustedMetrics.metrics_table)) {
    return (
      <div className="flex items-center justify-center h-64">
        <Typography variant="body1" color="text.secondary">
          No data available
        </Typography>
      </div>
    );
  }
  
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

  // Calculate stats for both default and adjusted
  const defaultFilteredData = filterFunction && defaultMetrics?.metrics_table
    ? defaultMetrics.metrics_table.filter(filterFunction)
    : defaultMetrics?.metrics_table || [];
  
  const adjustedFilteredData = filterFunction && adjustedMetrics?.metrics_table
    ? adjustedMetrics.metrics_table.filter(filterFunction)
    : adjustedMetrics?.metrics_table || [];
  
  const statsData = metricsConfig.flatMap(metric => {
    const rows = [];
    const defaultStats = defaultMetrics?.metrics_table
      ? calculateStats(defaultFilteredData, metric.key)
      : null;
    const adjustedStats = adjustedMetrics?.metrics_table
      ? calculateStats(adjustedFilteredData, metric.key)
      : null;

    if (defaultMetrics?.metrics_table) {
      rows.push({
        ...metric,
        scenario: "Default",
        stats: defaultStats,
        comparison: null
      });
    }

    if (adjustedMetrics?.metrics_table) {
      let comparison = null;
      if (adjustedStats && defaultStats) {
        comparison = {
          mean: adjustedStats.mean - defaultStats.mean,
          median: adjustedStats.median - defaultStats.median,
          p75: adjustedStats.p75 - defaultStats.p75,
          p90: adjustedStats.p90 - defaultStats.p90,
          min: adjustedStats.min - defaultStats.min,
          max: adjustedStats.max - defaultStats.max
        };
      }

      rows.push({
        ...metric,
        scenario: "Adjusted",
        stats: adjustedStats,
        comparison
      });
    }

    return rows;
  });

  const groupedStatsData = statsData.reduce((acc, row) => {
    const existing = acc.find(group => group.key === row.key);
    if (existing) {
      existing.rows.push(row);
    } else {
      acc.push({
        key: row.key,
        label: row.label,
        description: row.description,
        rows: [row]
      });
    }
    return acc;
  }, []);

  const formatValue = (value, unit = "min") => {
    if (value === null || value === undefined) return 'N/A';
    const roundedValue = Math.round(value * 10) / 10;
    return `${roundedValue} ${unit}`;
  };

  const renderValueWithComparison = (value, comparisonValue, unit = "min", isDefaultRow = false) => {
    if (value === null || value === undefined) return 'N/A';

    const formattedValue = formatValue(value, unit);

    if (comparisonValue === null || comparisonValue === undefined) {
      return (
        <Box
          textAlign="right"
          sx={{
            opacity: isDefaultRow ? 0.35 : 1,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'flex-end',
            minHeight: 32
          }}
        >
          <Typography sx={{ fontSize: '0.875rem' }}>
            {formattedValue}
          </Typography>
        </Box>
      );
    }

    const absChange = Math.abs(comparisonValue);
    const isSignificant = absChange >= 0.1;

    if (!isSignificant) {
      return (
        <Box textAlign="right" sx={{ opacity: isDefaultRow ? 0.35 : 1 }}>
          <Typography sx={{ fontSize: '0.875rem' }}>
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

    const isImprovement = comparisonValue < 0;
    const changeAmount = Math.round(Math.abs(comparisonValue) * 10) / 10;
    const signSymbol = isImprovement ? '-' : '+';
    const changeColor = isImprovement ? 'success.main' : 'error.main';

    return (
      <Box textAlign="right" sx={{ opacity: isDefaultRow ? 0.35 : 1 }}>
        <Typography sx={{ fontSize: '0.875rem' }}>
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
  };

  return (
    <Box>
      {/* Heading */}
      <Box sx={{ 
        display: 'flex', 
        justifyContent: 'flex-start',
        alignItems: 'flex-end',
        mb: '-1px',
        position: 'relative',
        zIndex: 2
      }}>
        <Typography variant="subtitle2" fontWeight="bold" color="text.primary" sx={{ mb: 1 }}>
          Statistics
        </Typography>
      </Box>

      {/* Statistics Table */}
      <TableContainer component={Paper} elevation={0} sx={{ maxHeight: 400, backgroundColor: theme.colors.background.paper }}>
        <Table size="small" stickyHeader sx={{ '& .MuiTableCell-root': { py: 0.75, px: 2 } }}>
          <TableHead>
            {/* Column headers */}
            <TableRow>
              <TableCell sx={{ 
                fontWeight: 'bold',
                color: theme.colors.text.primary,
                minWidth: 200, 
                backgroundColor: theme.colors.background.elevated,
                borderBottom: 2,
                borderColor: theme.colors.divider || 'rgba(255,255,255,0.12)',
                py: 0.75
              }}>
                Metric
              </TableCell>
              <TableCell sx={{ 
                fontWeight: 'bold',
                color: theme.colors.text.primary,
                minWidth: 90,
                backgroundColor: theme.colors.background.elevated,
                borderBottom: 2,
                borderColor: theme.colors.divider || 'rgba(255,255,255,0.12)',
                py: 0.5
              }}>
                Scenario
              </TableCell>
              <TableCell align="right" sx={{ 
                fontWeight: 'bold',
                color: theme.colors.text.primary,
                minWidth: 70,
                backgroundColor: theme.colors.background.elevated,
                borderBottom: 2,
                borderColor: theme.colors.divider || 'rgba(255,255,255,0.12)',
                py: 0.5
              }}>
                Mean
              </TableCell>
              <TableCell align="right" sx={{ 
                fontWeight: 'bold',
                color: theme.colors.text.primary,
                minWidth: 70,
                backgroundColor: theme.colors.background.elevated,
                borderBottom: 2,
                borderColor: theme.colors.divider || 'rgba(255,255,255,0.12)',
                py: 0.5
              }}>
                Median
              </TableCell>
              <TableCell align="right" sx={{ 
                fontWeight: 'bold',
                color: theme.colors.text.primary,
                minWidth: 70,
                backgroundColor: theme.colors.background.elevated,
                borderBottom: 2,
                borderColor: theme.colors.divider || 'rgba(255,255,255,0.12)',
                py: 0.5
              }}>
                P75
              </TableCell>
              <TableCell align="right" sx={{ 
                fontWeight: 'bold',
                color: theme.colors.text.primary,
                minWidth: 70,
                backgroundColor: theme.colors.background.elevated,
                borderBottom: 2,
                borderColor: theme.colors.divider || 'rgba(255,255,255,0.12)',
                py: 0.5
              }}>
                P90
              </TableCell>
              <TableCell align="right" sx={{ 
                fontWeight: 'bold',
                color: theme.colors.text.primary,
                minWidth: 70,
                backgroundColor: theme.colors.background.elevated,
                borderBottom: 2,
                borderColor: theme.colors.divider || 'rgba(255,255,255,0.12)',
                py: 0.5
              }}>
                Min
              </TableCell>
              <TableCell align="right" sx={{ 
                fontWeight: 'bold',
                color: theme.colors.text.primary,
                minWidth: 70,
                backgroundColor: theme.colors.background.elevated,
                borderBottom: 2,
                borderColor: theme.colors.divider || 'rgba(255,255,255,0.12)',
                py: 0.5
              }}>
                Max
              </TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {groupedStatsData.map((group) => (
              <React.Fragment key={group.key}>
                {group.rows.map((row, rowIndex) => (
                  (() => {
                    const isLastRowInGroup = rowIndex === group.rows.length - 1;
                    const dividerColor = theme.colors.divider || 'rgba(255,255,255,0.12)';
                    const rowBorder = isLastRowInGroup
                      ? `1px solid ${dividerColor}`
                      : 'none';
                    const rowBackground = row.scenario === 'Adjusted'
                      ? theme.colors.background.elevated
                      : theme.colors.background.paper;

                    return (
                  <TableRow 
                    key={`${row.key}-${row.scenario}`} 
                    hover 
                    sx={{ 
                      height: 44,
                      backgroundColor: rowBackground,
                      '&:hover': { backgroundColor: theme.colors.background.surface },
                      '& .MuiTableCell-root:not([rowspan])': {
                        verticalAlign: 'middle',
                        borderBottom: rowBorder,
                        backgroundColor: rowBackground
                      }
                    }}
                  >
                    {rowIndex === 0 && (
                      <TableCell
                        component="th"
                        scope="row"
                        rowSpan={group.rows.length}
                        sx={{ 
                          borderRight: `1px solid ${dividerColor}`,
                          verticalAlign: 'top',
                          borderBottom: `1px solid ${dividerColor}`,
                          backgroundColor: theme.colors.background.paper
                        }}
                      >
                        <Box>
                          <Typography variant="body2" fontWeight="medium" sx={{ 
                            lineHeight: 1.3,
                            fontSize: '0.875rem'
                          }}>
                            {group.label}
                          </Typography>
                          <Typography variant="caption" color="text.secondary" sx={{ 
                            lineHeight: 1.2,
                            fontSize: '0.75rem',
                            display: 'block'
                          }}>
                            {group.description}
                          </Typography>
                        </Box>
                      </TableCell>
                    )}

                    <TableCell sx={{ borderRight: `1px solid ${dividerColor}` }}>
                      <Typography variant="body2" fontWeight="medium" sx={{ fontSize: '0.8rem' }}>
                        {row.scenario}
                      </Typography>
                    </TableCell>
                    {row.stats ? (
                      <>
                        <TableCell align="right" sx={{ fontWeight: 500 }}>
                          {renderValueWithComparison(row.stats.mean, row.comparison?.mean, row.unit || "min", row.scenario === "Default")}
                        </TableCell>
                        <TableCell align="right">
                          {renderValueWithComparison(row.stats.median, row.comparison?.median, row.unit || "min", row.scenario === "Default")}
                        </TableCell>
                        <TableCell align="right">
                          {renderValueWithComparison(row.stats.p75, row.comparison?.p75, row.unit || "min", row.scenario === "Default")}
                        </TableCell>
                        <TableCell align="right">
                          {renderValueWithComparison(row.stats.p90, row.comparison?.p90, row.unit || "min", row.scenario === "Default")}
                        </TableCell>
                        <TableCell align="right">
                          {renderValueWithComparison(row.stats.min, row.comparison?.min, row.unit || "min", row.scenario === "Default")}
                        </TableCell>
                        <TableCell align="right">
                          {renderValueWithComparison(row.stats.max, row.comparison?.max, row.unit || "min", row.scenario === "Default")}
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
                    );
                  })()
                ))}
              </React.Fragment>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  );
};

export default StatsTable;