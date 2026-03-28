'use client';

import { useEffect, useState } from 'react';
import { useRouter, useParams } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@/lib/auth';
import { getLeaguePreview, joinLeague, ApiError } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Shield, Users, LogIn, UserPlus, CheckCircle2 } from 'lucide-react';

interface LeaguePreview {
  name: string;
  invite_code: string;
  member_count: number;
}

export default function JoinLeaguePage() {
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const router = useRouter();
  const params = useParams();
  const code = (params.code as string).toUpperCase();

  const [preview, setPreview] = useState<LeaguePreview | null>(null);
  const [previewError, setPreviewError] = useState('');
  const [isJoining, setIsJoining] = useState(false);
  const [joinError, setJoinError] = useState('');
  const [joined, setJoined] = useState(false);

  // Persist the invite code in localStorage so it survives the auth redirect
  useEffect(() => {
    if (code) localStorage.setItem('pending_invite_code', code);
  }, [code]);

  // Fetch league preview (public — works before login)
  useEffect(() => {
    getLeaguePreview(code)
      .then(setPreview)
      .catch(() => setPreviewError('This invite link is invalid or has expired.'));
  }, [code]);

  // After login, if there's a pending invite code, auto-join
  useEffect(() => {
    if (!isAuthenticated || authLoading) return;
    const pending = localStorage.getItem('pending_invite_code');
    if (pending === code) handleJoin();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isAuthenticated, authLoading]);

  const handleJoin = async () => {
    setJoinError('');
    setIsJoining(true);
    try {
      const league = await joinLeague(code);
      localStorage.removeItem('pending_invite_code');
      setJoined(true);
      setTimeout(() => router.push(`/leagues/${league.id}`), 1200);
    } catch (e) {
      if (e instanceof ApiError && e.message.includes('already a member')) {
        // Already in — just navigate there
        const leagues = await import('@/lib/api').then(m => m.getMyLeagues());
        const existing = leagues.find(l => l.invite_code === code);
        localStorage.removeItem('pending_invite_code');
        if (existing) router.push(`/leagues/${existing.id}`);
        else router.push('/leagues');
      } else {
        setJoinError(e instanceof Error ? e.message : 'Failed to join league');
      }
    } finally {
      setIsJoining(false);
    }
  };

  const appUrl = process.env.NEXT_PUBLIC_APP_URL || 'https://lazyfantasy.app';
  const redirectParam = encodeURIComponent(`/join/${code}`);

  return (
    <div className="min-h-[100dvh] bg-background flex flex-col items-center justify-center px-6">
      <div className="w-full max-w-sm space-y-6">

        {/* Brand */}
        <div className="text-center">
          <p className="text-xs font-bold tracking-widest text-primary uppercase mb-6">Lazy Fantasy</p>
        </div>

        {/* League card */}
        {previewError ? (
          <div className="text-center space-y-3">
            <p className="text-muted-foreground text-sm">{previewError}</p>
            <Link href="/leagues">
              <Button variant="outline" className="w-full">Go to My Leagues</Button>
            </Link>
          </div>
        ) : (
          <div className="rounded-2xl border border-border bg-card p-6 space-y-4 text-center">
            <div className="mx-auto h-16 w-16 rounded-full bg-primary/10 flex items-center justify-center">
              <Shield className="h-8 w-8 text-primary" />
            </div>

            <div className="space-y-1">
              <p className="text-xs text-muted-foreground uppercase tracking-wide">You're invited to join</p>
              <h1 className="text-2xl font-bold">
                {preview?.name ?? <span className="text-muted-foreground/40">Loading…</span>}
              </h1>
              {preview && (
                <p className="text-sm text-muted-foreground flex items-center justify-center gap-1.5">
                  <Users className="h-3.5 w-3.5" />
                  {preview.member_count} member{preview.member_count !== 1 ? 's' : ''} playing
                </p>
              )}
            </div>

            {joined ? (
              <div className="flex items-center justify-center gap-2 text-primary font-semibold">
                <CheckCircle2 className="h-5 w-5" />
                Joined! Taking you there…
              </div>
            ) : isAuthenticated ? (
              <div className="space-y-2 pt-2">
                <Button
                  className="w-full"
                  onClick={handleJoin}
                  disabled={isJoining || !preview}
                >
                  {isJoining ? 'Joining…' : `Join ${preview?.name ?? 'League'}`}
                </Button>
                {joinError && <p className="text-xs text-destructive">{joinError}</p>}
              </div>
            ) : (
              <div className="space-y-2 pt-2">
                <Link href={`/signup?redirect=${redirectParam}`} className="block">
                  <Button className="w-full gap-2">
                    <UserPlus className="h-4 w-4" />
                    Sign up &amp; join
                  </Button>
                </Link>
                <Link href={`/login?redirect=${redirectParam}`} className="block">
                  <Button variant="outline" className="w-full gap-2">
                    <LogIn className="h-4 w-4" />
                    Log in &amp; join
                  </Button>
                </Link>
                <p className="text-xs text-muted-foreground pt-1">Free to play. Always.</p>
              </div>
            )}
          </div>
        )}

      </div>
    </div>
  );
}
