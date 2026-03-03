import React, { useState, useCallback } from "react";
import SettingsCard from "../../../components/SettingsCard";
import SettingsModal from "../../../components/SettingsModal";
import HourlyLambdaChart from "../../../components/HourlyLambdaChart";
import { TextField, Button } from "@mui/material";
import { generateSineWave } from "../../../utils";

// 🔹 Default ED Arrivals settings
export const defaultArrivals = {
  hours: 24,
  walkin_hourly_lambda: generateSineWave(24, 1, 10, 1, -Math.PI / 2),
  lwbs_threshold_dist: { type: "uniform", low: 60, high: 240 },
};

const EdArrivalsSection = ({ arrivals, setArrivals }) => {
  const [lambdaModalOpen, setLambdaModalOpen] = useState(false);

  // Optimized onChange handler for hourly lambda to prevent lag
  const handleHourlyLambdaChange = useCallback((updated) => {
    setArrivals(prev => ({ ...prev, walkin_hourly_lambda: updated }));
  }, [setArrivals]);

  const handleThresholdChange = (field, value) => {
    const num = parseInt(value, 10) || 0;
    setArrivals({
      ...arrivals,
      lwbs_threshold_dist: {
        ...(arrivals.lwbs_threshold_dist || { type: "uniform", low: 0, high: 0 }),
        type: "uniform",
        [field]: num,
      },
    });
  };

  return (
    <SettingsCard
      title="ED Arrivals"
      footer={
        <Button
          color="primary"
          className="w-full"
          onClick={() => setLambdaModalOpen(true)}
        >
          Edit Hourly Arrivals
        </Button>
      }
    >
      <form className="w-full space-y-6 overflow-y-auto pt-2">
        {/* Hours */}
        <TextField
          type="number"
          fullWidth
          label="Hours"
          inputProps={{ min: 1, max: 24 }}
          value={arrivals.hours}
          onChange={(e) => {
            let newHours = Math.min(24, parseInt(e.target.value, 10) || 1);

            setArrivals((prev) => {
              let updated = [...prev.walkin_hourly_lambda];

              if (newHours > updated.length) {
                updated = [
                  ...updated,
                  ...Array(newHours - updated.length).fill(6),
                ];
              } else if (newHours < updated.length) {
                updated = updated.slice(0, newHours);
              }

              return {
                ...prev,
                hours: newHours,
                walkin_hourly_lambda: updated,
              };
            });
          }}
        />

        {/* LWBS Threshold */}
        <div>
          <p className="text-sm text-text-secondary mb-2">
            LWBS Threshold (minutes)
          </p>
          <div className="flex gap-3">
            <TextField
              type="number"
              fullWidth
              label="Min"
              value={arrivals.lwbs_threshold_dist?.low ?? ""}
              onChange={(e) => handleThresholdChange("low", e.target.value)}
            />
            <TextField
              type="number"
              fullWidth
              label="Max"
              value={arrivals.lwbs_threshold_dist?.high ?? ""}
              onChange={(e) => handleThresholdChange("high", e.target.value)}
            />
          </div>
        </div>
      </form>

      {/* Modal with draggable chart */}
      {lambdaModalOpen && (
        <SettingsModal
          setModalOpen={setLambdaModalOpen}
          handleSave={() => setLambdaModalOpen(false)}
          modalOpen={lambdaModalOpen}
          title="Edit Hourly Lambda"
        >
          <HourlyLambdaChart
            values={arrivals.walkin_hourly_lambda}
            onChange={handleHourlyLambdaChange}
          />
        </SettingsModal>
      )}
    </SettingsCard>
  );
};

export default EdArrivalsSection;
