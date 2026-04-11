'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { login as apiLogin, ApiError } from '@/lib/api';
import { useAuth } from '@/lib/auth';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Button } from '@/components/ui/button';


import GoogleSignInButton from '@/components/GoogleSignInButton';

export default function LoginPage() {
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [redirectTo, setRedirectTo] = useState('/dashboard');
    const router = useRouter();
    const { login } = useAuth();

    useEffect(() => {
        const params = new URLSearchParams(window.location.search);
        const redirect = params.get('redirect');
        if (redirect) setRedirectTo(redirect);
    }, []);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError('');
        setIsLoading(true);

        try {
            const response = await apiLogin(username, password);
            login(response.access_token, username, response.display_name);
            router.push(redirectTo);
        } catch (err) {
            if (err instanceof ApiError) {
                setError(err.message);
            } else {
                setError('An unexpected error occurred');
            }
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="min-h-[100dvh] flex items-center justify-center bg-background px-4">
            <div className="container-mobile w-full max-w-sm">
                <Card className="border-border bg-card">
                    <CardHeader className="items-center text-center space-y-3 pb-2">
                        <div>
                            {/* eslint-disable-next-line @next/next/no-img-element */}
                            <img src="/icon.svg" alt="Lazy Fantasy" width={48} height={48} className="h-12 w-12" />
                        </div>
                        <div>
                            <CardTitle className="text-xl">Welcome back</CardTitle>
                            <CardDescription className="mt-1">Sign in to keep playing</CardDescription>
                        </div>
                    </CardHeader>
                    <CardContent className="pt-4">
                        {error && (
                            <Card className="p-3 mb-4 border-destructive/50 bg-destructive/10">
                                <p className="text-sm text-destructive">{error}</p>
                            </Card>
                        )}

                        <GoogleSignInButton onError={setError} redirectTo={redirectTo} />

                        <div className="relative my-4">
                            <div className="absolute inset-0 flex items-center">
                                <span className="w-full border-t border-border" />
                            </div>
                            <div className="relative flex justify-center text-xs uppercase">
                                <span className="bg-card px-2 text-muted-foreground">or</span>
                            </div>
                        </div>

                        <form onSubmit={handleSubmit} className="space-y-4">
                            <div className="space-y-2">
                                <Label htmlFor="username">Username</Label>
                                <Input
                                    id="username"
                                    type="text"
                                    value={username}
                                    onChange={(e) => setUsername(e.target.value)}
                                    placeholder="Enter your username"
                                    required
                                />
                            </div>

                            <div className="space-y-2">
                                <Label htmlFor="password">Password</Label>
                                <Input
                                    id="password"
                                    type="password"
                                    value={password}
                                    onChange={(e) => setPassword(e.target.value)}
                                    placeholder="Enter your password"
                                    required
                                />
                            </div>

                            <Button type="submit" className="w-full" disabled={isLoading}>
                                {isLoading ? 'Signing in...' : 'Sign In'}
                            </Button>
                        </form>

                        <p className="text-center text-sm text-muted-foreground mt-4">
                            Don&apos;t have an account?{' '}
                            <Link href={redirectTo !== '/dashboard' ? `/signup?redirect=${encodeURIComponent(redirectTo)}` : '/signup'} className="text-primary hover:underline font-medium">
                                Sign up
                            </Link>
                        </p>
                    </CardContent>
                </Card>
            </div>
        </div>
    );
}
