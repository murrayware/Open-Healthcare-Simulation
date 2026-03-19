// src/api/client.js
const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000';

// Global auth handler - will be set by AuthContext
let globalAuthErrorHandler = null;

export const setAuthErrorHandler = (handler) => {
  globalAuthErrorHandler = handler;
};

async function apiFetch(path, options = {}) {
  const token = localStorage.getItem('token');
  const headers = {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...(options.headers || {}),
  };

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });

  // Handle 401 with automatic auth error handling (unless disabled)
  if (res.status === 401) {
    const text = await res.text();
    let data = null;
    try { data = text ? JSON.parse(text) : null; } catch {}
    const err = new Error(data?.error || 'Unauthorized');
    err.status = 401;
    err.data = data;
    
    // Auto-handle auth errors unless specifically disabled
    if (globalAuthErrorHandler && !options.skipAuthErrorHandling) {
      return globalAuthErrorHandler(err);
    }
    
    throw err;
  }

  const text = await res.text();
  const data = text ? JSON.parse(text) : null;

  if (!res.ok) {
    const msg = data?.error || data?.message || `Server error: ${res.status}`;
    const err = new Error(msg);
    err.status = res.status;
    err.data = data;
    throw err;
  }

  return data;
}

export default apiFetch;
