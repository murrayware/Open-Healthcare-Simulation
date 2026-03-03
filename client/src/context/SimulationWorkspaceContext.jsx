// SimulationWorkspace context for managing multiple simulations
import React, { createContext, useContext, useState, useEffect } from 'react';
import { v4 as uuidv4 } from 'uuid';
import { defaultArrivals } from '../pages/settings/ed/EdArrivalsSection';
import { defaultEms } from '../pages/settings/ems/EmsSection';

// Utility function to estimate localStorage usage
const getStorageInfo = () => {
  try {
    const totalSize = JSON.stringify(localStorage).length;
    const simulationSize = localStorage.getItem('simulation-workspaces')?.length || 0;
    return { totalSize, simulationSize };
  } catch {
    return { totalSize: 0, simulationSize: 0 };
  }
};

const SimulationWorkspaceContext = createContext();

export function SimulationWorkspaceProvider({ children }) {
  // Array of open simulations
  const [simulations, setSimulations] = useState([]);
  // Currently active simulation ID
  const [activeSimulationId, setActiveSimulationId] = useState(null);

  // Load simulations from localStorage on mount
  useEffect(() => {
    const saved = localStorage.getItem('simulation-workspaces');
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        setSimulations(parsed.simulations || []);
        setActiveSimulationId(parsed.activeSimulationId || null);
      } catch (err) {
        console.warn('Failed to load simulation workspaces:', err);
      }
    }
  }, []);

  // Save simulations to localStorage whenever they change
  useEffect(() => {
    try {
      // Create a lightweight version for storage (exclude large metrics data)
      const lightweightSimulations = simulations.map(sim => ({
        ...sim,
        // Keep metrics references but store them separately if needed
        defaultMetrics: sim.defaultMetrics ? 'stored' : null,
        adjustedMetrics: sim.adjustedMetrics ? 'stored' : null,
      }));

      const dataToStore = {
        simulations: lightweightSimulations,
        activeSimulationId
      };

      localStorage.setItem('simulation-workspaces', JSON.stringify(dataToStore));
    } catch (error) {
      console.warn('Failed to save simulations to localStorage:', error);
      
      // If quota exceeded, try to clear old data and save minimal version
      if (error.name === 'QuotaExceededError') {
        try {
          // Clear existing data
          localStorage.removeItem('simulation-workspaces');
          
          // Save only essential simulation info (no metrics)
          const minimalSimulations = simulations.map(sim => ({
            id: sim.id,
            name: sim.name,
            createdAt: sim.createdAt,
            lastAccessed: sim.lastAccessed,
            hospitalKey: sim.hospitalKey,
            compareId: sim.compareId,
            settings: sim.settings,
            // Exclude metrics entirely
            defaultMetrics: null,
            adjustedMetrics: null,
          }));

          localStorage.setItem('simulation-workspaces', JSON.stringify({
            simulations: minimalSimulations,
            activeSimulationId
          }));
          
          console.warn('Saved minimal simulation data due to storage quota limits');
        } catch (secondError) {
          console.error('Failed to save even minimal simulation data:', secondError);
        }
      }
    }
  }, [simulations, activeSimulationId]);

  // Create a new simulation workspace
  const createSimulation = (name, hospitalData = null) => {
    const id = uuidv4();
    const newSimulation = {
      id,
      name: name || `Simulation ${simulations.length + 1}`,
      createdAt: new Date().toISOString(),
      lastAccessed: new Date().toISOString(),
      
      // Simulation state
      defaultMetrics: null,
      adjustedMetrics: null,
      compareId: null,
      
      // Settings state (using backend format directly)
      hospitalKey: 'hospital-a', // default
      settings: {
        // Backend format structure
        doctors: [], // Instead of physicians
        arrivals: { // Combined arrivals configuration
          admit_prob: 0.38,
          fasttrack_route_probability: 0.53,
          hours: 24,
          lwbs_threshold_dist: { type: "uniform", low: 60, high: 240 },
          schema_version: 1,
          walkin_hourly_lambda: defaultArrivals.walkin_hourly_lambda || []
        },
        ems: {
          enabled: false,
          schema_version: 1,
          hours: defaultEms.hours,
          hourly_lambda: defaultEms.hourly_lambda,
          offload_nurses_per_hour: defaultEms.offload_nurses_per_hour,
          ctas_mix: defaultEms.ctas_mix
        },
        areas: {}, // Object with area names as keys
        capabilities: {
          schema_version: 1,
          has_CT: false,
          has_US: true,
          has_Xray: true
        },
        fasttrack: {
          enabled: false,
          schema_version: 1
        },
        inpatient: {
          units: {},
          direct_admits_enabled: true,
          direct_admit_hours: 24,
          direct_admit_hourly_lambda: {}
        },
        
        // Apply initial hospital data if provided (convert to backend format)
        ...(hospitalData && {
          doctors: hospitalData.doctors || [],
          arrivals: {
            ...( hospitalData.arrivals || {}),
            admit_prob: hospitalData.arrivals?.admit_prob || 0.38,
            fasttrack_route_probability: hospitalData.arrivals?.fasttrack_route_probability || 0.53,
            hours: hospitalData.arrivals?.hours || 24,
            lwbs_threshold_dist: hospitalData.arrivals?.lwbs_threshold_dist || { type: "uniform", low: 60, high: 240 },
            schema_version: 1,
            walkin_hourly_lambda: hospitalData.arrivals?.walkin_hourly_lambda || defaultArrivals.walkin_hourly_lambda || []
          },
          ems: hospitalData.ems || { 
            enabled: false, 
            schema_version: 1, 
            hours: defaultEms.hours, 
            hourly_lambda: defaultEms.hourly_lambda, 
            offload_nurses_per_hour: defaultEms.offload_nurses_per_hour, 
            ctas_mix: defaultEms.ctas_mix 
          },
          areas: hospitalData.areas || {},
          capabilities: hospitalData.capabilities || { schema_version: 1, has_CT: false, has_US: true, has_Xray: true },
          fasttrack: hospitalData.fasttrack || { enabled: false, schema_version: 1 },
          inpatient: hospitalData.inpatient || { units: {}, direct_admits_enabled: true, direct_admit_hours: 24, direct_admit_hourly_lambda: {} }
        })
      }
    };

    setSimulations(prev => [...prev, newSimulation]);
    setActiveSimulationId(id);
    
    return id;
  };

  // Get simulation by ID
  const getSimulation = (id) => {
    return simulations.find(sim => sim.id === id) || null;
  };

  // Get currently active simulation
  const getActiveSimulation = () => {
    return activeSimulationId ? getSimulation(activeSimulationId) : null;
  };

  // Update simulation data
  const updateSimulation = (id, updates) => {
    setSimulations(prev => prev.map(sim => 
      sim.id === id 
        ? { 
            ...sim, 
            ...updates, 
            lastAccessed: new Date().toISOString() 
          }
        : sim
    ));
  };

  // Switch to a different simulation
  const switchToSimulation = (id) => {
    const simulation = getSimulation(id);
    if (simulation) {
      setActiveSimulationId(id);
      updateSimulation(id, { lastAccessed: new Date().toISOString() });
      return simulation;
    }
    return null;
  };

  // Close/remove a simulation
  const closeSimulation = (id) => {
    setSimulations(prev => prev.filter(sim => sim.id !== id));
    
    // If closing active simulation, switch to another one
    if (activeSimulationId === id) {
      const remaining = simulations.filter(sim => sim.id !== id);
      if (remaining.length > 0) {
        setActiveSimulationId(remaining[0].id);
      } else {
        setActiveSimulationId(null);
      }
    }
  };

  // Rename a simulation
  const renameSimulation = (id, newName) => {
    updateSimulation(id, { name: newName });
  };

  // Clone/duplicate a simulation
  const cloneSimulation = (id) => {
    const original = getSimulation(id);
    if (!original) return null;

    const clonedId = uuidv4();
    const cloned = {
      ...original,
      id: clonedId,
      name: `${original.name} (Copy)`,
      createdAt: new Date().toISOString(),
      lastAccessed: new Date().toISOString(),
      // Reset metrics for the clone
      defaultMetrics: null,
      adjustedMetrics: null,
      compareId: null,
    };

    setSimulations(prev => [...prev, cloned]);
    setActiveSimulationId(clonedId);
    
    return clonedId;
  };

  // Clean up old simulations to prevent storage quota issues
  const cleanupOldSimulations = () => {
    const thirtyDaysAgo = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000);
    const recentSimulations = simulations.filter(sim => 
      new Date(sim.lastAccessed) > thirtyDaysAgo || sim.id === activeSimulationId
    );
    
    if (recentSimulations.length < simulations.length) {
      setSimulations(recentSimulations);
      console.log(`Cleaned up ${simulations.length - recentSimulations.length} old simulations`);
    }
  };

  const value = {
    // State
    simulations,
    activeSimulationId,
    
    // Getters
    getSimulation,
    getActiveSimulation,
    
    // Actions
    createSimulation,
    updateSimulation,
    switchToSimulation,
    closeSimulation,
    renameSimulation,
    cloneSimulation,
    cleanupOldSimulations,
    
    // Utilities
    getStorageInfo,
  };

  return (
    <SimulationWorkspaceContext.Provider value={value}>
      {children}
    </SimulationWorkspaceContext.Provider>
  );
}

export function useSimulationWorkspace() {
  const context = useContext(SimulationWorkspaceContext);
  if (!context) {
    throw new Error('useSimulationWorkspace must be used within SimulationWorkspaceProvider');
  }
  return context;
}

export default SimulationWorkspaceContext;