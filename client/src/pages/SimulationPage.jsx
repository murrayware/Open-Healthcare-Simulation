import React, { useState, useEffect, useRef, useCallback, useMemo } from "react";
import { CircularProgress, Button, Tabs, Tab, Box, IconButton } from "@mui/material";
import PlayArrowIcon from "@mui/icons-material/PlayArrow";
import { useParams, useNavigate, useSearchParams } from "react-router-dom";
import { useSimulationWorkspace } from "../context/SimulationWorkspaceContext";
import Chart from "react-apexcharts";
import SettingsSidebar from "../components/SettingsSidebar";
import MetricsTab from "../components/MetricsTab";
import { roundFloats } from "../utils";
import apiFetch from "../api/client";
import { 
  EMS_METRICS_CONFIG,
  ED_FLOW_METRICS_CONFIG,
  INPATIENT_METRICS_CONFIG,
  LAB_DIAGNOSTIC_METRICS_CONFIG,
  FILTER_FUNCTIONS
} from "../config/metricsConfig";

/**
 * SimulationPage
 * - supports defaultMetrics (first run from homepage / preloaded hospital or preloadedMetrics)
 * - supports adjustedMetrics (any subsequent Run)
 * - UI displays the most recent adjustedMetrics if present, otherwise defaultMetrics
 */

const SimulationPage = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const { 
    getSimulation, 
    updateSimulation, 
    switchToSimulation 
  } = useSimulationWorkspace();
  
  const simulation = getSimulation(id);
  
  // If simulation doesn't exist, redirect to home
  useEffect(() => {
    if (!simulation) {
      navigate('/home');
      return;
    }
  }, [simulation, navigate]);

  // Switch to this simulation (updates lastAccessed) - only once when component mounts
  useEffect(() => {
    if (simulation && id) {
      switchToSimulation(id);
    }
  }, [id]); // Only depend on id, not on simulation or switchToSimulation

  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState("ed_flow");
  const [isDesktop, setIsDesktop] = useState(window.innerWidth >= 1024);
  const [tabLoading, setTabLoading] = useState(false);
  const autoRunExecutedRef = useRef(false);

  // Memoize the settings change handler to prevent infinite loops
  const handleSettingsChange = useCallback((updatedSettings) => {
    updateSimulation(id, { settings: updatedSettings });
  }, [id, updateSimulation]);

  // Monitor window size for responsive behavior
  useEffect(() => {
    const handleResize = () => {
      setIsDesktop(window.innerWidth >= 1024);
    };
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  // Debounced tab change for better performance
  const handleTabChange = useCallback((event, newValue) => {
    setTabLoading(true);
    setActiveTab(newValue);
    // Small delay to show loading state, then hide it
    setTimeout(() => setTabLoading(false), 100);
  }, []);

  // If no simulation found, show loading or redirect
  if (!simulation) {
    return (
      <Box display="flex" alignItems="center" justifyContent="center" height="100%">
        <CircularProgress />
      </Box>
    );
  }

  // Extract data from simulation
  const {
    name,
    defaultMetrics,
    adjustedMetrics,
    compareId,
    settings = {}
  } = simulation;

  // Extract settings data (backend format)
  const {
    doctors: simulationDoctors = [],
    arrivals: simulationArrivals = { 
      hours: 24, 
      walkin_hourly_lambda: [],
      admit_prob: 0.38,
      fasttrack_route_probability: 0.53,
      lwbs_threshold_dist: { type: "uniform", low: 60, high: 240 }
    },
    ems: simulationEms = { enabled: false },
    areas: simulationAreas = {},
    capabilities: simulationCapabilities = {},
    fasttrack: simulationFasttrack = { enabled: false },
    inpatient: simulationInpatient = { 
      units: {}, 
      direct_admits_enabled: true, 
      direct_admit_hours: 24, 
      direct_admit_hourly_lambda: {} 
    },
  } = settings;

  // active metrics shown in UI: adjusted if available, otherwise default
  const metrics = adjustedMetrics ?? defaultMetrics ?? null;

  // Helper functions for updating simulation data
  const updateSimulationData = (updates) => {
    updateSimulation(id, updates);
  };

  const setDefaultMetrics = (metrics) => {
    updateSimulationData({ defaultMetrics: metrics });
  };

  const setAdjustedMetrics = (metrics) => {
    updateSimulationData({ adjustedMetrics: metrics });
  };

  const setCompareId = (compareId) => {
    updateSimulationData({ compareId });
  };

  // Build settings payload for API calls (minimal transformation)
  const buildSettingsPayload = (areasOverride = null, arrivalsOverride = null) => {
    const areasToUse = areasOverride || simulationAreas;
    const arrivalsToUse = arrivalsOverride || simulationArrivals;

    return {
      hospital_id: simulation.hospitalKey.replace("hospital-", "").toUpperCase(),
      run_id: `sim-${id}-${Date.now()}`,
      seed: 99,
      run: { duration_minutes: 1440 },
      doctors: simulationDoctors,
      arrivals: arrivalsToUse,
      ems: simulationEms,
      inpatient: simulationInpatient,
      areas: areasToUse,
      capabilities: simulationCapabilities,
      fasttrack: simulationFasttrack,
    };
  };

  // Run simulation function
  const runSimulation = async () => {
    // For blank simulations, provide defaults in backend format
    let areasToUse = simulationAreas;
    let arrivalsToUse = simulationArrivals;
    
    // Provide default area if none configured
    if (!areasToUse || Object.keys(areasToUse).length === 0) {
      areasToUse = {
        "Main": {
          name: "Main",
          beds: 10,
          nurse_model: {
            model: "ratio",
            ratio: 2,
            lab_support: true,
          },
        }
      };
    }

    // Provide default arrivals if empty
    if (!arrivalsToUse.walkin_hourly_lambda || arrivalsToUse.walkin_hourly_lambda.length === 0) {
      arrivalsToUse = {
        ...arrivalsToUse,
        walkin_hourly_lambda: [1, 1, 2, 2, 3, 4, 6, 7, 8, 9, 9, 10, 10, 10, 9, 9, 8, 7, 6, 4, 3, 2, 2, 1],
        hours: 24
      };
    }

    setLoading(true);
    try {
      const payload = buildSettingsPayload(areasToUse, arrivalsToUse);
      
      // Determine run type based on existing metrics
      const runType = defaultMetrics ? "adjusted" : "default";
      const apiEndpoint = "/simulate";
      
      // Add run_type and compare_id to payload
      const fullPayload = {
        ...payload,
        run_type: runType,
        ...(runType === "adjusted" && compareId && { compare_id: compareId })
      };
      
      const result = await apiFetch(apiEndpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(fullPayload),
      });

      if (result) {
        const rounded = roundFloats(result);
        
        if (!defaultMetrics) {
          // First run - set as default metrics
          setDefaultMetrics(rounded);
          setAdjustedMetrics(null);
          
          // Capture compare_id if this was the first run
          if (result.compare_id) {
            setCompareId(result.compare_id);
          }
        } else {
          // Subsequent run - set as adjusted metrics
          setAdjustedMetrics(rounded);
        }
      }
    } catch (err) {
      console.error("Run failed:", err);
      alert("Simulation failed. See console for details.");
    } finally {
      setLoading(false);
    }
  };

  // Auto-run simulation when created from hospital template
  useEffect(() => {
    const shouldAutoRun = searchParams.get('autoRun') === 'true';
    
    if (shouldAutoRun && simulation && !loading && !defaultMetrics && !autoRunExecutedRef.current) {
      // Mark as executed to prevent double execution (React.StrictMode in dev)
      autoRunExecutedRef.current = true;
      
      // Clear the URL parameter to avoid running again
      setSearchParams(prev => {
        const newParams = new URLSearchParams(prev);
        newParams.delete('autoRun');
        return newParams;
      });
      
      // Auto-run the simulation
      runSimulation();
    }
  }, [simulation, loading, defaultMetrics]); // Don't include searchParams to avoid dependency cycle

  // Memoize the metrics tabs configuration to prevent re-creation on every render
  const metricsTabs = useMemo(() => [
    { 
      key: "ed_flow", 
      label: "ED Flow", 
      title: "Emergency Department Flow Metrics",
      metricsConfig: ED_FLOW_METRICS_CONFIG,
      filterFunction: FILTER_FUNCTIONS.edFlow
    },
    { 
      key: "ems", 
      label: "EMS", 
      title: "Emergency Medical Services Metrics",
      metricsConfig: EMS_METRICS_CONFIG,
      filterFunction: FILTER_FUNCTIONS.ems
    },
    { 
      key: "inpatient_consults", 
      label: "Inpatient Consults", 
      title: "Inpatient Consultation Metrics",
      metricsConfig: INPATIENT_METRICS_CONFIG,
      filterFunction: FILTER_FUNCTIONS.inpatient
    },
    { 
      key: "lab_diagnostic", 
      label: "Lab/Diagnostic", 
      title: "Laboratory and Diagnostic Metrics",
      metricsConfig: LAB_DIAGNOSTIC_METRICS_CONFIG,
      filterFunction: FILTER_FUNCTIONS.lab
    }
  ], []);

  const currentTab = useMemo(() => 
    metricsTabs.find(tab => tab.key === activeTab) || metricsTabs[0],
    [metricsTabs, activeTab]
  );

  return (
    <div className="h-full w-full relative overflow-hidden">
      {/* Settings Sidebar */}
      <SettingsSidebar
        simulation={simulation}
        onSettingsChange={handleSettingsChange}
      />

      {/* Main Content Area */}
      <div 
        className="h-full overflow-auto transition-all duration-300"
        style={{ 
          marginLeft: isDesktop ? '60px' : '0px'
        }}
      >
        <div className="flex w-full flex-col h-full">
          <div className="flex w-full py-4 sticky top-0 z-20">
          <div className="flex w-full items-center justify-left w-full">

            <div className="flex gap-2">
              <Button 
                color="primary" 
                variant='contained'
                onClick={runSimulation} 
                disabled={loading}
                sx={{
                  borderTopLeftRadius: 0,
                  borderBottomLeftRadius: 0,
                  height: 40,
                }}
              >
                Run
                {loading ? <CircularProgress color="inherit" size={20} /> : <PlayArrowIcon />}
              </Button>
            </div>
            {/* <h1 className="flex w-full text-center text-xl font-semibold text-text-primary self-center">
              {simulation?.name || `Simulation ${id}`}
            </h1> */}
          </div>
        </div>

        {loading ? (
          <div className="flex-1 flex items-center justify-center">
            <CircularProgress color="inherit" />
          </div>
        ) : !metrics ? (
          <div className="flex-1 flex items-center justify-center">
            <div className="flex flex-col items-center space-y-4">
              <div className="flex items-center space-x-4">
                <IconButton 
                  color="primary" 
                  onClick={runSimulation}
                  sx={{
                    backgroundColor: 'primary.main',
                    color: 'white',
                    '&:hover': {
                      backgroundColor: 'primary.dark',
                    },
                    width: 64,
                    height: 64,
                  }}
                >
                  <PlayArrowIcon sx={{ fontSize: 32 }} />
                </IconButton>
              </div>
              <p className="text-text-secondary">No data yet — configure settings and run the simulation.</p>
            </div>
          </div>
        ) : (
          <>
            {/* Tab Navigation */}
            <Box sx={{ borderBottom: 1, borderColor: 'divider', display: 'flex', justifyContent: 'center' }}>
              <Tabs 
                value={activeTab} 
                onChange={handleTabChange}
                variant="scrollable"
                scrollButtons="auto"
                allowScrollButtonsMobile
              >
                {metricsTabs.map((tab) => (
                  <Tab 
                    key={tab.key}
                    value={tab.key}
                    label={tab.label}
                  />
                ))}
              </Tabs>
            </Box>

            {/* Tab Content */}
            <div className="flex-1 p-4">
              {tabLoading ? (
                <div className="flex items-center justify-center h-64">
                  <CircularProgress color="inherit" />
                </div>
              ) : (
                <MetricsTab
                  key={activeTab} // Force re-mount for better performance isolation
                  title={currentTab.title}
                  defaultMetrics={defaultMetrics}
                  adjustedMetrics={adjustedMetrics}
                  metricsConfig={currentTab.metricsConfig}
                  filterFunction={currentTab.filterFunction}
                  showTable={true}
                  showCharts={true}
                />
              )}
            </div>
          </>
        )}
        </div>
      </div>
    </div>
  );
};

export default SimulationPage;
