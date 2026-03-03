import { useAuth } from "../context/AuthContext";
import apiFetch from "../api/client";

/**
 * Custom hook that wraps apiFetch with automatic auth error handling
 * Automatically logs out user if token expires
 */
export const useApiFetch = () => {
  const { handleAuthError } = useAuth();

  const apiCall = async (path, options = {}) => {
    try {
      return await apiFetch(path, options);
    } catch (error) {
      return handleAuthError(error);
    }
  };

  return apiCall;
};

export default useApiFetch;