'use client';

import { Suspense, useEffect, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@/lib/auth';
import { getMyLeagues, joinLeague, createLeague, ApiError } from '@/lib/api';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog';
import { Shield, ChevronRight, LogIn, Plus, Copy, CheckCircle2, Share2 } from 'lucide-react';

interface League {
  id: number;
  name: string;
  invite_code: string;
  owner_id: number;
  sport?: string;
}

export default function LeaguesPage() {
  return (
    <Suspense>
      <LeaguesContent />
    </Suspense>
  );
}

function LeaguesContent() {
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const [leagues, setLeagues] = useState<League[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  // Dialog states
  const [joinOpen, setJoinOpen] = useState(false);
  const [createOpen, setCreateOpen] = useState(false);
  const [confirmOpen, setConfirmOpen] = useState(false);

  // Join form
  const [joinCode, setJoinCode] = useState('');
  const [joinError, setJoinError] = useState('');
  const [joinLoading, setJoinLoading] = useState(false);

  // Create form
  const [leagueName, setLeagueName] = useState('');
  const leagueSport = 'cricket';
  const [createError, setCreateError] = useState('');
  const [createLoading, setCreateLoading] = useState(false);

  // Created league info
  const [createdLeague, setCreatedLeague] = useState<League | null>(null);
  const [copied, setCopied] = useState(false);
  const [copiedLeagueId, setCopiedLeagueId] = useState<number | null>(null);
  const [loadError, setLoadError] = useState('');

  const getInviteLink = (code: string) => {
    if (typeof window === 'undefined') return code;
    return `${window.location.origin}/leagues?join=${code}`;
  };

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      const joinCode = searchParams.get('join');
      const redirect = joinCode
        ? `/login?redirect=${encodeURIComponent(`/leagues?join=${joinCode}`)}`
        : '/login';
      router.push(redirect);
    }
  }, [isAuthenticated, authLoading, router, searchParams]);

  useEffect(() => {
    if (isAuthenticated) {
      loadLeagues();
    }
  }, [isAuthenticated]);

  // Auto-open join dialog if ?join=CODE is in URL
  useEffect(() => {
    const code = searchParams.get('join');
    if (code && isAuthenticated) {
      setJoinCode(code.toUpperCase());
      setJoinOpen(true);
    }
  }, [searchParams, isAuthenticated]);

  const loadLeagues = async () => {
    try {
      const data = await getMyLeagues();
      setLeagues(data);
    } catch {
      setLoadError('Failed to load leagues');
    } finally {
      setIsLoading(false);
    }
  };

  const handleJoin = async () => {
    setJoinError('');
    if (!joinCode.trim()) {
      setJoinError('Please enter a league code');
      return;
    }

    setJoinLoading(true);
    try {
      const newLeague = await joinLeague(joinCode.trim().toUpperCase());
      setLeagues(prev => [...prev, newLeague]);
      setJoinOpen(false);
      setJoinCode('');
    } catch (err) {
      if (err instanceof ApiError) {
        setJoinError(err.message);
      } else {
        setJoinError('Failed to join league');
      }
    } finally {
      setJoinLoading(false);
    }
  };

  const handleCreate = async () => {
    setCreateError('');
    if (!leagueName.trim()) {
      setCreateError('Please enter a league name');
      return;
    }

    setCreateLoading(true);
    try {
      const league = await createLeague(leagueName.trim(), leagueSport);
      setLeagues(prev => [...prev, league]);
      setCreatedLeague(league);
      setCreateOpen(false);
      setConfirmOpen(true);
      setLeagueName('');
    } catch (err) {
      if (err instanceof ApiError) {
        setCreateError(err.message);
      } else {
        setCreateError('Failed to create league');
      }
    } finally {
      setCreateLoading(false);
    }
  };

  const copyInviteLink = (code: string, leagueId?: number) => {
    navigator.clipboard.writeText(getInviteLink(code));
    if (leagueId) {
      setCopiedLeagueId(leagueId);
      setTimeout(() => setCopiedLeagueId(null), 2000);
    } else {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  if (authLoading || isLoading) {
    return (
      <div className="container-mobile py-6 space-y-6">
        <div className="flex items-start justify-between">
          <div className="space-y-2">
            <Skeleton className="h-8 w-36" />
            <Skeleton className="h-4 w-52" />
          </div>
          <div className="flex gap-2">
            <Skeleton className="h-9 w-16" />
            <Skeleton className="h-9 w-24" />
          </div>
        </div>
        <Skeleton className="h-6 w-20" />
        <div className="space-y-3">
          {[...Array(3)].map((_, i) => (
            <Skeleton key={i} className="h-28" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="container-mobile py-6 space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold">My Leagues</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Create or join leagues to compete.
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={() => setJoinOpen(true)}>
            <LogIn className="h-4 w-4 mr-1.5" />
            Join
          </Button>
          <Button size="sm" onClick={() => setCreateOpen(true)}>
            <Plus className="h-4 w-4 mr-1.5" />
            Create
          </Button>
        </div>
      </div>

      {/* League Count */}
      <Badge variant="secondary" className="text-xs">
        {leagues.length} League{leagues.length !== 1 ? 's' : ''}
      </Badge>

      {/* Error */}
      {loadError && (
        <Card className="p-3 border-destructive/50 bg-destructive/10">
          <p className="text-sm text-destructive">{loadError}</p>
        </Card>
      )}

      {/* League Cards */}
      {leagues.length === 0 ? (
        <Card className="p-8 text-center space-y-3">
          <p className="text-sm text-muted-foreground">You haven&apos;t joined any leagues yet</p>
          <p className="text-xs text-muted-foreground">Create a new league or join one with an invite code</p>
        </Card>
      ) : (
        <div className="space-y-3">
          {leagues.map((league) => (
            <Card key={league.id} className="p-4 hover:border-primary/50 transition-colors">
              <div className="flex items-center gap-3">
                <div className="h-10 w-10 rounded-lg bg-primary/10 flex items-center justify-center shrink-0">
                  <Shield className="h-5 w-5 text-primary" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-sm">{league.name}</span>
                    <Badge variant="outline" className="text-[9px] px-1.5 py-0">
                      🏏
                    </Badge>
                  </div>
                  <div className="flex items-center gap-2 mt-1">
                    <Badge variant="outline" className="text-[10px]">
                      {league.invite_code}
                    </Badge>
                    <button
                      onClick={(e) => {
                        e.preventDefault();
                        copyInviteLink(league.invite_code, league.id);
                      }}
                      className="inline-flex items-center gap-1 text-[10px] text-muted-foreground hover:text-primary transition-colors"
                      aria-label="Copy invite link"
                    >
                      {copiedLeagueId === league.id ? (
                        <><CheckCircle2 className="h-3 w-3 text-primary" /> Copied!</>
                      ) : (
                        <><Share2 className="h-3 w-3" /> Share</>
                      )}
                    </button>
                  </div>
                </div>
                <Link href={`/leaderboard?league=${league.id}`} className="flex items-center gap-1 text-primary text-xs font-medium">
                  Board
                  <ChevronRight className="h-4 w-4" />
                </Link>
              </div>
            </Card>
          ))}
        </div>
      )}

      {/* Join League Dialog */}
      <Dialog open={joinOpen} onOpenChange={setJoinOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Join a League</DialogTitle>
            <DialogDescription>
              Enter the league code shared with you.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="join-code">League Code</Label>
              <Input
                id="join-code"
                placeholder="e.g., OFC-2026-XK9"
                value={joinCode}
                onChange={(e) => setJoinCode(e.target.value.toUpperCase())}
                maxLength={20}
              />
            </div>
            {joinError && (
              <p className="text-sm text-destructive">{joinError}</p>
            )}
            <Button
              className="w-full"
              onClick={handleJoin}
              disabled={joinLoading}
            >
              {joinLoading ? 'Joining...' : 'Join League'}
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* Create League Dialog */}
      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Create a New League</DialogTitle>
            <DialogDescription>
              Set up your league and invite friends.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="league-name">League Name</Label>
              <Input
                id="league-name"
                placeholder="e.g., Office Squad"
                value={leagueName}
                onChange={(e) => setLeagueName(e.target.value)}
                maxLength={100}
              />
            </div>
            {createError && (
              <p className="text-sm text-destructive">{createError}</p>
            )}
            <Button
              className="w-full"
              onClick={handleCreate}
              disabled={createLoading}
            >
              {createLoading ? 'Creating...' : 'Create League'}
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* League Created Confirmation Dialog */}
      <Dialog open={confirmOpen} onOpenChange={setConfirmOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader className="items-center text-center">
            <DialogTitle className="text-xl">League Created!</DialogTitle>
            <DialogDescription>
              Share the code below to invite friends.
            </DialogDescription>
          </DialogHeader>
          {createdLeague && (
            <div className="space-y-4">
              {/* Invite Code Display */}
              <div className="rounded-lg bg-primary/10 border border-primary/30 p-4 text-center">
                <p className="text-xs text-muted-foreground mb-1">League Code</p>
                <p className="text-2xl font-bold text-primary tracking-wider">
                  {createdLeague.invite_code}
                </p>
              </div>

              {/* Copy Link */}
              <div className="space-y-2">
                <Label className="text-xs text-muted-foreground">Invite Link</Label>
                <div className="flex items-center gap-2">
                  <Input
                    readOnly
                    value={getInviteLink(createdLeague.invite_code)}
                    className="text-sm text-xs"
                  />
                  <Button
                    variant="outline"
                    size="icon"
                    onClick={() => copyInviteLink(createdLeague.invite_code)}
                    aria-label="Copy invite link"
                  >
                    {copied ? (
                      <CheckCircle2 className="h-4 w-4 text-primary" />
                    ) : (
                      <Copy className="h-4 w-4" />
                    )}
                  </Button>
                </div>
              </div>

              <p className="text-xs text-muted-foreground text-center">
                Share this link to invite friends to <strong>{createdLeague.name}</strong>
              </p>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
