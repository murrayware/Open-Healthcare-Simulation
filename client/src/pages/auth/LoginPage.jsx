import React, { useState } from "react";
import { useLocation, useNavigate, Link } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";

import { TextField, Button } from "@mui/material";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const from = location.state?.from?.pathname || "/home";

  const onSubmit = async (e) => {
    e.preventDefault();
    setError("");
    try {
      await login(email, password);
      navigate(from, { replace: true });
    } catch (err) {
      // apiFetch / AuthContext errors use a `{ status, data }` or Error shape — handle common cases
      setError(err?.data?.error || err?.message || "Login failed");
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-bg text-text-primary">
      <div className="w-120 max-w-full p-8 rounded-2xl">
        <h2 className="text-2xl font-semibold">Sign into your account</h2>
        <p className="text-sm mt-4">
          Don’t have an account?{" "}
          <Link to="/signup" className="text-text-link hover:underline">
            Sign up
          </Link>
        </p>



        <form onSubmit={onSubmit} className="flex flex-col gap-6 mt-6">

                      <TextField
                        fullWidth
                        label="Email Address"
                        type="email"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        
                      />

                                <TextField
                        fullWidth
                        label="Email Address"
                        type="password"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        
                      />

        <Button
        type="submit"
        variant="contained"
        color="primary"
        className="mt-2"
        >Log In</Button>
        </form>
        {error && (
          <div className="mb-4 text-sm text-red-500 bg-red-50 px-2 rounded leading-14">
            {error}
          </div>
        )}

      </div>
    </div>
  );
}
