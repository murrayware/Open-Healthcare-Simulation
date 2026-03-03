import React, { createContext, useState, useEffect, useContext } from "react";
import apiFetch, { setAuthErrorHandler } from "../api/client";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  // Global error handler for token expiration
  const handleAuthError = (error) => {
    if (error?.status === 401) {
      // Token expired or invalid - clear auth state
      localStorage.removeItem("token");
      setUser(null);
      // Don't redirect here - let ProtectedRoute handle it
    }
    throw error; // Re-throw so calling components can handle it
  };

  // Register the auth error handler globally
  useEffect(() => {
    setAuthErrorHandler(handleAuthError);
  }, []);

  useEffect(() => {
    const init = async () => {
      const token = localStorage.getItem("token");
      if (!token) {
        setLoading(false);
        return;
      }
      try {
        // apiFetch will attach Authorization header automatically
        // Skip auth error handling since we're checking token validity
        const me = await apiFetch("/auth/me", { skipAuthErrorHandling: true });
        setUser(me);
      } catch (err) {
        // invalid/expired token -> remove and force login
        localStorage.removeItem("token");
        setUser(null);
      } finally {
        setLoading(false);
      }
    };
    init();
  }, []);

  async function login(email, password) {
    try {
      // call login endpoint; apiFetch returns parsed JSON or throws
      const res = await apiFetch("/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
        skipAuthErrorHandling: true, // Handle login errors manually
      });
      // ensure token saved so subsequent requests include Authorization
      if (res?.token) {
        localStorage.setItem("token", res.token);
      }
      setUser(res.user || null);
      return res;
    } catch (error) {
      return handleAuthError(error);
    }
  }

  async function signup(name, email, password) {
    try {
      const res = await apiFetch("/auth/signup", {
        method: "POST",
        body: JSON.stringify({ name, email, password }),
        skipAuthErrorHandling: true, // Handle signup errors manually
      });
      if (res?.token) {
        localStorage.setItem("token", res.token);
      }
      setUser(res.user || null);
      return res;
    } catch (error) {
      return handleAuthError(error);
    }
  }

  function logout() {
    localStorage.removeItem("token");
    setUser(null);
  }

  return (
    <AuthContext.Provider value={{ 
      user, 
      loading, 
      login, 
      signup, 
      logout, 
      handleAuthError 
    }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
