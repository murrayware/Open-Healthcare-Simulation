import React, { useState, useMemo } from "react";
import { Box, Typography, Tabs, Tab } from "@mui/material";
import DistributionChart from "./DistributionChart";
import StatsTable from "./StatsTable";

/**
 * Diagnostic Imaging Tab Component
 * Displays metrics for each DI modality individually with sub-tabs
 */
const DiagnosticTab = ({ 
  defaultMetrics, 
  adjustedMetrics,
  title = "Diagnostic Imaging Performance Metrics"
}) => {
  const [activeModality, setActiveModality] = useState("");

  // Extract DI modality names from the data (prefer adjusted, fallback to default)
  const modalityNames = useMemo(() => {
    const metrics = adjustedMetrics || defaultMetrics;
    if (!metrics?.di) return [];
    return Object.keys(metrics.di).sort();
  }, [defaultMetrics, adjustedMetrics]);

  // Set initial modality when data loads
  React.useEffect(() => {
    if (modalityNames.length > 0 && !activeModality) {
      setActiveModality(modalityNames[0]);
    }
  }, [modalityNames, activeModality]);

  const handleModalityChange = (event, newValue) => {
    setActiveModality(newValue);
  };

  // Metrics configuration for DI modalities
  const diMetrics = useMemo(() => [
    {
      key: 'di_minutes',
      label: 'DI Test Duration',
      description: 'Time taken to complete the diagnostic imaging test',
      unit: 'min',
      isTimestamp: false
    }
  ], []);

  // Transform DI data into metrics_table format for StatsTable
  const transformDiDataForTable = useMemo(() => (metricsData, modalityName) => {
    if (!metricsData?.di?.[modalityName]) return null;

    const modalityData = metricsData.di[modalityName];
    const rows = [];

    // Create a row for each data point
    const maxLength = modalityData.di_minutes?.length || 0;

    for (let i = 0; i < maxLength; i++) {
      rows.push({
        id: i,
        di_minutes: modalityData.di_minutes?.[i] ?? null
      });
    }

    return {
      ...metricsData,
      metrics_table: rows
    };
  }, []);

  // Transform data for current modality - memoize to avoid unnecessary recalculations
  const transformedDefaultMetrics = useMemo(() => 
    defaultMetrics ? transformDiDataForTable(defaultMetrics, activeModality) : null,
    [defaultMetrics, activeModality, transformDiDataForTable]
  );
  
  const transformedAdjustedMetrics = useMemo(() => 
    adjustedMetrics ? transformDiDataForTable(adjustedMetrics, activeModality) : null,
    [adjustedMetrics, activeModality, transformDiDataForTable]
  );

  if ((!defaultMetrics?.di && !adjustedMetrics?.di) || modalityNames.length === 0) {
    return (
      <div className="flex items-center justify-center h-64">
        <Typography variant="body1" color="text.secondary">
          No diagnostic imaging data available
        </Typography>
      </div>
    );
  }

  // Guard against undefined modality data
  const currentModalityData = (adjustedMetrics || defaultMetrics)?.di?.[activeModality];
  if (!currentModalityData) {
    return (
      <div className="flex items-center justify-center h-64">
        <Typography variant="body1" color="text.secondary">
          Loading diagnostic imaging data...
        </Typography>
      </div>
    );
  }

  return (
    <Box>
      <Typography variant="h6" gutterBottom sx={{ mb: 3 }}>
        {title}
      </Typography>

      {/* DI Modality Sub-tabs */}
      <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 3 }}>
        <Tabs 
          value={activeModality} 
          onChange={handleModalityChange}
          variant="scrollable"
          scrollButtons="auto"
          allowScrollButtonsMobile
        >
          {modalityNames.map((name) => (
            <Tab key={name} value={name} label={name} />
          ))}
        </Tabs>
      </Box>

      {/* DI Statistics Table */}
      <Box sx={{ mb: 4 }}>
        <StatsTable
          defaultMetrics={transformedDefaultMetrics}
          adjustedMetrics={transformedAdjustedMetrics}
          metricsConfig={diMetrics}
          filterFunction={null}
          title={`${activeModality} - Summary Statistics`}
        />
      </Box>

      {/* Distribution Charts */}
      <Box>
        <Typography variant="h6" gutterBottom sx={{ mb: 3 }}>
          Distribution Charts - {activeModality}
        </Typography>
        <Box sx={{ 
          display: 'flex', 
          flexDirection: 'column', 
          gap: 3 
        }}>
          {diMetrics.map((metric) => (
            <DistributionChart
              key={metric.key}
              metric={metric}
              defaultMetrics={transformedDefaultMetrics}
              adjustedMetrics={transformedAdjustedMetrics}
              filterFunction={null}
              title={metric.label}
            />
          ))}
        </Box>
      </Box>
    </Box>
  );
};

export default DiagnosticTab;
