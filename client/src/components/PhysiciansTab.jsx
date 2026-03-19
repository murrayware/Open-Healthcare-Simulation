import React, { useState, useMemo } from "react";
import { Box, Typography, Tabs, Tab } from "@mui/material";
import DistributionChart from "./DistributionChart";
import StatsTable from "./StatsTable";

/**
 * Physicians Tab Component
 * Displays metrics for each physician individually with sub-tabs
 */
const PhysiciansTab = ({ 
  defaultMetrics, 
  adjustedMetrics,
  title = "Physician Performance Metrics"
}) => {
  const [activePhysician, setActivePhysician] = useState("");

  // Extract physician names from the data (prefer adjusted, fallback to default)
  const physicianNames = useMemo(() => {
    const metrics = adjustedMetrics || defaultMetrics;
    if (!metrics?.physicians) return [];
    return Object.keys(metrics.physicians).sort();
  }, [defaultMetrics, adjustedMetrics]);

  // Set initial physician when data loads
  React.useEffect(() => {
    if (physicianNames.length > 0 && !activePhysician) {
      setActivePhysician(physicianNames[0]);
    }
  }, [physicianNames, activePhysician]);

  const handlePhysicianChange = (event, newValue) => {
    setActivePhysician(newValue);
  };

  // Metrics configuration for physicians
  const physicianMetrics = useMemo(() => [
    {
      key: 'doc_to_disp',
      label: 'Assessment to Disposition',
      description: 'Time from initial physician assessment to disposition decision',
      unit: 'min',
      isTimestamp: false
    },
    {
      key: 'bed_to_doc',
      label: 'Bed to Assessment',
      description: 'Time from bed placement to physician assessment',
      unit: 'min',
      isTimestamp: false
    },
    {
      key: 'treatment_start',
      label: 'Treatment Start Times',
      description: 'Distribution of treatment start times throughout the day',
      unit: 'hour',
      isTimestamp: true
    }
  ], []);

  // Transform physician data into metrics_table format for StatsTable
  const transformPhysicianDataForTable = useMemo(() => (metricsData, physicianName) => {
    if (!metricsData?.physicians?.[physicianName]) return null;

    const physicianData = metricsData.physicians[physicianName];
    const rows = [];

    // Create a row for each data point with all metrics
    const maxLength = Math.max(
      physicianData.doc_to_disp?.length || 0,
      physicianData.bed_to_doc?.length || 0,
      physicianData.treatment_start?.length || 0
    );

    for (let i = 0; i < maxLength; i++) {
      rows.push({
        id: i,
        doc_to_disp: physicianData.doc_to_disp?.[i] ?? null,
        bed_to_doc: physicianData.bed_to_doc?.[i] ?? null,
        treatment_start: physicianData.treatment_start?.[i] ?? null
      });
    }

    return {
      ...metricsData,
      metrics_table: rows
    };
  }, []);

  // Transform data for current physician - memoize to avoid unnecessary recalculations
  const transformedDefaultMetrics = useMemo(() => 
    defaultMetrics ? transformPhysicianDataForTable(defaultMetrics, activePhysician) : null,
    [defaultMetrics, activePhysician, transformPhysicianDataForTable]
  );
  
  const transformedAdjustedMetrics = useMemo(() => 
    adjustedMetrics ? transformPhysicianDataForTable(adjustedMetrics, activePhysician) : null,
    [adjustedMetrics, activePhysician, transformPhysicianDataForTable]
  );

  if ((!defaultMetrics?.physicians && !adjustedMetrics?.physicians) || physicianNames.length === 0) {
    return (
      <div className="flex items-center justify-center h-64">
        <Typography variant="body1" color="text.secondary">
          No physician data available
        </Typography>
      </div>
    );
  }

  // Guard against undefined physician data
  const currentPhysicianData = (adjustedMetrics || defaultMetrics)?.physicians?.[activePhysician];
  if (!currentPhysicianData) {
    return (
      <div className="flex items-center justify-center h-64">
        <Typography variant="body1" color="text.secondary">
          Loading physician data...
        </Typography>
      </div>
    );
  }

  return (
    <Box>
      <Typography variant="h6" gutterBottom sx={{ mb: 3 }}>
        {title}
      </Typography>

      {/* Physician Sub-tabs */}
      <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 3 }}>
        <Tabs 
          value={activePhysician} 
          onChange={handlePhysicianChange}
          variant="scrollable"
          scrollButtons="auto"
          allowScrollButtonsMobile
        >
          {physicianNames.map((name) => (
            <Tab key={name} value={name} label={name} />
          ))}
        </Tabs>
      </Box>

      {/* Physician Statistics Table */}
      <Box sx={{ mb: 4 }}>
        <StatsTable
          defaultMetrics={transformedDefaultMetrics}
          adjustedMetrics={transformedAdjustedMetrics}
          metricsConfig={physicianMetrics}
          filterFunction={null}
          title={`${activePhysician} - Summary Statistics`}
        />
      </Box>

      {/* Distribution Charts */}
      <Box>
        <Typography variant="h6" gutterBottom sx={{ mb: 3 }}>
          Distribution Charts - {activePhysician}
        </Typography>
        <Box sx={{ 
          display: 'flex', 
          flexDirection: 'column', 
          gap: 3 
        }}>
          {Array.from({ length: Math.ceil(physicianMetrics.length / 2) }).map((_, rowIndex) => (
            <Box key={rowIndex} sx={{ 
              display: 'flex', 
              gap: 3, 
              '& > *': { flex: 1 }
            }}>
              {physicianMetrics.slice(rowIndex * 2, rowIndex * 2 + 2).map((metric) => (
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
          ))}
        </Box>
      </Box>
    </Box>
  );
};

export default PhysiciansTab;
