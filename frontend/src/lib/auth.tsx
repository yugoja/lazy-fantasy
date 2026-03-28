'use client';

import { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { useRouter } from 'next/navigation';

interface AuthContextType {
    isAuthenticated: boolean;
    username: string | null;
    displayName: string | null;
    login: (token: string, username: string, displayName?: string | null) => void;
    logout: () => void;
    isLoading: boolean;
    setDisplayName: (name: string) => void;
}

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
    const [isAuthenticated, setIsAuthenticated] = useState(false);
    const [username, setUsername] = useState<string | null>(null);
    const [displayName, setDisplayNameState] = useState<string | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const router = useRouter();

    useEffect(() => {
        const token = localStorage.getItem('token');
        const storedUsername = localStorage.getItem('username');
        const storedDisplayName = localStorage.getItem('display_name');
        if (token && storedUsername) {
            setIsAuthenticated(true);
            setUsername(storedUsername);
            setDisplayNameState(storedDisplayName || null);
        }
        setIsLoading(false);
    }, []);

    const login = (token: string, username: string, displayName?: string | null) => {
        localStorage.setItem('token', token);
        localStorage.setItem('username', username);
        if (displayName) {
            localStorage.setItem('display_name', displayName);
        } else {
            localStorage.removeItem('display_name');
        }
        setIsAuthenticated(true);
        setUsername(username);
        setDisplayNameState(displayName ?? null);
    };

    const setDisplayName = (name: string) => {
        localStorage.setItem('display_name', name);
        setDisplayNameState(name);
    };

    const logout = () => {
        localStorage.removeItem('token');
        localStorage.removeItem('username');
        localStorage.removeItem('display_name');
        setIsAuthenticated(false);
        setUsername(null);
        setDisplayNameState(null);
        router.push('/login');
    };

    return (
        <AuthContext.Provider value={{ isAuthenticated, username, displayName, login, logout, isLoading, setDisplayName }}>
            {children}
        </AuthContext.Provider>
    );
}

export function useAuth() {
    const context = useContext(AuthContext);
    if (!context) {
        throw new Error('useAuth must be used within an AuthProvider');
    }
    return context;
}
