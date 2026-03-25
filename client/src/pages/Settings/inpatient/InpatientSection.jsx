import React, { useState, useCallback, useEffect, useRef } from "react";
import SettingsCard from "../../../components/SettingsCard";
import SettingsModal from "../../../components/SettingsModal";
import HourlyLambdaChart from "../../../components/HourlyLambdaChart";
import { generateSineWave } from "../../../utils";

import {
  TextField,
  Button,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  IconButton,
  Tooltip,
} from "@mui/material";
import EditIcon from "@mui/icons-material/Edit";
import DeleteIcon from "@mui/icons-material/Delete";
import AddIcon from "@mui/icons-material/Add";
import SettingsIcon from "@mui/icons-material/Settings";

export const defaultInpatientUnit = {
  service: "Medicine",
  beds: 20,
  los_draw: { uniform: [180, 720] },
};

const normalize = (s) => (s || "").trim();

const ensureLambda = (map, service, hours) => {
  if (map[service]) return map;
  return {
    ...map,
    [service]: generateSineWave(hours, 0, 5, 1, -Math.PI / 2),
  };
};

// Normalize los_draw to uniform format for editing (frontend only supports uniform)
const normalizeToUniform = (los_draw) => {
  if (!los_draw) return { uniform: [180, 720] };
  
  // If already uniform
  if (los_draw.uniform) return los_draw;
  
  // If lognormal or other format, convert to a reasonable uniform range
  if (los_draw.lognormal) {
    const mean = los_draw.lognormal.mean || 4.5; // hours
    const sigma = los_draw.lognormal.sigma || 0.35;
    // Approximate: use mean ± 2*sigma in hours, convert to minutes
    const lowHours = Math.max(0.5, mean - 2 * sigma);
    const highHours = mean + 2 * sigma;
    return { uniform: [Math.round(lowHours * 60), Math.round(highHours * 60)] };
  }
  
  // Fallback
  return { uniform: [180, 720] };
};

const InpatientSection = ({ inpatient, setInpatient, quickAction = null }) => {
  // Extract values from the inpatient object (backend format)
  const inpatientUnits = Object.values(inpatient?.units || {});
  const directAdmitsEnabled = inpatient?.direct_admits_enabled || false;
  const directAdmitHours = inpatient?.direct_admit_hours || 24;
  const directAdmitHourlyLambda = inpatient?.direct_admit_hourly_lambda || {};

  // Helper functions to update the inpatient object
  const setDirectAdmitsEnabled = (enabled) => {
    setInpatient({ ...inpatient, direct_admits_enabled: enabled });
  };

  const setDirectAdmitHours = (hours) => {
    setInpatient({ ...inpatient, direct_admit_hours: hours });
  };

  const setDirectAdmitHourlyLambda = (lambda) => {
    setInpatient({ ...inpatient, direct_admit_hourly_lambda: lambda });
  };

  const [unitModalOpen, setUnitModalOpen] = useState(false);
  const [directAdmitModalOpen, setDirectAdmitModalOpen] = useState(false);
  const [editingKey, setEditingKey] = useState(null);
  const [form, setForm] = useState(defaultInpatientUnit);
  const [originalService, setOriginalService] = useState(null);
  const [nameError, setNameError] = useState("");
  const lastHandledQuickActionToken = useRef(null);

  // Optimized onChange handler for hourly lambda chart
  const handleHourlyLambdaChange = useCallback((updated) => {
    const normalizedService = normalize(form.service);
    setInpatient(prev => ({
      ...prev,
      direct_admit_hourly_lambda: {
        ...prev.direct_admit_hourly_lambda,
        [normalizedService]: updated
      }
    }));
  }, [form.service, setInpatient]);

  // --- Unit Handling ---
  const openAddModal = () => {
    setEditingKey(null);
    setForm(defaultInpatientUnit);
    setOriginalService(null);
    setNameError("");
    setUnitModalOpen(true);
  };

  useEffect(() => {
    if (quickAction?.target !== "add-inpatient-unit" || !quickAction?.token) return;
    if (lastHandledQuickActionToken.current === quickAction.token) return;

    lastHandledQuickActionToken.current = quickAction.token;
    setEditingKey(null);
    setForm(defaultInpatientUnit);
    setOriginalService(null);
    setNameError("");
    setUnitModalOpen(true);
  }, [quickAction?.token, quickAction?.target]);

  const openEditModal = (unitKey) => {
    const unit = inpatientUnits.find(u => u.name === unitKey);
    setEditingKey(unitKey);
    setForm({ 
      service: unit.name, 
      beds: unit.beds,
      los_draw: normalizeToUniform(unit.los_draw)
    });
    setOriginalService(unit.name);
    setNameError("");
    setUnitModalOpen(true);
  };

  const handleSaveUnit = () => {
    const clean = normalize(form.service);
    if (!clean) return setNameError("Service name is required.");
    
    // Check for duplicates (excluding current item when editing)
    const existingUnits = inpatientUnits.filter(u => editingKey === null || u.name !== editingKey);
    if (existingUnits.some(u => normalize(u.name).toLowerCase() === clean.toLowerCase())) {
      return setNameError(`A unit named "${clean}" already exists.`);
    }

    const sanitized = { ...form, service: clean };

    // Update using backend format (object)
    const currentUnits = { ...inpatient.units };
    
    if (editingKey !== null) {
      // Remove old unit if service name changed
      if (originalService && originalService !== clean) {
        delete currentUnits[originalService];
      }
      // Add/update unit with new key
      currentUnits[clean] = { 
        name: clean, 
        beds: sanitized.beds,
        los_draw: sanitized.los_draw 
      };
      
      // Update inpatient object
      setInpatient({
        ...inpatient,
        units: currentUnits,
        direct_admit_hourly_lambda: {
          ...inpatient.direct_admit_hourly_lambda,
          ...(originalService && originalService !== clean ? 
            { [clean]: inpatient.direct_admit_hourly_lambda[originalService] || [] } : {}),
          ...(originalService && originalService !== clean ? 
            { [originalService]: undefined } : {})
        }
      });
    } else {
      // Add new unit
      currentUnits[clean] = { 
        name: clean, 
        beds: sanitized.beds,
        los_draw: sanitized.los_draw 
      };
      setInpatient({
        ...inpatient,
        units: currentUnits,
        direct_admit_hourly_lambda: {
          ...inpatient.direct_admit_hourly_lambda,
          [clean]: generateSineWave(directAdmitHours, 0, 5, 1, -Math.PI / 2)
        }
      });
    }

    setUnitModalOpen(false);
    setEditingKey(null);
    setOriginalService(null);
    setForm(defaultInpatientUnit);
    setNameError("");
  };

  const handleRemoveUnit = (unitKey) => {
    const currentUnits = { ...inpatient.units };
    delete currentUnits[unitKey];
    
    const currentLambda = { ...inpatient.direct_admit_hourly_lambda };
    delete currentLambda[unitKey];
    
    setInpatient({
      ...inpatient,
      units: currentUnits,
      direct_admit_hourly_lambda: currentLambda
    });
    
    setDirectAdmitHourlyLambda((prev) => {
      const updated = { ...prev };
      delete updated[unitKey];
      return updated;
    });
  };

  // --- Direct Admits Modal ---
  const handleHoursChange = (e) => {
    const newHours = Math.min(24, parseInt(e.target.value, 10) || 1);
    
    // Update lambda arrays for the new hours
    const currentLambda = inpatient.direct_admit_hourly_lambda || {};
    const updated = {};
    
    for (const [service, lambda] of Object.entries(currentLambda)) {
      let adjusted = [...lambda];
      if (newHours > adjusted.length) {
        adjusted = [
          ...adjusted,
          ...Array(newHours - adjusted.length).fill(adjusted.at(-1) || 1),
        ];
      } else {
        adjusted = adjusted.slice(0, newHours);
      }
      updated[service] = adjusted;
    }
    
    // Update inpatient object directly
    setInpatient({
      ...inpatient,
      direct_admit_hours: newHours,
      direct_admit_hourly_lambda: updated
    });
  };

  return (
    <SettingsCard
      title="Inpatient Units"
      footer={
        <>
        <Button variant="outlined" color="success" onClick={openAddModal} startIcon={<AddIcon />} className='grow'>
           Add Unit
        </Button>
          <Button
            onClick={() => setDirectAdmitModalOpen(true)}
            className='grow'
          >
             Direct Admit Settings
          </Button>

        </>
      }
    >
      {inpatientUnits.length === 0 ? (
        <div className="flex-1 flex items-center justify-center">
          <p className="text-text-secondary text-sm">
            No inpatient units added yet.
          </p>
        </div>
      ) : (
        <TableContainer component={Paper} sx={{ maxHeight: 400 }}>
          <Table stickyHeader>
            <TableHead>
              <TableRow>
                <TableCell>Service Name</TableCell>
                <TableCell align="center">Beds</TableCell>
                <TableCell align="center">LOS Min (mins)</TableCell>
                <TableCell align="center">LOS Max (mins)</TableCell>
                <TableCell align="center">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {inpatientUnits.map((unit) => (
                <TableRow
                  key={unit.name}
                  hover
                  sx={{ 
                    cursor: 'pointer',
                    '&:hover': {
                      backgroundColor: 'action.hover'
                    }
                  }}
                  onClick={() => openEditModal(unit.name)}
                >
                  <TableCell component="th" scope="row">
                    <strong>{unit.name}</strong>
                  </TableCell>
                  <TableCell align="center">{unit.beds}</TableCell>
                  <TableCell align="center">
                    {unit.los_draw?.uniform?.[0] || defaultInpatientUnit.los_draw.uniform[0]}
                  </TableCell>
                  <TableCell align="center">
                    {unit.los_draw?.uniform?.[1] || defaultInpatientUnit.los_draw.uniform[1]}
                  </TableCell>
                  <TableCell align="center">
                    <Tooltip title="Edit Unit">
                      <IconButton
                        size="small"
                        onClick={(e) => {
                          e.stopPropagation();
                          openEditModal(unit.name);
                        }}
                        color="primary"
                      >
                        <EditIcon fontSize="small" />
                      </IconButton>
                    </Tooltip>
                    <Tooltip title="Delete Unit">
                      <IconButton
                        size="small"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleRemoveUnit(unit.name);
                        }}
                        color="error"
                      >
                        <DeleteIcon fontSize="small" />
                      </IconButton>
                    </Tooltip>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}

      {/* Unit Modal */}
      {unitModalOpen && (
        <SettingsModal
          setModalOpen={setUnitModalOpen}
          modalOpen={unitModalOpen}
          title={editingKey !== null ? "Edit Unit" : "Add Unit"}
          handleSave={handleSaveUnit}
        >
          <form className="flex flex-col gap-4">
            <TextField
              fullWidth
              label="Service"
              value={form.service}
              error={!!nameError}
              helperText={nameError || ""}
              onChange={(e) => setForm({ ...form, service: e.target.value })}
            />

            <TextField
              type="number"
              fullWidth
              label="Beds"
              value={form.beds}
              onChange={(e) =>
                setForm({ ...form, beds: parseInt(e.target.value, 10) || 0 })
              }
            />

            <div className="flex gap-3">
              <TextField
                type="number"
                label="LOS Min (mins)"
                value={form.los_draw.uniform[0]}
                onChange={(e) =>
                  setForm({
                    ...form,
                    los_draw: {
                      uniform: [
                        parseInt(e.target.value, 10) || 0,
                        form.los_draw.uniform[1],
                      ],
                    },
                  })
                }
              />
              <TextField
                type="number"
                label="LOS Max (mins)"
                value={form.los_draw.uniform[1]}
                onChange={(e) =>
                  setForm({
                    ...form,
                    los_draw: {
                      uniform: [
                        form.los_draw.uniform[0],
                        parseInt(e.target.value, 10) || 0,
                      ],
                    },
                  })
                }
              />
            </div>

            {directAdmitsEnabled && (
              <div className="mt-4">
                <p className="text-sm text-text-secondary mb-2">
                  Hourly Lambda – {form.service}
                </p>
                <HourlyLambdaChart
                  values={
                    directAdmitHourlyLambda[normalize(form.service)] ??
                    generateSineWave(directAdmitHours, 0, 5, 1, -Math.PI / 2)
                  }
                  onChange={handleHourlyLambdaChange}
                />
              </div>
            )}
          </form>
        </SettingsModal>
      )}

      {/* Direct Admits Modal */}
      {directAdmitModalOpen && (
        <SettingsModal
          setModalOpen={setDirectAdmitModalOpen}
          modalOpen={directAdmitModalOpen}
          title="Direct Admit Settings"
          handleSave={() => setDirectAdmitModalOpen(false)}
        >
          <form className="flex flex-col gap-4">
            <FormControl fullWidth>
              <InputLabel>Enabled</InputLabel>
              <Select
                value={directAdmitsEnabled ? "true" : "false"}
                onChange={(e) =>
                  setDirectAdmitsEnabled(e.target.value === "true")
                }
              >
                <MenuItem value="true">Yes</MenuItem>
                <MenuItem value="false">No</MenuItem>
              </Select>
            </FormControl>

            <TextField
              type="number"
              fullWidth
              label="Direct Admit Hours"
              inputProps={{ min: 1, max: 24 }}
              value={directAdmitHours}
              disabled={!directAdmitsEnabled}
              onChange={handleHoursChange}
            />
          </form>
        </SettingsModal>
      )}
    </SettingsCard>
  );
};

export default InpatientSection;
