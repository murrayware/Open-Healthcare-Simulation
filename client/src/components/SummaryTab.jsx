import React, { useMemo } from "react";
import { Box, Typography } from "@mui/material";
import StatCard from "./StatCard";
import DistributionChart from "./DistributionChart";

/**
 * Summary Tab Component
 * Displays high-level summary statistics using StatCard components
 */
const SummaryTab = ({ 
  title = "Summary Metrics",
  defaultMetrics, 
  adjustedMetrics
}) => {
  // Calculate metrics from defaultMetrics
  const defaultStats = useMemo(() => {
    if (!defaultMetrics?.distributions) return null;
    
    const { distributions } = defaultMetrics;
    
    // 1. Total Arrivals
    const totalArrivals = distributions.arrival?.list_times?.length || 0;
    
    // 2. LWBS Count & Percentage
    const lwbsCount = distributions.lwbs?.list_times?.reduce((sum, val) => sum + (val || 0), 0) || 0;
    const lwbsPercent = totalArrivals > 0 ? ((lwbsCount / totalArrivals) * 100).toFixed(1) : 0;
    
    // 3. EMS Arrivals
    const emsArrivals = distributions.arrival_to_offload?.list_times?.length || 0;
    
    // 4. Admit Count & Percentage
    const admitCount = distributions.admit?.list_times?.reduce((sum, val) => sum + (val || 0), 0) || 0;
    const admitPercent = totalArrivals > 0 ? ((admitCount / totalArrivals) * 100).toFixed(1) : 0;
    
    // 5. Average Acuity
    const acuityValues = distributions.acuity?.list_times || [];
    const avgAcuity = acuityValues.length > 0 
      ? (acuityValues.reduce((sum, val) => sum + (val || 0), 0) / acuityValues.length).toFixed(2)
      : 0;
    
    return {
      totalArrivals,
      lwbsCount,
      lwbsPercent,
      emsArrivals,
      admitCount,
      admitPercent,
      avgAcuity
    };
  }, [defaultMetrics]);
  
  // Calculate metrics from adjustedMetrics
  const adjustedStats = useMemo(() => {
    if (!adjustedMetrics?.distributions) return null;
    
    const { distributions } = adjustedMetrics;
    
    // 1. Total Arrivals
    const totalArrivals = distributions.arrival?.list_times?.length || 0;
    
    // 2. LWBS Count & Percentage
    const lwbsCount = distributions.lwbs?.list_times?.reduce((sum, val) => sum + (val || 0), 0) || 0;
    const lwbsPercent = totalArrivals > 0 ? ((lwbsCount / totalArrivals) * 100).toFixed(1) : 0;
    
    // 3. EMS Arrivals
    const emsArrivals = distributions.arrival_to_offload?.list_times?.length || 0;
    
    // 4. Admit Count & Percentage
    const admitCount = distributions.admit?.list_times?.reduce((sum, val) => sum + (val || 0), 0) || 0;
    const admitPercent = totalArrivals > 0 ? ((admitCount / totalArrivals) * 100).toFixed(1) : 0;
    
    // 5. Average Acuity
    const acuityValues = distributions.acuity?.list_times || [];
    const avgAcuity = acuityValues.length > 0 
      ? (acuityValues.reduce((sum, val) => sum + (val || 0), 0) / acuityValues.length).toFixed(2)
      : 0;
    
    return {
      totalArrivals,
      lwbsCount,
      lwbsPercent,
      emsArrivals,
      admitCount,
      admitPercent,
      avgAcuity
    };
  }, [adjustedMetrics]);
  
  if (!defaultStats && !adjustedStats) {
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
      {/* Title */}
      <Typography variant="h6" sx={{ mb: 1 }}>
        {title}
      </Typography>
      
      <Box sx={{ display: 'flex', gap: 3, flexWrap: 'wrap' }}>
        <Box sx={{ flex: '1 1 0', minWidth: '200px' }}>
          <StatCard
            title="Total Arrivals"
            defaultValue={defaultStats?.totalArrivals || 0}
            unit=""
            showNoChangePillWhenDefaultOnly={true}
            isWholeNumber={true}
            changeType="neutral"
          />
        </Box>
        


        <Box sx={{ flex: '1 1 0', minWidth: '200px' }}>
          <StatCard
            title="EMS Arrivals"
            defaultValue={defaultStats?.emsArrivals || 0}
            unit=""
            showNoChangePillWhenDefaultOnly={true}
            isWholeNumber={true}
            changeType="neutral"
          />
        </Box>
        <Box sx={{ flex: '1 1 0', minWidth: '200px' }}>
          <StatCard
            title="LWBS"
            defaultValue={defaultStats?.lwbsPercent || 0}
            adjustedValue={adjustedStats?.lwbsPercent}
            unit="%"
            changeType="lower-is-better"
          />
        </Box>
        

        
        <Box sx={{ flex: '1 1 0', minWidth: '200px' }}>
          <StatCard
            title="Admit Rate"
            defaultValue={defaultStats?.admitPercent || 0}
            adjustedValue={adjustedStats?.admitPercent}
            unit="%"
          />
        </Box>
        
        <Box sx={{ flex: '1 1 0', minWidth: '200px' }}>
          <StatCard
            title="Average Acuity"
            defaultValue={defaultStats?.avgAcuity || 0}
            adjustedValue={adjustedStats?.avgAcuity}
            unit=""
          />
        </Box>
      </Box>

      {/* Charts Section */}
      <Box sx={{ mt: 4, display: 'flex', gap: 3, flexWrap: 'wrap' }}>
        <Box sx={{ flex: '1 1 0', minWidth: '400px' }}>
          <DistributionChart
            metric={{
              key: 'arrival',
              label: 'Arrivals by Hour',
              description: 'Distribution of patient arrivals throughout the day',
              unit: 'hour',
              isTimestamp: true,
              countLabel: 'arrivals'
            }}
            defaultMetrics={defaultMetrics}
            adjustedMetrics={adjustedMetrics}
            title="Arrivals per Hour of Day"
          />
        </Box>

        <Box sx={{ flex: '1 1 0', minWidth: '400px' }}>
          <DistributionChart
            metric={{
              key: 'ctas',
              label: 'CTAS Distribution',
              description: 'Distribution CTAS Levels among patients',
              unit: 'CTAS Level',
              isCategorical: true,
              showPercentage: true,
              showDataLabels: true,
              countLabel: 'patients'
            }}
            defaultMetrics={defaultMetrics}
            adjustedMetrics={adjustedMetrics}
            title="CTAS Distribution"
          />
        </Box>
      </Box>
    </Box>
  );
};

export default SummaryTab;
