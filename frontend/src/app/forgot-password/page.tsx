'use client';

import { useState } from 'react';
import Link from 'next/link';
import { forgotPassword } from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Button } from '@/components/ui/button';

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState('');
  const [sent, setSent] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    // Endpoint never reveals whether the account exists; either way we show the
    // same confirmation.
    try { await forgotPassword(email); } catch { /* ignore */ } finally {
      setSent(true);
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center px-4">
      <div className="w-full max-w-sm">
        <Card className="border-border bg-card">
          <CardHeader className="items-center text-center space-y-1 pb-2">
            <CardTitle className="text-xl">Reset your password</CardTitle>
            <CardDescription className="mt-1">We&apos;ll email you a reset link</CardDescription>
          </CardHeader>
          <CardContent className="pt-4">
            {sent ? (
              <div className="text-center space-y-4">
                <p className="text-sm text-muted-foreground leading-relaxed">
                  If an account exists for{' '}
                  <span className="text-foreground font-medium break-all">{email}</span>, a reset
                  link is on its way. Check your inbox — and your spam folder.
                </p>
                <Link href="/login" className="inline-block text-sm text-primary hover:underline font-medium">
                  Back to sign in
                </Link>
              </div>
            ) : (
              <form onSubmit={handleSubmit} className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="email">Email</Label>
                  <Input
                    id="email"
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="you@example.com"
                    required
                  />
                </div>
                <Button type="submit" className="w-full" disabled={isLoading}>
                  {isLoading ? 'Sending…' : 'Send reset link'}
                </Button>
                <p className="text-center text-sm text-muted-foreground">
                  Remembered it?{' '}
                  <Link href="/login" className="text-primary hover:underline font-medium">Sign in</Link>
                </p>
              </form>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
