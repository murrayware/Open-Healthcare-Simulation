// PhysiciansSection.jsx
import React, { useState, useCallback } from "react";
import SettingsCard from "../../../components/SettingsCard";
import SettingsModal from "../../../components/SettingsModal";
import HourlyLambdaChart from "../../../components/HourlyLambdaChart";
import ChartCard from "../../../components/ChartCard";
import { generateStepDecay } from "../../../utils";
import Chart from "react-apexcharts";
import { getChartConfig } from "../../../theme";

import AddIcon from "@mui/icons-material/Add";
import {
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
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
import dayjs from "dayjs";
import { TimePicker } from "@mui/x-date-pickers";

function generateSignups(shiftMinutes) {
  const hours = Math.ceil(shiftMinutes / 60);
  const defaultSignups = generateStepDecay(Math.ceil(shiftMinutes / 60), 3, 1, 3);
  return hours <= defaultSignups.length
    ? defaultSignups.slice(0, hours)
    : [...defaultSignups, ...Array(hours - defaultSignups.length).fill(1)];
}

export const defaultPhysicians = {
  name: "",
  specialty: "General",
  capacity: 10,
  area: "Main",
  start_minute: 480,
  shift_minutes: 600,
  max_active_panel: 8,
  hourly_max_signups: generateSignups(600),
};

const adjustArrayLength = (arr, hours, fill = 1) => {
  const newLength = Math.ceil(hours);
  if (newLength > arr.length) {
    return [...arr, ...Array(newLength - arr.length).fill(fill)];
  }
  return arr.slice(0, newLength);
};

const PhysiciansSection = ({ physicians, setPhysicians, availableAreas = {}, fastTrack = {} }) => {
  const [modalOpen, setModalOpen] = useState(false);
  const [editingIndex, setEditingIndex] = useState(null);
  const [form, setForm] = useState(defaultPhysicians);

  // Get list of available area names
  const areaNames = Object.keys(availableAreas);
  
  // Add FastTrack to available areas if enabled
  const allAvailableAreas = [...areaNames];
  if (fastTrack.enabled && fastTrack.name) {
    allAvailableAreas.push(fastTrack.name);
  }
  
  const hasAreas = allAvailableAreas.length > 0;

  // Optimized onChange handler for hourly max signups to prevent lag
  const handleHourlyMaxSignupsChange = useCallback((updated) => {
    setForm(prev => ({ ...prev, hourly_max_signups: updated }));
  }, []);

  const openAddModal = () => {
    setEditingIndex(null);
    setForm(defaultPhysicians);
    setModalOpen(true);
  };

  const openEditModal = (index) => {
    setEditingIndex(index);
    setForm(physicians[index]);
    setModalOpen(true);
  };

  const handleSave = () => {
    if (editingIndex !== null) {
      const updated = [...physicians];
      updated[editingIndex] = form;
      setPhysicians(updated);
    } else {
      setPhysicians([...physicians, form]);
    }
    setForm(defaultPhysicians);
    setModalOpen(false);
    setEditingIndex(null);
  };

  const handleRemove = (index) => {
    setPhysicians(physicians.filter((_, i) => i !== index));
  };

  const computeEndTime = () => {
    const start = dayjs().startOf("day").add(form.start_minute, "minute");
    return start.add(form.shift_minutes, "minute").format("h:mm A");
  };

  const formatStartTime = (startMinute) => {
    return dayjs().startOf("day").add(startMinute, "minute").format("h:mm A");
  };

  const formatShiftLength = (shiftMinutes) => {
    const hours = shiftMinutes / 60;
    return hours % 1 === 0 ? `${hours}h` : `${hours.toFixed(1)}h`;
  };

  // Generate Gantt chart data
  const generateGanttData = () => {
    if (physicians.length === 0) return [];

    return physicians.map((physician, index) => {
      const startTime = new Date();
      startTime.setHours(0, 0, 0, 0);
      startTime.setMinutes(physician.start_minute);
      
      const endTime = new Date(startTime);
      endTime.setMinutes(endTime.getMinutes() + physician.shift_minutes);

      return {
        x: physician.name || `Physician ${index + 1}`,
        y: [startTime.getTime(), endTime.getTime()],
        fillColor: getPhysicianColor(index),
        physician: physician
      };
    });
  };

  // Generate colors for physicians
  const getPhysicianColor = (index) => {
    const colors = [
      '#008FFB', '#00E396', '#FEB019', '#FF4560', '#775DD0',
      '#546E7A', '#26a69a', '#D10CE8', '#FF9800', '#607D8B'
    ];
    return colors[index % colors.length];
  };

  // Gantt chart configuration using centralized theme
  const ganttChartOptions = getChartConfig('gantt', {
    chart: {
      type: 'rangeBar',
      height: Math.max(300, physicians.length * 40 + 100),
    },
    plotOptions: {
      bar: {
        horizontal: true,
        barHeight: '70%',
        rangeBarGroupRows: false
      }
    },
    dataLabels: {
      enabled: true,
      formatter: function(val, opts) {
        const physician = opts.w.config.series[0].data[opts.dataPointIndex].physician;
        const start = formatStartTime(physician.start_minute);
        const length = formatShiftLength(physician.shift_minutes);
        return `${start} (${length})`;
      },
      style: {
        colors: ['#fff'],
        fontWeight: 'bold'
      }
    },
    xaxis: {
      type: 'datetime',
      min: new Date().setHours(0, 0, 0, 0),
      max: new Date().setHours(23, 59, 59, 999),
      labels: {
        datetimeUTC: false,
        format: 'HH:mm',
      },
      title: {
        text: 'Time of Day',
      }
    },
    tooltip: {
      custom: function({series, seriesIndex, dataPointIndex, w}) {
        const physician = w.config.series[0].data[dataPointIndex].physician;
        return `
          <div style="padding: 10px; background: #1e1e1e; border-radius: 4px;">
            <strong>${physician.name}</strong><br/>
            <span>Specialty: ${physician.specialty || 'General'}</span><br/>
            <span>Area: ${physician.area}</span><br/>
            <span>Start: ${formatStartTime(physician.start_minute)}</span><br/>
            <span>Length: ${formatShiftLength(physician.shift_minutes)}</span><br/>
            <span>Max Panel: ${physician.max_active_panel}</span>
          </div>
        `;
      }
    }
  });

  const ganttChartSeries = [{
    name: 'Physician Shifts',
    data: generateGanttData()
  }];

  return (
    <SettingsCard
      title="Physicians"
      footer={
        <Button variant="outlined" color="primary" onClick={openAddModal} className='grow' startIcon={<AddIcon />}>
           Add Physician
        </Button>
      }
    >
      {physicians.length === 0 ? (
        <div className="flex-1 flex items-center justify-center">
          <p className="text-text-secondary text-sm">No physicians added yet.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {/* Gantt Chart */}

            <Chart
              options={ganttChartOptions}
              series={ganttChartSeries}
              type="rangeBar"
              height={Math.max(150, physicians.length * 20 + 100)}
            />


          {/* Physicians Table */}
          <TableContainer component={Paper} sx={{ maxHeight: 400 }}>
            <Table stickyHeader size='small'>
              <TableHead>
                <TableRow>
                  <TableCell>Name</TableCell>
                  <TableCell>Specialty</TableCell>
                  <TableCell>Area</TableCell>
                  <TableCell>Start Time</TableCell>
                  <TableCell>Shift Length</TableCell>
                  <TableCell>Max Panel</TableCell>
                  <TableCell align="center">Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {physicians.map((physician, index) => (
                  <TableRow
                    key={index}
                    hover
                    sx={{ 
                      cursor: 'pointer',
                      '&:hover': {
                        backgroundColor: 'action.hover'
                      }
                    }}
                    onClick={() => openEditModal(index)}
                  >
                    <TableCell component="th" scope="row">
                      <strong>{physician.name}</strong>
                    </TableCell>
                    <TableCell>{physician.specialty || 'General'}</TableCell>
                    <TableCell>{physician.area}</TableCell>
                    <TableCell>{formatStartTime(physician.start_minute)}</TableCell>
                    <TableCell>{formatShiftLength(physician.shift_minutes)}</TableCell>
                    <TableCell>{physician.max_active_panel}</TableCell>
                    <TableCell align="center">
                      <Tooltip title="Edit Physician">
                        <IconButton
                          size="small"
                          onClick={(e) => {
                            e.stopPropagation();
                            openEditModal(index);
                          }}
                          color="primary"
                        >
                          <EditIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                      <Tooltip title="Delete Physician">
                        <IconButton
                          size="small"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleRemove(index);
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
        </div>
      )}

      {/* Modal */}
      {modalOpen && (
        <SettingsModal
          setModalOpen={setModalOpen}
          modalOpen={modalOpen}
          handleSave={handleSave}
          title="Physician Settings"
        >
          <form className="flex flex-col gap-4">
            <TextField
              fullWidth
              label="Name"
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
            />

            <FormControl fullWidth>
              <InputLabel>Area</InputLabel>
              <Select
                value={form.area || (hasAreas ? allAvailableAreas[0] : "Main")}
                label="Area"
                onChange={(e) => setForm({ ...form, area: e.target.value })}
              >
                {hasAreas ? (
                  allAvailableAreas.map((areaName) => (
                    <MenuItem key={areaName} value={areaName}>
                      {areaName}
                      {areaName === fastTrack.name ? " (FastTrack)" : ""}
                    </MenuItem>
                  ))
                ) : (
                  <MenuItem value="Main">Main (Default)</MenuItem>
                )}
              </Select>
            </FormControl>

            <TimePicker
              label="Start Time"
              value={dayjs().startOf("day").add(form.start_minute, "minute")}
              onChange={(newValue) => {
                if (newValue) {
                  const minutes = newValue.hour() * 60 + newValue.minute();
                  setForm({ ...form, start_minute: minutes });
                }
              }}
            />

            <TextField
              type="number"
              fullWidth
              label="Shift Length (hours)"
              inputProps={{ min: 1, max: 24, step: 0.25 }}
              value={form.shift_minutes / 60}
              onChange={(e) => {
                let hours = parseFloat(e.target.value) || 0;
                if (hours > 24) hours = 24;
                const minutes = Math.round(hours * 60);

                setForm((prev) => ({
                  ...prev,
                  shift_minutes: minutes,
                  hourly_max_signups: adjustArrayLength(
                    prev.hourly_max_signups,
                    hours,
                    1
                  ),
                }));
              }}
              helperText={`Ends at ${computeEndTime()}`}
            />

            <TextField
              type="number"
              fullWidth
              label="Max Active Panel"
              value={form.max_active_panel || 8}
              onChange={(e) =>
                setForm({
                  ...form,
                  max_active_panel: parseInt(e.target.value, 10),
                })
              }
            />

            <div>
              <p className="text-sm text-text-secondary mb-2">
                Hourly Max Signups
              </p>
              <HourlyLambdaChart
                values={form.hourly_max_signups}
                onChange={handleHourlyMaxSignupsChange}
              />
            </div>
          </form>
        </SettingsModal>
      )}
    </SettingsCard>
  );
};

export default PhysiciansSection;
