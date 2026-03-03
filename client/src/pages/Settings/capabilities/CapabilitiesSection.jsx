// src/pages/settings/capabilities/CapabilitiesSection.jsx
import React from "react";
import SettingsCard from "../../../components/SettingsCard";
import { TextField, FormControlLabel, Checkbox } from "@mui/material";

export const defaultCapabilities = {
  has_Xray: true,
  has_CT: false,
  has_US: true,
  transfer_only_admit: false,
  external_di_roundtrip: true,
  external_di_total_time_draw: { uniform: [100, 180] },
  admit_transfer_total_time_draw: { uniform: [90, 180] },
};

const CapabilitiesSection = ({ capabilities, setCapabilities }) => {

  const handleCheckboxChange = (field) => (event) => {
    setCapabilities({
      ...capabilities,
      [field]: event.target.checked,
    });
  };

  const handleUniformChange = (field, index) => (event) => {
    const value = parseInt(event.target.value, 10) || 0;
    // Ensure the field exists and has a uniform array before updating
    const currentUniform = capabilities[field]?.uniform || defaultCapabilities[field]?.uniform || [0, 0];
    const updated = [...currentUniform];
    updated[index] = value;
    setCapabilities({
      ...capabilities,
      [field]: { uniform: updated },
    });
  };

  return (
    <SettingsCard title="Capabilities">
      <form className="flex flex-col gap-4 w-full">
        {/* Imaging Capabilities */}
        <FormControlLabel
          control={
            <Checkbox
              checked={capabilities.has_Xray}
              onChange={handleCheckboxChange("has_Xray")}
            />
          }
          label="X-ray"
        />
        <FormControlLabel
          control={
            <Checkbox
              checked={capabilities.has_CT}
              onChange={handleCheckboxChange("has_CT")}
            />
          }
          label="CT"
        />
        <FormControlLabel
          control={
            <Checkbox
              checked={capabilities.has_US}
              onChange={handleCheckboxChange("has_US")}
            />
          }
          label="Ultrasound"
        />

        {/* Other Capabilities */}
        <FormControlLabel
          control={
            <Checkbox
              checked={capabilities.transfer_only_admit}
              onChange={handleCheckboxChange("transfer_only_admit")}
            />
          }
          label="Transfer Only Admit"
        />
        <FormControlLabel
          control={
            <Checkbox
              checked={capabilities.external_di_roundtrip}
              onChange={handleCheckboxChange("external_di_roundtrip")}
            />
          }
          label="External DI Roundtrip"
        />

        {/* Time Settings */}
        <div>
          <p className="text-sm text-text-secondary mb-2">
            External DI Total Time (minutes)
          </p>
          <div className="flex gap-3">
            <TextField
              type="number"
              label="Min"
              value={capabilities.external_di_total_time_draw?.uniform?.[0] ?? defaultCapabilities.external_di_total_time_draw.uniform[0]}
              onChange={handleUniformChange(
                "external_di_total_time_draw",
                0
              )}
            />
            <TextField
              type="number"
              label="Max"
              value={capabilities.external_di_total_time_draw?.uniform?.[1] ?? defaultCapabilities.external_di_total_time_draw.uniform[1]}
              onChange={handleUniformChange(
                "external_di_total_time_draw",
                1
              )}
            />
          </div>
        </div>

        <div>
          <p className="text-sm text-text-secondary mb-2">
            Admit Transfer Total Time (minutes)
          </p>
          <div className="flex gap-3">
            <TextField
              type="number"
              label="Min"
              value={capabilities.admit_transfer_total_time_draw?.uniform?.[0] ?? defaultCapabilities.admit_transfer_total_time_draw.uniform[0]}
              onChange={handleUniformChange(
                "admit_transfer_total_time_draw",
                0
              )}
            />
            <TextField
              type="number"
              label="Max"
              value={capabilities.admit_transfer_total_time_draw?.uniform?.[1] ?? defaultCapabilities.admit_transfer_total_time_draw.uniform[1]}
              onChange={handleUniformChange(
                "admit_transfer_total_time_draw",
                1
              )}
            />
          </div>
        </div>
      </form>
    </SettingsCard>
  );
};

export default CapabilitiesSection;
