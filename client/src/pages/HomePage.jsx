import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useSimulationWorkspace } from "../context/SimulationWorkspaceContext";
import {
  Paper,
  TableContainer,
  Table,
  TableHead,
  TableBody,
  TableRow,
  TableCell,
  TablePagination,
  CircularProgress,
  Typography,
  Box,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  TextField,
  Card,
  CardContent,
  CardActions,
  Chip,
} from "@mui/material";
import ScienceIcon from "@mui/icons-material/Science";
import AddIcon from "@mui/icons-material/Add";
import apiFetch from "../api/client";

export default function HomePage() {
  const navigate = useNavigate();
  const { simulations, createSimulation, updateSimulation } = useSimulationWorkspace();
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Create simulation modal state
  const [createOpen, setCreateOpen] = useState(false);
  const [simulationName, setSimulationName] = useState('');
  const [selectedTemplate, setSelectedTemplate] = useState('blank');
  
  // Hospital template state
  const [hospitals, setHospitals] = useState([]);
  const [loadingHospitals, setLoadingHospitals] = useState(false);
  const [selectedHospital, setSelectedHospital] = useState("");
  const [fetchingHospital, setFetchingHospital] = useState(false);

  // pagination
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(10);

  useEffect(() => {
    let mounted = true;
    const load = async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await apiFetch("/api/compares");
        if (!mounted) return;
        setProjects(data?.compares || []);
      } catch (err) {
        if (!mounted) return;
        setError(err?.message || "Failed to load projects");
      } finally {
        if (mounted) setLoading(false);
      }
    };
    load();
    return () => {
      mounted = false;
    };
  }, []);

  const loadHospitals = async () => {
    if (hospitals.length > 0) return; // already loaded
    setLoadingHospitals(true);
    try {
      console.log("Fetching hospitals from /api/hospitals...");
      const data = await apiFetch("/api/hospitals");
      console.log("Hospital data received:", data);
      setHospitals(data?.hospitals || []);
    } catch (err) {
      console.error("Failed to load hospitals", err);
      setHospitals([]);
    } finally {
      setLoadingHospitals(false);
    }
  };

  const openCreate = () => {
    setCreateOpen(true);
    setSimulationName('');
    setSelectedTemplate('blank');
    setSelectedHospital('');
  };

  // Load hospitals when template changes to 'hospital'
  useEffect(() => {
    if (selectedTemplate === 'hospital' && hospitals.length === 0) {
      loadHospitals();
    }
  }, [selectedTemplate]);

  const closeCreate = () => {
    setCreateOpen(false);
    setSimulationName('');
    setSelectedTemplate('blank');
    setSelectedHospital('');
  };

  const handleCreateSimulation = async () => {
    let hospitalData = null;
    
    // If hospital template selected, fetch the data
    if (selectedTemplate === 'hospital' && selectedHospital) {
      setFetchingHospital(true);
      try {
        const data = await apiFetch(`/api/hospitals/${encodeURIComponent(selectedHospital)}`);
        hospitalData = data?.hospital || null;
      } catch (err) {
        console.error("Failed to fetch hospital template:", err);
        alert("Failed to load hospital template. Creating blank simulation instead.");
      } finally {
        setFetchingHospital(false);
      }
    }

    // Create the simulation
    const simulationId = createSimulation(
      simulationName || `Simulation ${simulations.length + 1}`,
      hospitalData
    );

    // Navigate to the new simulation (with small delay to ensure state update)
    // Add auto-run parameter if this is a hospital template
    const shouldAutoRun = selectedTemplate === 'hospital' && hospitalData;
    const navigationPath = shouldAutoRun 
      ? `/simulation/${simulationId}?autoRun=true`
      : `/simulation/${simulationId}`;
    
    setTimeout(() => {
      navigate(navigationPath);
      closeCreate();
    }, 0);
  };

  const handleOpenExistingSimulation = (simulationId) => {
    navigate(`/simulation/${simulationId}`);
  };

  const loadProject = async (projectId) => {
    setLoading(true);
    try {
      const data = await apiFetch(`/api/compares/${projectId}`);
      
      // Create a new simulation workspace with the project data
      const simulationName = `Project ${projectId}`;
      const simulationId = createSimulation(simulationName);
      
      // Extract settings from the first output's configs
      const settings = data.output_1?.configs || {};
      
      // Update the new simulation with the project data and settings (backend format)
      updateSimulation(simulationId, {
        defaultMetrics: data.output_1?.results || null,
        adjustedMetrics: data.output_2?.results || null,
        compareId: projectId,
        settings: {
          doctors: settings.doctors || [],
          arrivals: settings.arrivals || { 
            hours: 24, 
            walkin_hourly_lambda: [], 
            admit_prob: 0.38, 
            fasttrack_route_probability: 0.53,
            lwbs_threshold_dist: { type: "uniform", low: 60, high: 240 }
          },
          ems: settings.ems || { enabled: false },
          areas: settings.areas || {},
          capabilities: settings.capabilities || {},
          fasttrack: settings.fasttrack || { enabled: false },
          inpatient: settings.inpatient || { 
            units: {}, 
            direct_admits_enabled: true, 
            direct_admit_hours: 24, 
            direct_admit_hourly_lambda: {} 
          }
        }
      });
      
      // Navigate to the new simulation
      setTimeout(() => {
        navigate(`/simulation/${simulationId}`);
      }, 0);
    } catch (err) {
      console.error("Failed to load project:", err);
      alert("Failed to load project. See console for details.");
    } finally {
      setLoading(false);
    }
  };

  const handleChangePage = (_, newPage) => {
    setPage(newPage);
  };

  const handleChangeRowsPerPage = (event) => {
    setRowsPerPage(parseInt(event.target.value, 10));
    setPage(0);
  };

  const paged = projects.slice(page * rowsPerPage, page * rowsPerPage + rowsPerPage);

  return (
    <Box p={3}>
      <Box display="flex" alignItems="center" justifyContent="space-between" mb={3}>
        <Typography variant="h4">Hospital Simulation Dashboard</Typography>
      </Box>

      {/* Active Simulations Section */}
      <Box mb={4}>
        <Typography variant="h6" mb={2}>Active Simulations</Typography>
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
          {/* Create New Simulation Card */}
          <div>
            <Card 
              sx={{ 
                cursor: 'pointer',
                border: '2px dashed',
                borderColor: 'primary.main',
                backgroundColor: 'transparent',
                '&:hover': { 
                  boxShadow: 6,
                  borderColor: 'primary.light',
                  backgroundColor: 'action.hover'
                }
              }}
              onClick={() => setCreateOpen(true)}
            >
              <CardContent sx={{ 
                display: 'flex', 
                flexDirection: 'column', 
                alignItems: 'center', 
                justifyContent: 'center',
                minHeight: 160,
                textAlign: 'center'
              }}>
                <AddIcon 
                  color="primary" 
                  sx={{ 
                    fontSize: 48, 
                    mb: 2 
                  }} 
                />
                <Typography variant="h6" color="primary">
                  Create New Simulation
                </Typography>
                <Typography variant="body2" color="text.secondary" mt={1}>
                  Start a new simulation project
                </Typography>
              </CardContent>
            </Card>
          </div>

          {/* Existing Simulations */}
          {simulations.map((simulation) => (
            <div key={simulation.id}>
              <Card 
                sx={{ 
                  cursor: 'pointer',
                  '&:hover': { boxShadow: 6 }
                }}
                onClick={() => handleOpenExistingSimulation(simulation.id)}
              >
                <CardContent>
                  <Box display="flex" alignItems="center" mb={1}>
                    <ScienceIcon color="primary" sx={{ mr: 1 }} />
                    <Typography variant="h6" noWrap>{simulation.name}</Typography>
                  </Box>
                  <Typography variant="body2" color="text.secondary" mb={1}>
                    Created: {new Date(simulation.createdAt).toLocaleDateString()}
                  </Typography>
                  <Typography variant="body2" color="text.secondary" mb={1}>
                    Last accessed: {new Date(simulation.lastAccessed).toLocaleDateString()}
                  </Typography>
                  <Box display="flex" gap={1} flexWrap="wrap">
                    {simulation.defaultMetrics && (
                      <Chip label="Has Results" color="success" size="small" />
                    )}
                    {simulation.adjustedMetrics && (
                      <Chip label="Adjusted" color="info" size="small" />
                    )}
                    <Chip 
                      label={`Hospital ${simulation.hospitalKey.replace('hospital-', '').toUpperCase()}`}
                      variant="outlined" 
                      size="small" 
                    />
                  </Box>
                </CardContent>
              </Card>
            </div>
          ))}
        </div>
      </Box>

      {/* Project History Section */}
      <Box>
        <Typography variant="h6" mb={2}>Project History</Typography>

      {loading ? (
        <Box display="flex" alignItems="center" justifyContent="center" py={6}>
          <CircularProgress />
        </Box>
      ) : error ? (
        <Typography color="error">{error}</Typography>
      ) : projects.length === 0 ? (
        <Typography color="text.secondary">No projects yet.</Typography>
      ) : (
        <Box>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Click on a project to load it in the simulation page with its settings and results.
          </Typography>
        <Paper>
          <TableContainer>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Created</TableCell>
                  <TableCell>Project ID</TableCell>
                  <TableCell>Status</TableCell>
                </TableRow>
              </TableHead>

              <TableBody>
                {paged.map((c) => {
                  const created = c.created ?? "";
                  const hasAdjusted = c.output_2_id !== null;
                  const status = hasAdjusted ? "Complete" : "Baseline Only";
                  
                  return (
                    <TableRow
                      key={c.id}
                      hover
                      sx={{ cursor: "pointer" }}
                      onClick={() => loadProject(c.id)}
                    >
                      <TableCell style={{ whiteSpace: "nowrap" }}>{created}</TableCell>
                      <TableCell>{c.id}</TableCell>
                      <TableCell>
                        <span style={{ 
                          color: hasAdjusted ? '#4caf50' : '#ff9800',
                          fontSize: '0.875rem'
                        }}>
                          {status}
                        </span>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </TableContainer>

          <TablePagination
            component="div"
            count={projects.length}
            page={page}
            onPageChange={handleChangePage}
            rowsPerPage={rowsPerPage}
            onRowsPerPageChange={handleChangeRowsPerPage}
            rowsPerPageOptions={[5, 10, 25, 50]}
          />
        </Paper>
        </Box>
      )}
      </Box>

      {/* Create Simulation Dialog */}
      <Dialog open={createOpen} onClose={closeCreate} fullWidth maxWidth="sm">
        <DialogTitle>Create New Simulation</DialogTitle>
        <DialogContent dividers>
          <TextField
            fullWidth
            label="Simulation Name"
            value={simulationName}
            onChange={(e) => setSimulationName(e.target.value)}
            placeholder={`Simulation ${simulations.length + 1}`}
            margin="normal"
          />
          
          <FormControl fullWidth margin="normal">
            <InputLabel>Template</InputLabel>
            <Select
              value={selectedTemplate}
              onChange={(e) => setSelectedTemplate(e.target.value)}
              label="Template"
            >
              <MenuItem value="blank">Blank Simulation</MenuItem>
              <MenuItem value="hospital">Hospital Template</MenuItem>
            </Select>
          </FormControl>

          {selectedTemplate === 'hospital' && (
            <FormControl fullWidth margin="normal">
              <InputLabel>Hospital Template</InputLabel>
              <Select
                value={selectedHospital}
                onChange={(e) => setSelectedHospital(e.target.value)}
                disabled={loadingHospitals}
                label="Hospital Template"
              >
                {loadingHospitals ? (
                  <MenuItem value="">
                    <em>Loading...</em>
                  </MenuItem>
                ) : hospitals.length === 0 ? (
                  <MenuItem value="">
                    <em>No hospitals available</em>
                  </MenuItem>
                ) : (
                  hospitals.map((h) => (
                    <MenuItem key={h} value={h}>
                      {h}
                    </MenuItem>
                  ))
                )}
              </Select>
            </FormControl>
          )}
        </DialogContent>

        <DialogActions>
          <Button onClick={closeCreate} disabled={fetchingHospital}>
            Cancel
          </Button>
          <Button
            onClick={handleCreateSimulation}
            variant="contained"
            color="primary"
            disabled={
              fetchingHospital || 
              (selectedTemplate === 'hospital' && !selectedHospital)
            }
          >
            {fetchingHospital ? <CircularProgress size={18} /> : "Create Simulation"}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}