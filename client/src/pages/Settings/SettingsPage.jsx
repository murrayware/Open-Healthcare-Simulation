// SettingsPage.jsx
import React from "react";
import { Routes, Route, Navigate, useParams } from "react-router-dom";
import { Button } from "@mui/material";
import PhysiciansSection from "./physicians/PhysiciansSection";
import EdArrivalsSection from "./ed/EdArrivalsSection";
import EmsSection from "./ems/EmsSection";
import InpatientSection from "./inpatient/InpatientSection";
import EDAreasSection from "./ed/EDAreasSection";
import CapabilitiesSection from "./capabilities/CapabilitiesSection";
import { useHospitalSettings } from "../../context/HospitalSettingsContext";

const SettingsPage = () => {
  return (
    <Routes>
      {/* Default settings route */}
      <Route index element={<Navigate to="hospital-a" replace />} />
      
      {/* Hospital-specific settings */}
      <Route path="hospital-a" element={<HospitalSettings hospitalKey="A" />} />
      <Route path="hospital-b" element={<HospitalSettings hospitalKey="B" />} />
      <Route path="hospital-c" element={<HospitalSettings hospitalKey="C" />} />
    </Routes>
  );
};

const HospitalSettings = ({ hospitalKey }) => {
  const {
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
    handleSendSettings,
    isLoading
  } = useHospitalSettings();

  return (
    <main className="h-full w-full overflow-y-auto bg-bg">
      {/* Sticky Header */}
      <div className="sticky top-0 z-10 bg-bg border-b border-border p-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-text-primary">
              Hospital {hospitalKey} Settings
            </h1>
            <p className="text-text-secondary mt-1">
              Configure simulation parameters for Hospital {hospitalKey}
            </p>
          </div>
          <Button
            variant="contained"
            onClick={handleSendSettings}
            disabled={isLoading}
            className="bg-accent hover:bg-accent/90"
          >
            {isLoading ? "Saving..." : "Save Settings"}
          </Button>
        </div>
      </div>

      {/* Settings Content */}
      <div className="p-6 space-y-6">
        <PhysiciansSection
          physicians={physicians}
          setPhysicians={setPhysicians}
        />

        <EDAreasSection
          edAreas={edAreas}
          setEdAreas={setEdAreas}
          fastTrack={fastTrack}
          setFastTrack={setFastTrack}
        />

        <EdArrivalsSection
          arrivals={arrivals}
          setArrivals={setArrivals}
        />

        <EmsSection
          ems={ems}
          setEms={setEms}
        />

        <InpatientSection
          inpatientUnits={inpatientUnits}
          setInpatientUnits={setInpatientUnits}
          directAdmitsEnabled={directAdmitsEnabled}
          setDirectAdmitsEnabled={setDirectAdmitsEnabled}
          directAdmitHours={directAdmitHours}
          setDirectAdmitHours={setDirectAdmitHours}
          directAdmitHourlyLambda={directAdmitHourlyLambda}
          setDirectAdmitHourlyLambda={setDirectAdmitHourlyLambda}
        />

        <CapabilitiesSection
          capabilities={capabilities}
          setCapabilities={setCapabilities}
        />
      </div>
    </main>
  );
};export default SettingsPage;
