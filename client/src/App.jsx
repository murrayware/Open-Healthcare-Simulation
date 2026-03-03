// App.jsx
import React, { useState } from "react";
import {
  BrowserRouter as Router,
  Routes,
  Route,
  Navigate,
  Outlet,
} from "react-router-dom";

import Sidebar from "./components/Sidebar";
import ProtectedRoute from "./components/ProtectedRoute";
import SimulationPage from "./pages/SimulationPage";
import FacilityMapPage from "./pages/FacilityMapPage";
import HomePage from "./pages/HomePage";
import SettingsPage from "./pages/settings/SettingsPage";

import { AuthProvider } from "./context/AuthContext";
import { HospitalSettingsProvider } from "./context/HospitalSettingsContext";
import { SimulationWorkspaceProvider } from "./context/SimulationWorkspaceContext";
import LoginPage from "./pages/auth/LoginPage";
import SignupPage from "./pages/auth/SignupPage";

function App() {
  const [sidebarOpen, setSidebarOpen] = useState(true);

  return (
    <AuthProvider>
      <SimulationWorkspaceProvider>
        <HospitalSettingsProvider>
          <Router>
          <Routes>
            {/* Public routes (no sidebar) */}
            <Route path="/login" element={<LoginPage />} />
            <Route path="/signup" element={<SignupPage />} />

            {/* App shell routes (with sidebar) - Protected */}
            <Route
              path="/"
              element={
                <ProtectedRoute>
                  <AppLayout 
                    sidebarOpen={sidebarOpen}
                    setSidebarOpen={setSidebarOpen}
                  />
                </ProtectedRoute>
              }
            >
              {/* Default redirect */}
              <Route index element={<Navigate to="home" replace />} />
              
              {/* Main pages */}
              <Route path="home" element={<HomePage />} />
              <Route path="simulation/:id" element={<SimulationPage />} />
              <Route path="facility-map" element={<FacilityMapPage />} />
              
              {/* Settings with nested routes */}
              <Route path="settings/*" element={<SettingsPage />} />
            </Route>

            {/* Catch-all */}
            <Route path="*" element={<Navigate to="/home" replace />} />
          </Routes>
        </Router>
      </HospitalSettingsProvider>
    </SimulationWorkspaceProvider>
    </AuthProvider>
  );
}

/**
 * Layout component that renders sidebar + main content
 * Uses Material UI Drawer with responsive behavior:
 * - Mobile: Temporary drawer (overlay)
 * - Desktop: Persistent drawer (adjusts content width)
 */
function AppLayout({ sidebarOpen, setSidebarOpen }) {
  return (
    <div className="flex h-screen w-screen bg-bg text-text-primary">
      <Sidebar
        sidebarOpen={sidebarOpen}
        setSidebarOpen={setSidebarOpen}
      />
      <div className="flex-1 overflow-auto">
        <Outlet />
      </div>
    </div>
  );
}

export default App;
