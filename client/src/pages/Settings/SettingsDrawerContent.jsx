// SettingsDrawerContent.jsx - Full settings content for use in drawers
import React, { useState, useEffect, useCallback, useRef, useMemo } from "react";
import { Button, Typography, Box, Tabs, Tab, IconButton } from "@mui/material";
import SettingsIcon from "@mui/icons-material/Settings";
import ChevronLeftIcon from "@mui/icons-material/ChevronLeft";
import PhysiciansSection from "./physicians/PhysiciansSection";
import EdArrivalsSection, { defaultArrivals } from "./ed/EdArrivalsSection";
import EmsSection, { defaultEms } from "./ems/EmsSection";
import InpatientSection from "./inpatient/InpatientSection";
import EDAreasSection from "./ed/EDAreasSection";
import CapabilitiesSection, { defaultCapabilities } from "./capabilities/CapabilitiesSection";

// Debounce hook for performance optimization
const useDebounce = (value, delay) => {
  const [debouncedValue, setDebouncedValue] = useState(value);

  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    return () => {
      clearTimeout(handler);
    };
  }, [value, delay]);

  return debouncedValue;
};

// Tab Panel component
function TabPanel({ children, value, index, ...other }) {
  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`settings-tabpanel-${index}`}
      aria-labelledby={`settings-tab-${index}`}
      {...other}
    >
      {value === index && (
        <Box sx={{ pt: 3 }}>
          {children}
        </Box>
      )}
    </div>
  );
}

const SettingsDrawerContent = ({ onClose, simulation, onSettingsChange, quickAction = null }) => {
  // Tab state
  const [activeTab, setActiveTab] = useState(0);

  // Tab change handler
  const handleTabChange = (event, newValue) => {
    setActiveTab(newValue);
  };

  useEffect(() => {
    if (!quickAction?.target || !quickAction?.token) return;

    if (quickAction.target === "add-inpatient-unit") {
      setActiveTab(2);
      return;
    }

    if (quickAction.target === "add-physician" || quickAction.target === "add-ed-area") {
      setActiveTab(0);
    }
  }, [quickAction?.token, quickAction?.target]);

  // Initialize settings from simulation using backend format
  const [doctors, setDoctors] = useState(simulation?.settings?.doctors || []);
  const [arrivals, setArrivals] = useState(simulation?.settings?.arrivals || { 
    hours: 24, 
    walkin_hourly_lambda: [], 
    admit_prob: 0.38, 
    fasttrack_route_probability: 0.53,
    lwbs_threshold_dist: { type: "uniform", low: 60, high: 240 }
  });
  const [ems, setEms] = useState(simulation?.settings?.ems || { 
    enabled: false, 
    schema_version: 1, 
    hours: defaultEms.hours, 
    hourly_lambda: defaultEms.hourly_lambda, 
    offload_nurses_per_hour: defaultEms.offload_nurses_per_hour, 
    ctas_mix: defaultEms.ctas_mix 
  });
  const [areas, setAreas] = useState(simulation?.settings?.areas || {});
  const [capabilities, setCapabilities] = useState(() => ({
    ...defaultCapabilities,
    ...(simulation?.settings?.capabilities || {})
  }));
  const [fasttrack, setFasttrack] = useState(simulation?.settings?.fasttrack || { enabled: false });
  const [inpatient, setInpatient] = useState(simulation?.settings?.inpatient || { 
    units: {}, 
    direct_admits_enabled: true, 
    direct_admit_hours: 24, 
    direct_admit_hourly_lambda: {} 
  });

  // Update local state when simulation changes (backend format)
  useEffect(() => {
    if (simulation?.settings) {
      setDoctors(simulation.settings.doctors || []);
      setArrivals(simulation.settings.arrivals || { 
        hours: 24, 
        walkin_hourly_lambda: [], 
        admit_prob: 0.38, 
        fasttrack_route_probability: 0.53,
        lwbs_threshold_dist: { type: "uniform", low: 60, high: 240 }
      });
      setEms(simulation.settings.ems || { 
        enabled: false, 
        schema_version: 1, 
        hours: defaultEms.hours, 
        hourly_lambda: defaultEms.hourly_lambda, 
        offload_nurses_per_hour: defaultEms.offload_nurses_per_hour, 
        ctas_mix: defaultEms.ctas_mix 
      });
      setAreas(simulation.settings.areas || {});
      setCapabilities({
        ...defaultCapabilities,
        ...(simulation.settings.capabilities || {})
      });
      setFasttrack(simulation.settings.fasttrack || { enabled: false });
      setInpatient(simulation.settings.inpatient || { 
        units: {}, 
        direct_admits_enabled: true, 
        direct_admit_hours: 24, 
        direct_admit_hourly_lambda: {} 
      });
    }
  }, [simulation?.id, simulation?.name]); // Only reset when switching simulations

  // Track if this is the initial render to avoid unnecessary auto-save
  const isInitialRender = useRef(true);
  const previousSettings = useRef(null);
  const onSettingsChangeRef = useRef(onSettingsChange);

  // Update the callback ref when onSettingsChange changes
  useEffect(() => {
    onSettingsChangeRef.current = onSettingsChange;
  }, [onSettingsChange]);

  // Create a memoized settings object to avoid unnecessary recalculations
  const currentSettings = useMemo(() => ({
    doctors,
    arrivals,
    ems,
    areas,
    capabilities,
    fasttrack,
    inpatient
  }), [doctors, arrivals, ems, areas, capabilities, fasttrack, inpatient]);

  // Debounce settings to avoid excessive auto-save calls
  const debouncedSettings = useDebounce(currentSettings, 500); // 500ms delay

  // Auto-save settings with debouncing
  useEffect(() => {
    // Skip auto-save on initial render to avoid unnecessary calls
    if (isInitialRender.current) {
      isInitialRender.current = false;
      previousSettings.current = debouncedSettings;
      return;
    }
    
    // Check if settings actually changed to prevent infinite loops
    const settingsChanged = JSON.stringify(previousSettings.current) !== JSON.stringify(debouncedSettings);
    
    if (settingsChanged && debouncedSettings) {
      previousSettings.current = debouncedSettings;
      // Use the callback ref to avoid dependency issues
      if (typeof onSettingsChangeRef.current === 'function') {
        onSettingsChangeRef.current(debouncedSettings);
      }
    }
  }, [debouncedSettings]); // Only depend on debouncedSettings

  const handleResetToDefault = () => {
    if (simulation?.defaultSettings) {
      const defaults = simulation.defaultSettings;
      
      // Reset all individual state pieces
      setDoctors(defaults.doctors || []);
      setArrivals(defaults.arrivals || { 
        hours: 24, 
        walkin_hourly_lambda: [], 
        admit_prob: 0.38, 
        fasttrack_route_probability: 0.53,
        lwbs_threshold_dist: { type: "uniform", low: 60, high: 240 }
      });
      setEms(defaults.ems || { enabled: false });
      setAreas(defaults.areas || {});
      setCapabilities(defaults.capabilities || defaultCapabilities);
      setFasttrack(defaults.fasttrack || { enabled: false });
      setInpatient(defaults.inpatient || { 
        units: {}, 
        direct_admits_enabled: true, 
        direct_admit_hours: 24, 
        direct_admit_hourly_lambda: {} 
      });
      
      // Manually trigger settings change immediately (bypass debounce)
      if (typeof onSettingsChange === 'function') {
        const resetSettings = {
          doctors: defaults.doctors || [],
          arrivals: defaults.arrivals || { hours: 24, walkin_hourly_lambda: [], admit_prob: 0.38, fasttrack_route_probability: 0.53, lwbs_threshold_dist: { type: "uniform", low: 60, high: 240 } },
          ems: defaults.ems || { enabled: false },
          areas: defaults.areas || {},
          capabilities: defaults.capabilities || defaultCapabilities,
          fasttrack: defaults.fasttrack || { enabled: false },
          inpatient: defaults.inpatient || { units: {}, direct_admits_enabled: true, direct_admit_hours: 24, direct_admit_hourly_lambda: {} }
        };
        onSettingsChange(resetSettings);
      }
    }
  };

  const hasDefaultSettings = simulation?.defaultSettings !== null && simulation?.defaultSettings !== undefined;

  return (
    <Box sx={{ height: '100%', width: '100%', overflow: 'auto', position: 'relative' }}>
      {/* Close Button - Fixed on right edge */}
      <IconButton
        onClick={onClose}
        sx={{
          position: 'absolute',
          right: 16,
          top: 16,
          zIndex: 1100,
          bgcolor: 'background.paper',
          boxShadow: 2,
          '&:hover': {
            bgcolor: 'background.elevated',
          }
        }}
      >
        <ChevronLeftIcon />
      </IconButton>

      {/* Sticky Header */}
      <Box sx={{ 
        position: 'sticky', 
        top: 0, 
        zIndex: 10, 
        display: 'flex', 
        justifyContent: 'left', 
        alignItems: 'center', 
        p: 3, 
        gap:2,
        bgcolor: 'background.default', 
        borderBottom: 1, 
        borderColor: 'divider' 
      }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <SettingsIcon size={70}/>
          <Typography variant="h5" sx={{ fontWeight: 'bold' }}>
            Hospital Settings
          </Typography>
        </Box>
        {hasDefaultSettings && (
          <Button
            variant="outlined"
            onClick={handleResetToDefault}
            size="small"
          >
            Reset to Default
          </Button>
        )}
      </Box>

      {/* Content */}
      <Box sx={{ flexGrow: 1, display: 'flex', flexDirection: 'column' }}>
        {/* Tab Navigation */}
        <Box sx={{ borderBottom: 1, borderColor: 'divider', px: 3 }}>
          <Tabs 
            value={activeTab} 
            onChange={handleTabChange}
            variant="scrollable"
            scrollButtons="auto"
            allowScrollButtonsMobile
          >
            <Tab label="Emergency Department" />
            <Tab label="EMS" />
            <Tab label="Inpatient Services" />
            <Tab label="Hospital Capabilities" />
          </Tabs>
        </Box>

        {/* Tab Panels */}
        <Box sx={{ flexGrow: 1, overflow: 'auto' }}>
          {/* Emergency Department Tab */}
          <TabPanel value={activeTab} index={0}>
            <Box sx={{ px: 3, pb: 3 }}>
              {/* <Box sx={{ mb: 3 }}>
                <Typography variant="h5" sx={{ fontWeight: 'bold', mb: 1 }}>
                  Emergency Department
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Configure ED physicians, patient arrivals, and treatment areas
                </Typography>
              </Box> */}
              <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', xl: 'repeat(2, 1fr)' }, gap: 5 }}>
                <Box sx={{ gridColumn: { xl: 'span 2' } }}>
                  <EDAreasSection 
                    edAreas={areas} 
                    setEdAreas={setAreas} 
                    fastTrack={fasttrack} 
                    setFastTrack={setFasttrack}
                    quickAction={quickAction}
                  />
                </Box>
                <Box sx={{ gridColumn: { xl: 'span 2' } }}>
                  <PhysiciansSection 
                    physicians={doctors} 
                    setPhysicians={setDoctors} 
                    availableAreas={areas}
                    fastTrack={fasttrack}
                    quickAction={quickAction}
                  />
                </Box>
                <Box>
                  <EdArrivalsSection 
                    arrivals={arrivals} 
                    setArrivals={setArrivals} 
                  />
                </Box>
              </Box>
            </Box>
          </TabPanel>

          {/* EMS Tab */}
          <TabPanel value={activeTab} index={1}>
            <Box sx={{ px: 3, pb: 3 }}>
              {/* <Box sx={{ mb: 3 }}>
                <Typography variant="h5" sx={{ fontWeight: 'bold', mb: 1 }}>
                  EMS
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Configure EMS arrivals and protocols
                </Typography>
              </Box> */}
              <Box>
                <EmsSection 
                  ems={ems} 
                  setEms={setEms} 
                />
              </Box>
            </Box>
          </TabPanel>

          {/* Inpatient Tab */}
          <TabPanel value={activeTab} index={2}>
            <Box sx={{ px: 3, pb: 3 }}>
              {/* <Box sx={{ mb: 3 }}>
                <Typography variant="h5" sx={{ fontWeight: 'bold', mb: 1 }}>
                  Inpatient Services
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Configure inpatient units and direct admissions
                </Typography>
              </Box> */}
              <Box>
                <InpatientSection 
                  inpatient={inpatient} 
                  setInpatient={setInpatient}
                  quickAction={quickAction}
                />
              </Box>
            </Box>
          </TabPanel>

          {/* Capabilities Tab */}
          <TabPanel value={activeTab} index={3}>
            <Box sx={{ px: 3, pb: 3 }}>
              {/* <Box sx={{ mb: 3 }}>
                <Typography variant="h5" sx={{ fontWeight: 'bold', mb: 1 }}>
                  Hospital Capabilities
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Configure hospital services and capabilities
                </Typography>
              </Box> */}
              <Box>
                <CapabilitiesSection 
                  capabilities={capabilities} 
                  setCapabilities={setCapabilities} 
                />
              </Box>
            </Box>
          </TabPanel>
        </Box>
      </Box>
    </Box>
  );
};

export default SettingsDrawerContent;