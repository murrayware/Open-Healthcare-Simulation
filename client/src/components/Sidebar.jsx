import React, { useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { useSimulationWorkspace } from "../context/SimulationWorkspaceContext";
import { useAuth } from "../context/AuthContext";
import {
  Drawer,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Collapse,
  IconButton,
  Divider,
  Typography,
  Box,
  useTheme,
  useMediaQuery,
  Avatar,
  Menu,
  MenuItem,
  Button,
} from "@mui/material";
import { useAppTheme } from "../theme/useTheme";
import DashboardIcon from "@mui/icons-material/Dashboard";
import MapIcon from "@mui/icons-material/Map";
import SettingsIcon from "@mui/icons-material/Settings";
import ChevronLeftIcon from "@mui/icons-material/ChevronLeft";
import ChevronRightIcon from "@mui/icons-material/ChevronRight";
import CloseIcon from "@mui/icons-material/Close";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import ExpandLessIcon from "@mui/icons-material/ExpandLess";
import HomeIcon from "@mui/icons-material/Home";
import ScienceIcon from "@mui/icons-material/Science";
import DeleteIcon from "@mui/icons-material/Delete";

const menuItems = [
  { 
    key: "home", 
    label: "Home", 
    icon: <HomeIcon />, 
    path: "/home" 
  },
  { 
    key: "facility-map", 
    label: "Facility Map", 
    icon: <MapIcon />, 
    path: "/facility-map" 
  },
];

const DRAWER_WIDTH = 280;
const COLLAPSED_WIDTH = 72;

const Sidebar = ({ sidebarOpen, setSidebarOpen }) => {
  const location = useLocation();
  const navigate = useNavigate();
  const theme = useTheme();
  const appTheme = useAppTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
  const { simulations, activeSimulationId, closeSimulation } = useSimulationWorkspace();
  const { user, loading, logout } = useAuth();
  const [simulationsOpen, setSimulationsOpen] = useState(true);
  const [anchorEl, setAnchorEl] = useState(null);

  // Generate a deterministic color from a string (name/email)
  const stringToColor = (str = "") => {
    let hash = 0;
    for (let i = 0; i < str.length; i++) {
      hash = str.charCodeAt(i) + ((hash << 5) - hash);
    }
    let color = "#";
    for (let i = 0; i < 3; i++) {
      const value = (hash >> (i * 8)) & 0xff;
      color += (`00${value.toString(16)}`).slice(-2);
    }
    return color;
  };

  const getInitial = (s = "") => (s ? s.trim()[0].toUpperCase() : "U");

  const isActive = (path) => {
    return location.pathname === path || 
           (path !== '/' && location.pathname.startsWith(path));
  };

  const handleNavigation = (path) => {
    navigate(path);
    if (isMobile) {
      setSidebarOpen(false);
    }
  };

  const handleSimulationNavigation = (simulationId) => {
    navigate(`/simulation/${simulationId}`);
    if (isMobile) {
      setSidebarOpen(false);
    }
  };

  const handleCloseSimulation = (e, simulationId) => {
    e.stopPropagation();
    closeSimulation(simulationId);
  };

  const handleSimulationsToggle = () => {
    setSimulationsOpen(prev => !prev);
  };

  const toggleDrawer = () => {
    setSidebarOpen(!sidebarOpen);
  };

  // Auth menu handlers
  const handleLogin = () => navigate("/login");
  const handleSignup = () => navigate("/signup");
  const openMenu = (e) => setAnchorEl(e.currentTarget);
  const closeMenu = () => setAnchorEl(null);
  const handleLogout = () => {
    closeMenu();
    logout();
    navigate("/login");
  };

  const drawerContent = (
    <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      {/* Header */}
      <Box sx={{ 
        p: 2, 
        display: 'flex', 
        alignItems: 'center', 
        justifyContent: sidebarOpen ? 'space-between' : 'center',
        minHeight: 64
      }}>
        {sidebarOpen && (
          <Typography variant="h6" sx={{ fontWeight: 'bold', color: appTheme.colors.primary.dark }}>
            [logo]
          </Typography>
        )}
        <IconButton 
          onClick={toggleDrawer}
          sx={{ 
            color: appTheme.colors.primary.dark,
            '&:hover': { backgroundColor: appTheme.colors.background.surface, color: appTheme.colors.secondary.light }
          }}
        >
          {sidebarOpen ? <ChevronLeftIcon /> : <ChevronRightIcon />}
        </IconButton>
      </Box>

  <Divider sx={{ borderColor: appTheme.colors.border.primary }} />

      {/* Main Navigation */}
      <List sx={{ flexGrow: 1, pt: 1 }}>
        {menuItems.map((item) => (
          <ListItem key={item.key} disablePadding sx={{ display: 'block' }}>
              <ListItemButton
              onClick={() => handleNavigation(item.path)}
              selected={isActive(item.path)}
            >
              <ListItemIcon>
                {item.icon}
              </ListItemIcon>
              <ListItemText 
                primary={item.label} 
                sx={{ 
                  opacity: sidebarOpen ? 1 : 0,
                }} 
              />
            </ListItemButton>
          </ListItem>
        ))}

        {/* Simulations Section */}
        {simulations.length > 0 && (
          <>
            <Divider sx={{ mt: 2, mb: 1, borderColor: appTheme.colors.border.primary }} />
            
            <ListItem disablePadding sx={{ display: 'block' }}>
              <ListItemButton
                onClick={handleSimulationsToggle}
              >
                <ListItemIcon>
                  <ScienceIcon />
                </ListItemIcon>
                {sidebarOpen && (
                  <>
                    <ListItemText 
                      primary="Simulations" 
                      primaryTypographyProps={{
                        fontSize: '0.875rem',
                        fontWeight: 'medium',
                        textTransform: 'uppercase',
                        letterSpacing: '0.1em',
                      }}
                    />
                    <IconButton size="small">
                      {simulationsOpen ? <ExpandLessIcon /> : <ExpandMoreIcon />}
                    </IconButton>
                  </>
                )}
              </ListItemButton>
            </ListItem>

            <Collapse in={simulationsOpen && sidebarOpen} timeout="auto" unmountOnExit>
              <List component="div" disablePadding>
                {simulations.map((simulation) => (
                  <ListItem key={simulation.id} disablePadding sx={{ display: 'block' }}>
                    <ListItemButton
                      onClick={() => handleSimulationNavigation(simulation.id)}
                      selected={location.pathname === `/simulation/${simulation.id}`}
                      className="simulation-item"
                    >
                      <ListItemIcon>
                        <ScienceIcon fontSize="small" />
                      </ListItemIcon>
                      <ListItemText 
                        primary={simulation.name}
                        primaryTypographyProps={{
                          fontSize: '0.875rem',
                          noWrap: true,
                        }}
                      />
                      <IconButton
                        size="small"
                        onClick={(e) => handleCloseSimulation(e, simulation.id)}
                        sx={{
                          opacity: 0,
                          color: '#9ca3af',
                          '.MuiListItemButton-root:hover &': {
                            opacity: 1,
                          },
                          '&:hover': {
                            color: '#ef4444',
                          },
                        }}
                      >
                        <CloseIcon fontSize="small" />
                      </IconButton>
                    </ListItemButton>
                  </ListItem>
                ))}
              </List>
            </Collapse>
          </>
        )}
      </List>

      {/* User Authentication Section */}
      <Box sx={{ mt: 'auto', p: 2 }}>
        <Divider sx={{ mb: 2, borderColor: appTheme.colors.border.primary }} />
        
        {loading ? null : user ? (
          <>
            <Box 
              onClick={openMenu}
              sx={{ 
                display: 'flex', 
                alignItems: 'center', 
                justifyContent: 'left',
                cursor: 'pointer',
                p: 1,
                borderRadius: 1,
                '&:hover': { backgroundColor: appTheme.colors.background.surface }
              }}
            >
              <Avatar
                sx={{
                  width: 32,
                  height: 32,
                  bgcolor: stringToColor(user.name || user.email || "user"),
                  color: "#fff",
                  mr: sidebarOpen ? 1 : 0,
                }}
              >
                {getInitial(user.name || user.email)}
              </Avatar>
              {sidebarOpen && (
                <Typography 
                  variant="body2" 
                  sx={{ 
                    color: appTheme.colors.text.primary,
                    fontSize: '0.875rem',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    whiteSpace: 'nowrap'
                  }}
                >
                  {user.name || user.email}
                </Typography>
              )}
            </Box>

            <Menu
              anchorEl={anchorEl}
              open={Boolean(anchorEl)}
              onClose={closeMenu}
              anchorOrigin={{ vertical: "top", horizontal: "right" }}
              transformOrigin={{ vertical: "bottom", horizontal: "right" }}
            >
              <MenuItem onClick={() => { closeMenu(); }}>
                Profile
              </MenuItem>
              <MenuItem onClick={() => { closeMenu(); }}>
                Settings
              </MenuItem>
              <MenuItem onClick={() => { closeMenu(); }}>
                Help
              </MenuItem>
              <Divider />
              <MenuItem onClick={handleLogout}>Logout</MenuItem>
            </Menu>
          </>
        ) : (
          <Box sx={{ display: 'flex', flexDirection: sidebarOpen ? 'row' : 'column', gap: 1 }}>
            <Button
              variant="text"
              color="primary"
              onClick={handleLogin}
              size="small"
              sx={{ 
                minWidth: sidebarOpen ? 'auto' : 48,
                fontSize: sidebarOpen ? '0.75rem' : '0.6rem'
              }}
            >
              {sidebarOpen ? 'Login' : 'Log'}
            </Button>
            <Button
              variant="outlined"
              color="primary"
              onClick={handleSignup}
              size="small"
              sx={{ 
                minWidth: sidebarOpen ? 'auto' : 48,
                fontSize: sidebarOpen ? '0.75rem' : '0.6rem'
              }}
            >
              {sidebarOpen ? 'Sign Up' : 'Sign'}
            </Button>
          </Box>
        )}
      </Box>
    </Box>
  );

  return (
    <>
      {/* Mobile Drawer - Temporary (Overlay) */}
      <Drawer
        variant="temporary"
        open={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        ModalProps={{
          keepMounted: true, // Better open performance on mobile
        }}
        sx={{
          display: { xs: 'block', md: 'none' },
          '& .MuiDrawer-paper': {
            boxSizing: 'border-box',
            width: DRAWER_WIDTH,
            backgroundColor: appTheme.colors.background.sidebar,
            borderRight: `1px solid ${appTheme.colors.border.primary}`,
          },
        }}
      >
        {drawerContent}
      </Drawer>

      {/* Desktop Drawer - Persistent (Adjusts Content Width) */}
      <Drawer
        variant="persistent"
        anchor="left"
        open={true} // Always open on desktop, but width changes
        sx={{
          display: { xs: 'none', md: 'block' },
          width: sidebarOpen ? DRAWER_WIDTH : COLLAPSED_WIDTH,
          flexShrink: 0,
          '& .MuiDrawer-paper': {
            width: sidebarOpen ? DRAWER_WIDTH : COLLAPSED_WIDTH,
            boxSizing: 'border-box',
            backgroundColor: appTheme.colors.background.sidebar,
            borderRight: `1px solid ${appTheme.colors.border.primary}`,
            transition: theme.transitions.create('width', {
              easing: theme.transitions.easing.sharp,
              duration: theme.transitions.duration.enteringScreen,
            }),
            overflowX: 'hidden',
          },
        }}
      >
        {drawerContent}
      </Drawer>
    </>
  );
};

export default Sidebar;
