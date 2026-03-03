import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { TextField, Button } from '@mui/material';

export default function SignupPage() {
    const [name, setName] = useState('');
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');
    const { signup } = useAuth();
    const navigate = useNavigate();

    const onSubmit = async (e) => {
        e.preventDefault();
        setError('');
        try {
            await signup(name, email, password);
            navigate('/simulation', { replace: true });
        } catch (err) {
            setError(err?.data?.error || err?.message || 'Signup failed');
        }
    };

    return (
        <div className="min-h-screen flex items-center justify-center bg-bg text-text-primary">
            <div className="w-120 max-w-full p-8 rounded-2xl shadow-md ">
                <h2 className="text-2xl font-semibold">Create an account</h2>
                <p className="text-sm mt-4">
                    Already have an account?{" "}
                    <Link to="/login" className="text-text-link hover:underline">
                        Log in
                    </Link>
                </p>


                <form onSubmit={onSubmit} className="flex flex-col gap-6 mt-6">
                    <TextField
                        fullWidth
                        label="Full Name"
                        type="text"
                        value={name}
                        onChange={(e) => setName(e.target.value)}
                    />

                    <TextField
                        fullWidth
                        label="Email Address"
                        type="email"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                    />

                    <TextField
                        fullWidth
                        label="Password (min 8 chars)"
                        type="password"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                    />

                    <Button
                        type="submit"
                        variant="contained"
                        color="primary"
                        className="mt-2 "
                    >
                        Create Account
                    </Button>

                {error && (
                    <div className="mb-4 text-sm text-red-500 bg-red-50 px-2 rounded leading-10">
                        {error}
                    </div>
                )}
                </form>
            </div>
        </div>
    );
}
