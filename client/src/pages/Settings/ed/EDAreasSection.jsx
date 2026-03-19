import React, { useState, useEffect, useRef } from "react";
import SettingsCard from "../../../components/SettingsCard";
import SettingsModal from "../../../components/SettingsModal";
import {
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Checkbox,
  FormControlLabel,
  Button,
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

export const defaultEDArea = {
  name: "Main",
  beds: 10,
  nurse_model: {
    model: "ratio", // "ratio" or "team"
    ratio: 2,
    team_nurses: 0,
    lab_support: true,
  },
};

export const defaultFastTrack = {
  enabled: false,
  name: "FAST",
  assessment_spaces: 10,
  route_probability: 0.5,
  route_all: false,
  ctas_min: 3,
  no_trauma: false,
  min_gcs: 13,
  no_critical_ems: true,
};

const EDAreasSection = ({ edAreas, setEdAreas, fastTrack, setFastTrack, quickAction = null }) => {
  const [modalOpen, setModalOpen] = useState(false);
  const [fastTrackModalOpen, setFastTrackModalOpen] = useState(false);
  const [editingKey, setEditingKey] = useState(null);
  const [form, setForm] = useState(defaultEDArea);
  const [fastTrackForm, setFastTrackForm] = useState(
    fastTrack || defaultFastTrack
  );
  const lastHandledQuickActionToken = useRef(null);

  // Convert areas object to array for display
  const areasArray = Object.values(edAreas || {});
  const areaKeys = Object.keys(edAreas || {});

  // --- Regular ED areas ---
  const openAddModal = () => {
    setEditingKey(null);
    setForm(defaultEDArea);
    setModalOpen(true);
  };

  useEffect(() => {
    if (quickAction?.target !== "add-ed-area" || !quickAction?.token) return;
    if (lastHandledQuickActionToken.current === quickAction.token) return;

    lastHandledQuickActionToken.current = quickAction.token;
    setEditingKey(null);
    setForm(defaultEDArea);
    setModalOpen(true);
  }, [quickAction?.token, quickAction?.target]);

  const openEditModal = (areaKey) => {
    setEditingKey(areaKey);
    setForm(edAreas[areaKey]);
    setModalOpen(true);
  };

  const handleSave = () => {
    if (editingKey !== null) {
      // Update existing area
      setEdAreas({
        ...edAreas,
        [editingKey]: form
      });
    } else {
      // Add new area
      setEdAreas({
        ...edAreas,
        [form.name]: form
      });
    }
    setModalOpen(false);
    setEditingKey(null);
  };

  const handleRemove = (areaKey) => {
    const newAreas = { ...edAreas };
    delete newAreas[areaKey];
    setEdAreas(newAreas);
  };

  // --- Fast Track ---
  const openFastTrackModal = () => {
    setFastTrackForm(fastTrack.enabled ? fastTrack : defaultFastTrack);
    setFastTrackModalOpen(true);
  };

  const handleSaveFastTrack = () => {
    setFastTrack({ ...fastTrackForm, enabled: true });
    setFastTrackModalOpen(false);
  };

  const handleRemoveFastTrack = () => {
    setFastTrack({ ...defaultFastTrack, enabled: false });
  };

  return (
    <SettingsCard
      title="ED Areas"
      footer={
        <>
          <Button variant="outlined" color="success" onClick={openAddModal} startIcon={<AddIcon />} className='grow'>
            Add Area
          </Button>
          {!fastTrack.enabled && (
            <Button
              variant="outlined"
              color="primary"
              onClick={openFastTrackModal}
              startIcon={<AddIcon />}
              className='grow'
            >
              Add Fast Track
            </Button>
          )}
        </>
      }
    >
      {/* Areas and Fast Track Table */}
      {areasArray.length === 0 && !fastTrack.enabled ? (
        <div className="flex-1 flex items-center justify-center">
          <p className="text-text-secondary text-sm">No areas added yet.</p>
        </div>
      ) : (
        <TableContainer >
          <Table stickyHeader size='small' component={Paper}>
            <TableHead>
              <TableRow>
                <TableCell>Name</TableCell>
                <TableCell align="center">Type</TableCell>
                <TableCell align="center">Capacity</TableCell>
                <TableCell align="center">Details</TableCell>
                <TableCell align="center">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {/* Regular Areas */}
              {areasArray.map((area, index) => {
                const areaKey = areaKeys[index];
                return (
                  <TableRow
                    key={areaKey}
                    hover
                    sx={{ 
                      cursor: 'pointer',
                      '&:hover': {
                        backgroundColor: 'action.hover'
                      }
                    }}
                    onClick={() => openEditModal(areaKey)}
                  >
                    <TableCell component="th" scope="row">
                      <strong>Area {area.name}</strong>
                    </TableCell>
                    <TableCell align="center">ED Area</TableCell>
                    <TableCell align="center">{area.beds} beds</TableCell>
                    <TableCell align="center">
                      {area.nurse_model.model === 'ratio' 
                        ? `1:${area.nurse_model.ratio} ratio` 
                        : `${area.nurse_model.team_nurses} nurses`}
                      {area.nurse_model.lab_support && ', Lab Support'}
                    </TableCell>
                    <TableCell align="center">
                      <Tooltip title="Edit Area">
                        <IconButton
                          size="small"
                          onClick={(e) => {
                            e.stopPropagation();
                            openEditModal(areaKey);
                          }}
                          color="primary"
                        >
                          <EditIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                      <Tooltip title="Delete Area">
                        <IconButton
                          size="small"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleRemove(areaKey);
                          }}
                          color="error"
                        >
                          <DeleteIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                    </TableCell>
                  </TableRow>
                );
              })}
              
              {/* Fast Track Row */}
              {fastTrack.enabled && (
                <TableRow
                  hover
                  sx={{ 
                    cursor: 'pointer',
                    '&:hover': {
                      backgroundColor: 'action.hover'
                    }
                  }}
                  onClick={openFastTrackModal}
                >
                  <TableCell component="th" scope="row">
                    <strong>{fastTrack.name}</strong>
                  </TableCell>
                  <TableCell align="center">Fast Track</TableCell>
                  <TableCell align="center">{fastTrack.assessment_spaces} spaces</TableCell>
                  <TableCell align="center">
                    Prob: {fastTrack.route_probability}, CTAS ≥{fastTrack.ctas_min}
                    {fastTrack.no_trauma && ', No Trauma'}
                    {fastTrack.no_critical_ems && ', No Critical EMS'}
                  </TableCell>
                  <TableCell align="center">
                    <Tooltip title="Edit Fast Track">
                      <IconButton
                        size="small"
                        onClick={(e) => {
                          e.stopPropagation();
                          openFastTrackModal();
                        }}
                        color="primary"
                      >
                        <EditIcon fontSize="small" />
                      </IconButton>
                    </Tooltip>
                    <Tooltip title="Delete Fast Track">
                      <IconButton
                        size="small"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleRemoveFastTrack();
                        }}
                        color="error"
                      >
                        <DeleteIcon fontSize="small" />
                      </IconButton>
                    </Tooltip>
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </TableContainer>
      )}

      {/* Modal for ED Area */}
      {modalOpen && (
        <SettingsModal
          setModalOpen={setModalOpen}
          modalOpen={modalOpen}
          title={editingKey !== null ? "Edit ED Area" : "Add ED Area"}
          handleSave={handleSave}
        >
          <form className="flex flex-col gap-4 space-y-4">
            {/* Name */}
            <TextField
              fullWidth
              label="Area Name"
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
            />

            {/* Beds */}
            <TextField
              type="number"
              fullWidth
              label="Beds"
              value={form.beds}
              onChange={(e) =>
                setForm({ ...form, beds: parseInt(e.target.value, 10) || 0 })
              }
            />

            {/* Nurse Model */}
            <FormControl fullWidth>
              <InputLabel>Nurse Model</InputLabel>
              <Select
                value={form.nurse_model.model}
                onChange={(e) =>
                  setForm({
                    ...form,
                    nurse_model: {
                      ...form.nurse_model,
                      model: e.target.value,
                    },
                  })
                }
              >
                <MenuItem value="ratio">Ratio</MenuItem>
                <MenuItem value="team">Team</MenuItem>
              </Select>
            </FormControl>

            {form.nurse_model.model === "ratio" ? (
              <TextField
                type="number"
                fullWidth
                label="Ratio"
                value={form.nurse_model.ratio}
                onChange={(e) =>
                  setForm({
                    ...form,
                    nurse_model: {
                      ...form.nurse_model,
                      ratio: parseFloat(e.target.value) || 0,
                    },
                  })
                }
              />
            ) : (
              <TextField
                type="number"
                fullWidth
                label="Team Nurses"
                value={form.nurse_model.team_nurses}
                onChange={(e) =>
                  setForm({
                    ...form,
                    nurse_model: {
                      ...form.nurse_model,
                      team_nurses: parseInt(e.target.value, 10) || 0,
                    },
                  })
                }
              />
            )}

            {/* Lab Support */}
            <FormControlLabel
              control={
                <Checkbox
                  checked={form.nurse_model.lab_support}
                  onChange={(e) =>
                    setForm({
                      ...form,
                      nurse_model: {
                        ...form.nurse_model,
                        lab_support: e.target.checked,
                      },
                    })
                  }
                />
              }
              label="Lab Support"
            />
          </form>
        </SettingsModal>
      )}

      {/* Modal for Fast Track */}
      {fastTrackModalOpen && (
        <SettingsModal
          setModalOpen={setFastTrackModalOpen}
          modalOpen={fastTrackModalOpen}
          title="Fast Track Settings"
          handleSave={handleSaveFastTrack}
        >
          <form className="flex flex-col gap-4 space-y-4">
            <TextField
              fullWidth
              label="Name"
              value={fastTrackForm.name}
              onChange={(e) =>
                setFastTrackForm({ ...fastTrackForm, name: e.target.value })
              }
            />

            <TextField
              type="number"
              fullWidth
              label="Assessment Spaces"
              value={fastTrackForm.assessment_spaces}
              onChange={(e) =>
                setFastTrackForm({
                  ...fastTrackForm,
                  assessment_spaces: parseInt(e.target.value, 10) || 0,
                })
              }
            />

            <TextField
              type="number"
              fullWidth
              label="Route Probability"
              value={fastTrackForm.route_probability}
              inputProps={{ step: 0.01, min: 0, max: 1 }}
              onChange={(e) =>
                setFastTrackForm({
                  ...fastTrackForm,
                  route_probability: parseFloat(e.target.value) || 0,
                })
              }
            />

            <FormControlLabel
              control={
                <Checkbox
                  checked={fastTrackForm.route_all}
                  onChange={(e) =>
                    setFastTrackForm({
                      ...fastTrackForm,
                      route_all: e.target.checked,
                    })
                  }
                />
              }
              label="Route All Patients"
            />

            <TextField
              type="number"
              fullWidth
              label="CTAS Min"
              value={fastTrackForm.ctas_min}
              onChange={(e) =>
                setFastTrackForm({
                  ...fastTrackForm,
                  ctas_min: parseInt(e.target.value, 10) || 0,
                })
              }
            />

            <FormControlLabel
              control={
                <Checkbox
                  checked={fastTrackForm.no_trauma}
                  onChange={(e) =>
                    setFastTrackForm({
                      ...fastTrackForm,
                      no_trauma: e.target.checked,
                    })
                  }
                />
              }
              label="Exclude Trauma"
            />

            <TextField
              type="number"
              fullWidth
              label="Min GCS"
              value={fastTrackForm.min_gcs}
              onChange={(e) =>
                setFastTrackForm({
                  ...fastTrackForm,
                  min_gcs: parseInt(e.target.value, 10) || 0,
                })
              }
            />

            <FormControlLabel
              control={
                <Checkbox
                  checked={fastTrackForm.no_critical_ems}
                  onChange={(e) =>
                    setFastTrackForm({
                      ...fastTrackForm,
                      no_critical_ems: e.target.checked,
                    })
                  }
                />
              }
              label="Exclude Critical EMS"
            />
          </form>
        </SettingsModal>
      )}
    </SettingsCard>
  );
};

export default EDAreasSection;
