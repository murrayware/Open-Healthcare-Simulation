import React, { useCallback } from "react";
import HourlyLambdaChart from "../../../components/HourlyLambdaChart";
import SettingsCard from "../../../components/SettingsCard";
import {
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
} from "@mui/material";

// 🔹 Default EMS settings
export const defaultEms = {
  enabled: true,
  internal_generation: true,
  hours: 12,
  hourly_lambda: [1,1,2,2,2,3,3,3,3,3,3,2,2,2,2,1,1,1,1,1,1,1,1,1],
  ctas_mix: { 1: 0.03, 2: 0.12, 3: 0.45, 4: 0.35, 5: 0.05 },
  p_critical: 0.01,
  p_direct_to_bed: 0.3,
  download_capacity: 12,
  offload_nurses_per_hour: [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1],
  crew_hospital_time_draw: 25.0,
  "offload_service_time_draw": {
      "uniform": [
          8,
          18
      ]
  },
};

const EmsSection = ({ ems, setEms }) => {
  // Optimized onChange handlers to prevent lag
  const handleHourlyLambdaChange = useCallback((updated) => {
    setEms(prev => ({ ...prev, hourly_lambda: updated }));
  }, [setEms]);

  const handleOffloadNursesChange = useCallback((updated) => {
    setEms(prev => ({ ...prev, offload_nurses_per_hour: updated }));
  }, [setEms]);

  return (
    <SettingsCard title="EMS Arrivals">
      <form className="w-full space-y-6">
        {/* Enabled */}
        <FormControl fullWidth margin="normal">
          <InputLabel>Enabled</InputLabel>
          <Select
            value={ems.enabled ? "true" : "false"}
            label="Enabled"
            onChange={(e) =>
              setEms((prev) => ({
                ...prev,
                enabled: e.target.value === "true",
              }))
            }
          >
            <MenuItem value="true">Yes</MenuItem>
            <MenuItem value="false">No</MenuItem>
          </Select>
        </FormControl>

        {/* Hours */}
        <FormControl fullWidth margin="normal">
          <TextField
            type="number"
            fullWidth
            label="Hours"
            inputProps={{ min: 1, max: 24 }}
            value={ems.hours}
            disabled={!ems.enabled}
            onChange={(e) => {
              let newHours = Math.min(24, parseInt(e.target.value, 10) || 1);
              setEms((prev) => {
                // Adjust hourly_lambda - handle case where it might be undefined
                let updatedLambda = [...(prev.hourly_lambda || [])];
                if (newHours > updatedLambda.length) {
                  updatedLambda = [
                    ...updatedLambda,
                    ...Array(newHours - updatedLambda.length).fill(2),
                  ];
                } else if (newHours < updatedLambda.length) {
                  updatedLambda = updatedLambda.slice(0, newHours);
                }

                // Adjust offload_nurses_per_hour - handle case where it might be undefined
                let updatedNurses = [...(prev.offload_nurses_per_hour || [])];
                if (newHours > updatedNurses.length) {
                  updatedNurses = [
                    ...updatedNurses,
                    ...Array(newHours - updatedNurses.length).fill(1),
                  ];
                } else if (newHours < updatedNurses.length) {
                  updatedNurses = updatedNurses.slice(0, newHours);
                }

                return {
                  ...prev,
                  hours: newHours,
                  hourly_lambda: updatedLambda,
                  offload_nurses_per_hour: updatedNurses,
                };
              });
            }}
          />
        </FormControl>

        {/* Internal Generation */}
        <FormControl fullWidth margin="normal">
          <InputLabel>Internal Generation</InputLabel>
          <Select
            value={ems.internal_generation ? "true" : "false"}
            label="Internal Generation"
            disabled={!ems.enabled}
            onChange={(e) =>
              setEms((prev) => ({
                ...prev,
                internal_generation: e.target.value === "true",
              }))
            }
          >
            <MenuItem value="true">Yes</MenuItem>
            <MenuItem value="false">No</MenuItem>
          </Select>
        </FormControl>

        {/* Hourly Lambda */}
        <div>
          <p className="text-sm text-text-secondary mb-2">
            Hourly EMS Lambda
          </p>
          <HourlyLambdaChart
            values={ems.hourly_lambda?.length > 0 ? ems.hourly_lambda : defaultEms.hourly_lambda}
            onChange={handleHourlyLambdaChange}
            disabled={!ems.enabled}
          />
        </div>

        {/* CTAS Mix */}
        <div>
          <p className="text-sm text-text-secondary mb-2">CTAS Mix</p>
          <div className="grid grid-cols-5 gap-3">
            {Object.entries(ems.ctas_mix).map(([level, value]) => (
              <TextField
                key={level}
                type="number"
                label={`CTAS ${level}`}
                value={value}
                disabled={!ems.enabled}
                inputProps={{ step: 0.01, min: 0, max: 1 }}
                onChange={(e) =>
                  setEms((prev) => ({
                    ...prev,
                    ctas_mix: {
                      ...(prev.ctas_mix || {}),
                      [level]: parseFloat(e.target.value) || 0,
                    },
                  }))
                }
              />
            ))}
          </div>
        </div>

        {/* Probabilities */}
        <FormControl fullWidth margin="normal">
          <TextField
            type="number"
            fullWidth
            label="P(Critical)"
            value={ems.p_critical}
            disabled={!ems.enabled}
            inputProps={{ step: 0.01, min: 0, max: 1 }}
            onChange={(e) =>
              setEms({ ...ems, p_critical: parseFloat(e.target.value) || 0 })
            }
          />
        </FormControl>
        <FormControl fullWidth margin="normal">
          <TextField
            type="number"
            fullWidth
            label="P(Direct to Bed)"
            value={ems.p_direct_to_bed}
            disabled={!ems.enabled}
            inputProps={{ step: 0.01, min: 0, max: 1 }}
            onChange={(e) =>
              setEms({
                ...ems,
                p_direct_to_bed: parseFloat(e.target.value) || 0,
              })
            }
          />
        </FormControl>

        {/* Download Capacity */}
        <FormControl fullWidth margin="normal">
          <TextField
            type="number"
            fullWidth
            label="Download Capacity"
            value={ems.download_capacity}
            disabled={!ems.enabled}
            onChange={(e) =>
              setEms({
                ...ems,
                download_capacity: parseInt(e.target.value, 10) || 0,
              })
            }
          />
        </FormControl>

        {/* Offload Nurses Per Hour */}
        <div>
          <p className="text-sm text-text-secondary mb-2">
            Offload Nurses per Hour
          </p>
          <HourlyLambdaChart
            values={ems.offload_nurses_per_hour?.length > 0 ? ems.offload_nurses_per_hour : defaultEms.offload_nurses_per_hour}
            onChange={handleOffloadNursesChange}
            disabled={!ems.enabled}
          />
        </div>

        {/* Crew Hospital Time */}
        <FormControl fullWidth margin="normal">
          <TextField
            type="number"
            fullWidth
            label="Crew Hospital Time (minutes)"
            value={ems.crew_hospital_time_draw}
            disabled={!ems.enabled}
            onChange={(e) =>
              setEms({
                ...ems,
                crew_hospital_time_draw: parseFloat(e.target.value) || 0,
              })
            }
          />
        </FormControl>
      </form>
    </SettingsCard>
  );
};

export default EmsSection;
