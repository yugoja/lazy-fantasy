'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { resetPassword, ApiError } from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Button } from '@/components/ui/button';

export default function ResetPasswordPage() {
  const [token, setToken] = useState('');
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [error, setError] = useState('');
  const [done, setDone] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const router = useRouter();

  useEffect(() => {
    const t = new URLSearchParams(window.location.search).get('token');
    if (t) setToken(t);
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    if (password.length < 8) { setError('Password must be at least 8 characters.'); return; }
    if (password !== confirm) { setError('Passwords do not match.'); return; }
    setIsLoading(true);
    try {
      await resetPassword(token, password);
      setDone(true);
      setTimeout(() => router.push('/login'), 1800);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not reset your password.');
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center px-4">
      <div className="w-full max-w-sm">
        <Card className="border-border bg-card">
          <CardHeader className="items-center text-center space-y-1 pb-2">
            <CardTitle className="text-xl">{done ? 'Password updated' : 'Choose a new password'}</CardTitle>
            <CardDescription className="mt-1">
              {done ? 'Redirecting you to sign in…' : 'Make it at least 8 characters'}
            </CardDescription>
          </CardHeader>
          <CardContent className="pt-4">
            {done ? (
              <div className="text-center space-y-4">
                <p className="text-sm text-muted-foreground">Your password has been changed. You can now sign in with it.</p>
                <Link href="/login" className="inline-block text-sm text-primary hover:underline font-medium">Go to sign in</Link>
              </div>
            ) : !token ? (
              <div className="text-center space-y-4">
                <p className="text-sm text-muted-foreground">This reset link is missing its token. Request a new one.</p>
                <Link href="/forgot-password" className="inline-block text-sm text-primary hover:underline font-medium">Request a reset link</Link>
              </div>
            ) : (
              <form onSubmit={handleSubmit} className="space-y-4">
                {error && (
                  <Card className="p-3 border-destructive/50 bg-destructive/10">
                    <p className="text-sm text-destructive">{error}</p>
                  </Card>
                )}
                <div className="space-y-2">
                  <Label htmlFor="password">New password</Label>
                  <Input id="password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="New password" required />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="confirm">Confirm password</Label>
                  <Input id="confirm" type="password" value={confirm} onChange={(e) => setConfirm(e.target.value)} placeholder="Re-enter password" required />
                </div>
                <Button type="submit" className="w-full" disabled={isLoading}>
                  {isLoading ? 'Updating…' : 'Update password'}
                </Button>
              </form>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
