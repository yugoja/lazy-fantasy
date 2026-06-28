'use client';

import { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { useRouter } from 'next/navigation';
import { analytics } from '@/lib/analytics';

interface AuthContextType {
    isAuthenticated: boolean;
    username: string | null;
    displayName: string | null;
    avatarUrl: string | null;
    login: (token: string, username: string, displayName?: string | null) => void;
    logout: () => void;
    isLoading: boolean;
    setDisplayName: (name: string) => void;
    setAvatarUrl: (url: string | null) => void;
}

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
    const [isAuthenticated, setIsAuthenticated] = useState(false);
    const [username, setUsername] = useState<string | null>(null);
    const [displayName, setDisplayNameState] = useState<string | null>(null);
    const [avatarUrl, setAvatarUrlState] = useState<string | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const router = useRouter();

    useEffect(() => {
        const token = localStorage.getItem('token');
        const storedUsername = localStorage.getItem('username');
        const storedDisplayName = localStorage.getItem('display_name');
        const storedAvatarUrl = localStorage.getItem('avatar_url');
        if (token && storedUsername) {
            setIsAuthenticated(true);
            setUsername(storedUsername);
            setDisplayNameState(storedDisplayName || null);
            setAvatarUrlState(storedAvatarUrl || null);
            analytics.identify(storedUsername, { display_name: storedDisplayName || undefined });
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
        analytics.identify(username, { display_name: displayName ?? undefined });
    };

    const setDisplayName = (name: string) => {
        localStorage.setItem('display_name', name);
        setDisplayNameState(name);
    };

    const setAvatarUrl = (url: string | null) => {
        if (url) localStorage.setItem('avatar_url', url);
        else localStorage.removeItem('avatar_url');
        setAvatarUrlState(url);
    };

    const logout = () => {
        localStorage.removeItem('token');
        localStorage.removeItem('username');
        localStorage.removeItem('display_name');
        localStorage.removeItem('avatar_url');
        setIsAuthenticated(false);
        setUsername(null);
        setDisplayNameState(null);
        setAvatarUrlState(null);
        analytics.reset();
        router.push('/login');
    };

    return (
        <AuthContext.Provider value={{ isAuthenticated, username, displayName, avatarUrl, login, logout, isLoading, setDisplayName, setAvatarUrl }}>
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
