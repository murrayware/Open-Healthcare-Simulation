import React, { createContext, useContext, useState, useEffect } from 'react';
import { defaultPhysicians } from '../pages/settings/physicians/PhysiciansSection';
import { defaultArrivals } from '../pages/settings/ed/EdArrivalsSection';
import { defaultEms } from '../pages/settings/ems/EmsSection';
import { defaultCapabilities } from '../pages/settings/capabilities/CapabilitiesSection';
import apiFetch from '../api/client';

const HospitalSettingsContext = createContext();

export function HospitalSettingsProvider({ children }) {
  // ---------------- Settings State ----------------
  const [hospitalKey] = useState("hospital-a"); // default for now

  const [physicians, setPhysicians] = useState([]);
  const [arrivals, setArrivals] = useState(defaultArrivals);
  const [ems, setEms] = useState(defaultEms);
  const [inpatientUnits, setInpatientUnits] = useState([]);
  const [directAdmitsEnabled, setDirectAdmitsEnabled] = useState(true);
  const [directAdmitHours, setDirectAdmitHours] = useState(24);
  const [directAdmitHourlyLambda, setDirectAdmitHourlyLambda] = useState({});
  const [edAreas, setEdAreas] = useState([]);
  const [fastTrack, setFastTrack] = useState({ enabled: false });
  const [capabilities, setCapabilities] = useState(defaultCapabilities);

  // ---------------- Persistence ----------------
  useEffect(() => {
    const saved = localStorage.getItem(`settings-${hospitalKey}`);
    if (saved) {
      const parsed = JSON.parse(saved);
      setPhysicians(parsed.physicians || []);
      setArrivals(parsed.arrivals || defaultArrivals);
      setEms(parsed.ems || defaultEms);
      setCapabilities(parsed.capabilities || defaultCapabilities);
      setEdAreas(parsed.edAreas || []);
      setFastTrack(parsed.fastTrack || { enabled: false });
      setInpatientUnits(parsed.inpatientUnits || []);
    }
  }, [hospitalKey]);

  useEffect(() => {
    // Only save to localStorage if we have any data to save
    if (physicians.length > 0 || arrivals.length > 0 || ems.length > 0 || 
        inpatientUnits.length > 0 || edAreas.length > 0 || Object.keys(capabilities).length > 0) {
      localStorage.setItem(
        `settings-${hospitalKey}`,
        JSON.stringify({
          physicians,
          arrivals,
          ems,
          inpatientUnits,
          edAreas,
          fastTrack,
          capabilities,
        })
      );
    }
  }, [physicians, arrivals, ems, inpatientUnits, edAreas, fastTrack, capabilities, hospitalKey]);

  // ---------------- Business Logic ----------------
  const inpatientConfig = {
    units: inpatientUnits.reduce((acc, u) => {
      acc[u.service] = {
        name: u.service,
        beds: u.beds,
      };
      return acc;
    }, {}),
    direct_admits_enabled: directAdmitsEnabled,
    direct_admit_hours: directAdmitHours,
    direct_admit_hourly_lambda: directAdmitHourlyLambda,
  };

  const transformEdAreas = (areas) =>
    areas.reduce((acc, area) => {
      acc[area.name] = {
        ...area,
        nurse_model: {
          ...area.nurse_model,
          ...(area.nurse_model.model === "ratio"
            ? { ratio: area.nurse_model.ratio }
            : { team_nurses: area.nurse_model.team_nurses }),
        },
      };
      return acc;
    }, {});

  const buildSettingsPayload = () => ({
    hospital_id: hospitalKey.replace("hospital-", "").toUpperCase(),
    run_id: "test-123",
    seed: 99,
    run: { duration_minutes: 1440 },
    doctors: physicians,
    arrivals: arrivals,
    ems: ems,
    inpatient: inpatientConfig,
    areas: transformEdAreas(edAreas),
    capabilities: capabilities,
    fasttrack: fastTrack,
  });

  const handlePrintSettings = () => {
    const settings = buildSettingsPayload();
    console.log("🔹 Current Settings:", settings);
    alert("Settings printed to console!");
  };

  const handleSendSettings = async (runType = "adjusted", compareId = null) => {
    const settingsPayload = buildSettingsPayload();
    // include run_type for server
    settingsPayload.run_type = runType;
    // include compare_id for adjusted runs
    if (compareId) {
      settingsPayload.compare_id = compareId;
    }
    try {
      const data = await apiFetch('/simulate', {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(settingsPayload),
      });

      console.log("✅ Simulation response:", data);
      return data;
    } catch (err) {
      console.error("❌ Error sending settings:", err);
      alert("Failed to send settings. Check console for details.");
      return null;
    }
  };

  // Apply defaults from a backend "preloadedHospital" object into the frontend settings state
  const applyHospitalDefaults = (raw) => {
    if (!raw) return;
    let h = raw;
    try {
      if (typeof raw === "string") h = JSON.parse(raw);
    } catch (e) {
      console.warn("applyHospitalDefaults: failed to parse raw hospital payload", e);
      h = raw;
    }

    // doctors -> physicians list
    if (h.doctors || h.physicians) {
      setPhysicians(h.doctors ?? h.physicians ?? []);
    }

    // arrivals
    if (h.arrivals) {
      setArrivals(h.arrivals);
    }

    // ems
    if (h.ems) {
      setEms(h.ems);
    }

    // capabilities
    if (h.capabilities) {
      setCapabilities(h.capabilities);
    }

    // fasttrack (should be an object)
    if (h.fasttrack) {
      setFastTrack(h.fasttrack);
    }

    // ed areas: backend may store as dict { "A": {...}, "B": {...} } or as array
    if (h.areas) {
      if (Array.isArray(h.areas)) {
        setEdAreas(h.areas);
      } else {
        const areasArr = Object.entries(h.areas).map(([name, cfg]) => ({
          name,
          beds: cfg?.beds ?? cfg?.bed ?? 0,
          nurse_model: {
            model: cfg?.nurse_model?.model ?? (cfg?.nurse_model?.ratio ? "ratio" : "team"),
            ratio: Math.ceil(cfg?.nurse_model?.ratio ?? cfg?.nurse_model?.ratio ?? 2),
            team_nurses: cfg?.nurse_model?.team_nurses ?? cfg?.nurse_model?.team_nurses ?? 2,
            lab_support: !!(cfg?.nurse_model?.lab_support ?? cfg?.lab_support),
          },
        }));
        setEdAreas(areasArr);
      }
    }

    // inpatient: convert units dict to frontend inpatientUnits array + direct admit settings
    if (h.inpatient) {
      const units = h.inpatient.units ?? h.inpatient.unit_specs ?? h.inpatient;
      if (units && typeof units === "object" && !Array.isArray(units)) {
        const iu = Object.entries(units).map(([service, spec]) => ({
          service,
          beds: spec?.beds ?? spec?.bed_base ?? spec?.beds_per_unit ?? 0,
        }));
        setInpatientUnits(iu);
      } else if (Array.isArray(h.inpatient)) {
        // if backend already provided array-of-units
        setInpatientUnits(h.inpatient);
      }

      setDirectAdmitsEnabled(Boolean(h.inpatient.direct_admits_enabled ?? h.inpatient.direct_admits ?? true));
      setDirectAdmitHours(Number(h.inpatient.direct_admit_hours ?? h.inpatient.direct_admit_hour ?? 24));
      setDirectAdmitHourlyLambda(h.inpatient.direct_admit_hourly_lambda ?? h.inpatient.direct_admit_hourly_lambda ?? {});
    }

    // persist to localStorage happens automatically via existing effect
  };

  // ---------------- Context Value ----------------
  const contextValue = {
    // State
    hospitalKey,
    physicians, setPhysicians,
    arrivals, setArrivals,
    ems, setEms,
    inpatientUnits, setInpatientUnits,
    directAdmitsEnabled, setDirectAdmitsEnabled,
    directAdmitHours, setDirectAdmitHours,
    directAdmitHourlyLambda, setDirectAdmitHourlyLambda,
    edAreas, setEdAreas,
    fastTrack, setFastTrack,
    capabilities, setCapabilities,

    // Business logic
    buildSettingsPayload,
    handlePrintSettings,
    handleSendSettings,
    applyHospitalDefaults,
    
    // Computed values
    inpatientConfig,
    transformEdAreas,
  };

  return (
    <HospitalSettingsContext.Provider value={contextValue}>
      {children}
    </HospitalSettingsContext.Provider>
  );
}

export const useHospitalSettings = () => {
  const context = useContext(HospitalSettingsContext);
  if (!context) {
    throw new Error('useHospitalSettings must be used within HospitalSettingsProvider');
  }
  return context;
};

export default HospitalSettingsContext;