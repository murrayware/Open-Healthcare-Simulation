import React, { useState, useEffect, useRef, useCallback, useMemo } from "react";
import { CircularProgress, Button, Tabs, Tab, Box, IconButton } from "@mui/material";
import PlayArrowIcon from "@mui/icons-material/PlayArrow";
import { useParams, useNavigate, useSearchParams } from "react-router-dom";
import { useSimulationWorkspace } from "../context/SimulationWorkspaceContext";
import Chart from "react-apexcharts";
import SettingsSidebar from "../components/SettingsSidebar";
import MetricsTab from "../components/MetricsTab";
import PhysiciansTab from "../components/PhysiciansTab";
import DiagnosticTab from "../components/DiagnosticTab";
import SummaryTab from "../components/SummaryTab";
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
  console.log('[SIMULATION PAGE] Component rendered with ID from URL:', id);
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const { 
    getSimulation, 
    updateSimulation, 
    switchToSimulation 
  } = useSimulationWorkspace();
  
  const simulation = getSimulation(id);
  console.log('[SIMULATION PAGE] Retrieved simulation:', simulation ? { id: simulation.id, name: simulation.name } : 'null');
  
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
  const [activeTab, setActiveTab] = useState("summary");
  const [isDesktop, setIsDesktop] = useState(window.innerWidth >= 1024);
  const [tabLoading, setTabLoading] = useState(false);
  const [settingsModified, setSettingsModified] = useState(false);
  const [tooltipDismissed, setTooltipDismissed] = useState(false);
  const autoRunExecutedRef = useRef(false);

  // Memoize the settings change handler to prevent infinite loops
  const handleSettingsChange = useCallback((updatedSettings) => {
    updateSimulation(id, { settings: updatedSettings });
    setSettingsModified(true);
    console.log("Settings modified for simulation", id);
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

  // Extract data from simulation (with safe defaults)
  const {
    name,
    defaultMetrics,
    adjustedMetrics,
    compareId,
    settings = {},
    defaultSettings = null,
    isFromTemplate = true // default to true for backward compatibility
  } = simulation || {};

  // Load default settings from database if not already loaded
  useEffect(() => {
    const loadDefaultSettings = async () => {
      console.log('[DEFAULT SETTINGS] Check:', { 
        hasSimulation: !!simulation, 
        hasDefaultMetrics: !!defaultMetrics, 
        hasDefaultSettings: !!defaultSettings, 
        hasCompareId: !!compareId,
        simulationId: id
      });
      
      // Only load if:
      // 1. We have metrics (simulation has been run)
      // 2. We don't have defaultSettings yet
      // 3. We have a compareId (confirms simulation was saved to database)
      if (!simulation || !defaultMetrics || defaultSettings || !compareId) {
        return;
      }
      
      console.log('[DEFAULT SETTINGS] Fetching from database for simulation:', id);
      
      // Small delay to ensure database write has completed
      await new Promise(resolve => setTimeout(resolve, 100));
      
      try {
        // Try to get the first input settings from the database using simulation_id
        const response = await apiFetch(`/api/inputs/first/${id}`, {
          method: "GET"
        });

        if (response && response.settings) {
          console.log('[DEFAULT SETTINGS] Loaded from database successfully');
          // Update simulation with the default settings from first run
          updateSimulationData({ defaultSettings: response.settings });
        }
      } catch (err) {
        // Silently handle 404 - it's expected for old simulations or after database recreation
        // No action needed, simulation will work normally without default settings
        console.error('[DEFAULT SETTINGS] Failed to load:', err);
        if (err.status !== 404) {
          console.warn("Could not load default settings from database:", err);
        }
      }
    };

    loadDefaultSettings();
  }, [id, simulation, defaultMetrics, defaultSettings, compareId]);

  // Reset settingsModified and tooltip flags when simulation changes or results change
  useEffect(() => {
    setSettingsModified(false);
    setTooltipDismissed(false);
  }, [id, defaultMetrics, adjustedMetrics]);

  // If no simulation found, show loading or redirect
  if (!simulation) {
    return (
      <Box display="flex" alignItems="center" justifyContent="center" height="100%">
        <CircularProgress />
      </Box>
    );
  }

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
    // Don't capture defaultSettings here - it will be loaded from database
    updateSimulationData({ 
      defaultMetrics: metrics
    });
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

    console.log('[SIMULATION PAGE] Building payload with simulation_id:', id, 'name:', simulation.name);
    return {
      hospital_id: simulation.templateName || null,
      run_id: `sim-${id}-${Date.now()}`,
      simulation_id: id,  // Constant identifier for grouping all runs of this simulation
      simulation_name: simulation.name,  // Store the simulation name in database
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
          
          // Don't set defaultSettings here - let the useEffect fetch it from database
          // This ensures we always get the actual first-run settings from the database
          
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
      key: "summary", 
      label: "Summary", 
      title: "Summary Metrics",
      component: 'summary'
    },
    { 
      key: "ed_flow", 
      label: "ED Flow", 
      title: "Emergency Department Flow Metrics",
      metricsConfig: ED_FLOW_METRICS_CONFIG,
      filterFunction: FILTER_FUNCTIONS.edFlow,
      component: 'metrics'
    },
    { 
      key: "ems", 
      label: "EMS", 
      title: "Emergency Medical Services Metrics",
      metricsConfig: EMS_METRICS_CONFIG,
      filterFunction: FILTER_FUNCTIONS.ems,
      component: 'metrics'
    },
    { 
      key: "physicians", 
      label: "Physicians", 
      title: "Physician Performance Metrics",
      component: 'physicians'
    },
    { 
      key: "diagnostic", 
      label: "Diagnostic", 
      title: "Diagnostic Imaging Metrics",
      component: 'diagnostic'
    },
    // { 
    //   key: "inpatient_consults", 
    //   label: "Inpatient Consults", 
    //   title: "Inpatient Consultation Metrics",
    //   metricsConfig: INPATIENT_METRICS_CONFIG,
    //   filterFunction: FILTER_FUNCTIONS.inpatient,
    //   component: 'metrics'
    // },
    // { 
    //   key: "lab_diagnostic", 
    //   label: "Lab/Diagnostic", 
    //   title: "Laboratory and Diagnostic Metrics",
    //   metricsConfig: LAB_DIAGNOSTIC_METRICS_CONFIG,
    //   filterFunction: FILTER_FUNCTIONS.lab,
    //   component: 'metrics'
    // }
  ], []);

  const currentTab = useMemo(() => 
    metricsTabs.find(tab => tab.key === activeTab) || metricsTabs[0],
    [metricsTabs, activeTab]
  );

  // Calculate if tooltip should show (when defaultSettings exist and settings haven't been modified yet)
  const shouldShowTooltip = !!defaultSettings && !settingsModified && !tooltipDismissed && !loading;

  return (
    <div className="h-full w-full relative overflow-hidden">
      {/* Settings Sidebar */}
      <SettingsSidebar
        simulation={simulation}
        onSettingsChange={handleSettingsChange}
        showTooltip={shouldShowTooltip}
        onTooltipDismiss={() => setTooltipDismissed(true)}
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
              <div
                onClick={() => {
                  const isDisabled = loading || (metrics && !settingsModified) || (!isFromTemplate && !settingsModified);
                  if (isDisabled && !isFromTemplate && !settingsModified) {
                    setTooltipDismissed(false);
                  }
                }}
                style={{ display: 'inline-block' }}
              >
                <Button 
                  color="primary" 
                  variant='contained'
                  onClick={runSimulation}
                  disabled={loading || (metrics && !settingsModified) || (!isFromTemplate && !settingsModified)}
                  sx={{
                    borderTopLeftRadius: 0,
                    borderBottomLeftRadius: 0,
                    height: 40,
                    pointerEvents: (loading || (metrics && !settingsModified) || (!isFromTemplate && !settingsModified)) ? 'none' : 'auto',
                  }}
                >
                  Run
                  {loading ? <CircularProgress color="inherit" size={20} /> : <PlayArrowIcon />}
                </Button>
              </div>
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
                <div
                  onClick={() => {
                    const isDisabled = loading || (!isFromTemplate && !settingsModified);
                    if (isDisabled && !isFromTemplate && !settingsModified) {
                      setTooltipDismissed(false);
                    }
                  }}
                  style={{ display: 'inline-block' }}
                >
                  <IconButton 
                    color="primary" 
                    onClick={runSimulation}
                    disabled={loading || (!isFromTemplate && !settingsModified)}
                    sx={{
                      backgroundColor: (!isFromTemplate && !settingsModified) ? 'action.disabledBackground' : 'primary.main',
                      color: (!isFromTemplate && !settingsModified) ? 'action.disabled' : 'white',
                      '&:hover': {
                        backgroundColor: (!isFromTemplate && !settingsModified) ? 'action.disabledBackground' : 'primary.dark',
                      },
                      width: 64,
                      height: 64,
                      pointerEvents: (loading || (!isFromTemplate && !settingsModified)) ? 'none' : 'auto',
                    }}
                  >
                    <PlayArrowIcon sx={{ fontSize: 32 }} />
                  </IconButton>
                </div>
              </div>
              <p className="text-text-secondary">
                {!isFromTemplate && !settingsModified
                  ? "Configure settings in the sidebar to enable running the simulation."
                  : "No data yet — run the simulation to see results."}
              </p>
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
              ) : currentTab.component === 'summary' ? (
                <SummaryTab
                  key={activeTab}
                  title={currentTab.title}
                  defaultMetrics={defaultMetrics}
                  adjustedMetrics={adjustedMetrics}
                />
              ) : currentTab.component === 'physicians' ? (
                <PhysiciansTab
                  key={activeTab}
                  title={currentTab.title}
                  defaultMetrics={defaultMetrics}
                  adjustedMetrics={adjustedMetrics}
                />
              ) : currentTab.component === 'diagnostic' ? (
                <DiagnosticTab
                  key={activeTab}
                  title={currentTab.title}
                  defaultMetrics={defaultMetrics}
                  adjustedMetrics={adjustedMetrics}
                />
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
