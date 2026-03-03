import React, { useState } from "react";
import MenuIcon from "@mui/icons-material/Menu";
import CloseIcon from "@mui/icons-material/Close";
import {
  Button,
  Menu,
  MenuItem,
  IconButton,
  Avatar,
  Divider,
} from "@mui/material";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

const Navbar = ({ sidebarOpen, setSidebarOpen }) => {
  const navigate = useNavigate();
  const { user, loading, logout } = useAuth();
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

  const handleLogin = () => navigate("/login");
  const handleSignup = () => navigate("/signup");

  const openMenu = (e) => setAnchorEl(e.currentTarget);
  const closeMenu = () => setAnchorEl(null);

  const handleLogout = () => {
    closeMenu();
    logout();
    navigate("/login");
  };

  return (
    <header className="flex items-center justify-between bg-bg px-6 py-4 shadow">
      {/* Mobile toggle */}
      <button
        onClick={() => setSidebarOpen(!sidebarOpen)}
        className="md:hidden block cursor-pointer"
      >
        {sidebarOpen ? (
          <CloseIcon className="h-6 w-6" />
        ) : (
          <MenuIcon className="h-6 w-6" />
        )}
      </button>

      {/* Title */}
      <h1 className="font-bold text-lg"></h1>

      {/* User Avatar / Auth buttons */}
      <div className="flex items-center space-x-4">
        {loading ? null : user ? (
          <>
            <IconButton
              onClick={openMenu}
              size="small"
              sx={{ ml: 1 }}
              aria-label="user menu"
            >
              <Avatar
                sx={{
                  width: 36,
                  height: 36,
                  bgcolor: stringToColor(user.name || user.email || "user"),
                  color: "#fff",
                }}
              >
                {getInitial(user.name || user.email)}
              </Avatar>
            </IconButton>

            <Menu
              anchorEl={anchorEl}
              open={Boolean(anchorEl)}
              onClose={closeMenu}
              anchorOrigin={{ vertical: "bottom", horizontal: "right" }}
              transformOrigin={{ vertical: "top", horizontal: "right" }}
            >
              <MenuItem onClick={() => { closeMenu(); /* placeholder */ }}>
                Profile
              </MenuItem>
              <MenuItem onClick={() => { closeMenu(); /* placeholder */ }}>
                Settings
              </MenuItem>
              <MenuItem onClick={() => { closeMenu(); /* placeholder */ }}>
                Help
              </MenuItem>
              <Divider />
              <MenuItem onClick={handleLogout}>Logout</MenuItem>
            </Menu>
          </>
        ) : (
          <div className="flex items-center space-x-2">
            <Button
              variant="text"
              color="primary"
              onClick={handleLogin}
            >
              Login
            </Button>
            <Button
              variant="outlined"
              color="primary"
              onClick={handleSignup}
            >
              Sign Up
            </Button>
          </div>
        )}
      </div>
    </header>
  );
};

export default Navbar;