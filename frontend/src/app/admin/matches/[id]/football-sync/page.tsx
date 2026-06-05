'use client';

import { useEffect, useState } from 'react';
import { useRouter, useParams } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@/lib/auth';
import { API_BASE } from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { ArrowLeft, Link2, RefreshCw, AlertTriangle, CheckCircle2, Clock } from 'lucide-react';
import FootballResultForm from '@/components/admin/FootballResultForm';

interface MatchInfo {
  id: number;
  team_1: { id: number; name: string; short_name: string };
  team_2: { id: number; name: string; short_name: string };
  external_match_id: string | null;
  sync_state: string;
  sync_error: string | null;
  last_synced_at: string | null;
  status: string;
}

interface Player {
  id: number;
  name: string;
  role: string;
  team_id: number;
}

interface SyncResult {
  status: string;
  predictions_processed: number;
  unresolved_players: string[];
  sync_error: string | null;
  sync_state: string;
  last_synced_at: string | null;
}

const STATE_BADGE: Record<string, { label: string; className: string }> = {
  unlinked:      { label: 'Unlinked',      className: 'bg-muted text-muted-foreground border-border' },
  linked:        { label: 'Linked',        className: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30' },
  result_synced: { label: 'Result Synced', className: 'bg-green-500/20 text-green-400 border-green-500/30' },
};

export default function FootballSyncPage() {
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const router = useRouter();
  const params = useParams();
  const matchId = Number(params.id);

  const [match, setMatch] = useState<MatchInfo | null>(null);
  const [team1Players, setTeam1Players] = useState<Player[]>([]);
  const [team2Players, setTeam2Players] = useState<Player[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  const [fixtureId, setFixtureId] = useState('');
  const [isLinking, setIsLinking] = useState(false);
  const [linkError, setLinkError] = useState('');

  const [isSyncing, setIsSyncing] = useState(false);
  const [syncResult, setSyncResult] = useState<SyncResult | null>(null);
  const [syncError, setSyncError] = useState('');

  const [successMessage, setSuccessMessage] = useState('');

  useEffect(() => {
    if (!authLoading && !isAuthenticated) router.push('/login');
  }, [isAuthenticated, authLoading, router]);

  useEffect(() => {
    if (matchId && isAuthenticated) loadData();
  }, [matchId, isAuthenticated]);

  const authHeaders = () => ({
    Authorization: `Bearer ${localStorage.getItem('token')}`,
    'Content-Type': 'application/json',
  });

  const loadData = async () => {
    try {
      const [matchesResp, squadResp] = await Promise.all([
        fetch(`${API_BASE}/admin/matches`, { headers: authHeaders() }),
        fetch(`${API_BASE}/admin/matches/${matchId}/squad`, { headers: authHeaders() }),
      ]);
      if (!matchesResp.ok || !squadResp.ok) throw new Error('Failed to load match data');

      const matches: MatchInfo[] = await matchesResp.json();
      const squad = await squadResp.json();

      const m = matches.find((x) => x.id === matchId);
      if (!m) throw new Error('Match not found');
      setMatch(m);
      if (m.external_match_id) setFixtureId(m.external_match_id);

      setTeam1Players(squad.team_1_players ?? []);
      setTeam2Players(squad.team_2_players ?? []);
    } catch {
      // handled by null match check below
    } finally {
      setIsLoading(false);
    }
  };

  const handleLink = async () => {
    setLinkError('');
    setIsLinking(true);
    try {
      const resp = await fetch(`${API_BASE}/admin/matches/${matchId}/link-football`, {
        method: 'POST',
        headers: authHeaders(),
        body: JSON.stringify({ fixture_id: parseInt(fixtureId) }),
      });
      if (!resp.ok) {
        const data = await resp.json();
        throw new Error(data.detail || 'Failed to link');
      }
      await loadData();
    } catch (err) {
      setLinkError(err instanceof Error ? err.message : 'Failed to link');
    } finally {
      setIsLinking(false);
    }
  };

  const handleSync = async () => {
    setSyncError('');
    setSyncResult(null);
    setIsSyncing(true);
    try {
      const resp = await fetch(`${API_BASE}/admin/matches/${matchId}/sync-football`, {
        method: 'POST',
        headers: authHeaders(),
      });
      const data = await resp.json();
      if (!resp.ok) throw new Error(data.detail || 'Sync failed');
      setSyncResult(data);
      await loadData();
    } catch (err) {
      setSyncError(err instanceof Error ? err.message : 'Sync failed');
    } finally {
      setIsSyncing(false);
    }
  };

  const handleManualSuccess = (predictionsProcessed: number) => {
    setSuccessMessage(`Manual result saved — ${predictionsProcessed} predictions scored.`);
    loadData();
  };

  if (authLoading || isLoading) {
    return (
      <div className="container-mobile py-6 space-y-4">
        <Skeleton className="h-6 w-24" />
        <Skeleton className="h-8 w-64" />
        {[...Array(3)].map((_, i) => <Skeleton key={i} className="h-24 w-full" />)}
      </div>
    );
  }

  if (!match) {
    return (
      <div className="container-mobile py-6">
        <Card className="p-6 text-center">
          <p className="text-sm text-destructive">Match not found</p>
          <Link href="/admin"><Button variant="outline" size="sm" className="mt-3"><ArrowLeft className="h-4 w-4 mr-2" />Back</Button></Link>
        </Card>
      </div>
    );
  }

  const stateBadge = STATE_BADGE[match.sync_state] ?? STATE_BADGE.unlinked;

  return (
    <div className="container-mobile py-6 space-y-5">
      <Link href="/admin" className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors">
        <ArrowLeft className="h-4 w-4" />
        Back to Admin
      </Link>

      <div>
        <h1 className="text-xl font-bold">Football Sync</h1>
        <p className="text-xs text-muted-foreground mt-1">
          {match.team_1.name} vs {match.team_2.name}
        </p>
      </div>

      {successMessage && (
        <Card className="p-3 border-green-500/50 bg-green-500/10">
          <p className="text-sm text-green-400">{successMessage}</p>
        </Card>
      )}

      {/* 1. Sync Status */}
      <Card className="border-border bg-card">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm flex items-center gap-2">
            <Clock className="h-4 w-4 text-muted-foreground" />
            Sync Status
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          <div className="flex items-center gap-2 flex-wrap">
            <span className={`inline-flex items-center gap-1 text-[10px] px-1.5 py-0.5 rounded border ${stateBadge.className}`}>
              {stateBadge.label}
            </span>
            {match.external_match_id && (
              <Badge variant="outline" className="text-[10px]">
                Fixture #{match.external_match_id}
              </Badge>
            )}
          </div>
          {match.last_synced_at && (
            <p className="text-[10px] text-muted-foreground">
              Last synced: {new Date(match.last_synced_at).toLocaleString()}
            </p>
          )}
          {match.sync_error && (
            <div className="flex items-start gap-1.5 bg-orange-500/10 border border-orange-500/30 rounded px-2 py-1.5">
              <AlertTriangle className="h-3 w-3 text-orange-400 shrink-0 mt-0.5" />
              <p className="text-[10px] text-orange-300">{match.sync_error}</p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* 2. Link Fixture */}
      <Card className="border-border bg-card">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm flex items-center gap-2">
            <Link2 className="h-4 w-4 text-muted-foreground" />
            Link Fixture
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="space-y-1.5">
            <Label className="text-xs">api-football.com Fixture ID</Label>
            <div className="flex gap-2">
              <Input
                type="number"
                placeholder="e.g. 1234567"
                value={fixtureId}
                onChange={(e) => setFixtureId(e.target.value)}
                className="h-8 text-sm"
              />
              <Button
                size="sm"
                variant="secondary"
                onClick={handleLink}
                disabled={isLinking || !fixtureId}
                className="shrink-0"
              >
                {isLinking ? 'Linking…' : 'Link'}
              </Button>
            </div>
          </div>
          {linkError && (
            <p className="text-xs text-destructive">{linkError}</p>
          )}
        </CardContent>
      </Card>

      {/* 3. Sync from API — only when linked */}
      {match.external_match_id && (
        <Card className="border-border bg-card">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm flex items-center gap-2">
              <RefreshCw className="h-4 w-4 text-muted-foreground" />
              Sync from API
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <p className="text-xs text-muted-foreground">
              Fetches scoreline + per-player stats from api-football.com and scores all predictions.
            </p>
            <Button
              size="sm"
              onClick={handleSync}
              disabled={isSyncing}
              className="w-full"
            >
              {isSyncing ? (
                <><RefreshCw className="h-3.5 w-3.5 mr-2 animate-spin" />Syncing…</>
              ) : (
                'Sync Results'
              )}
            </Button>
            {syncError && (
              <p className="text-xs text-destructive bg-destructive/10 rounded px-2 py-1">{syncError}</p>
            )}
            {syncResult && (
              <div className="space-y-1.5">
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="h-3.5 w-3.5 text-green-400" />
                  <span className="text-xs text-green-400">
                    {syncResult.status === 'not_finished'
                      ? 'Match not finished yet'
                      : `Synced — ${syncResult.predictions_processed} predictions scored`}
                  </span>
                </div>
                {syncResult.unresolved_players.length > 0 && (
                  <div className="bg-orange-500/10 border border-orange-500/30 rounded px-2 py-1.5 space-y-1">
                    <p className="text-[10px] font-semibold text-orange-400">
                      {syncResult.unresolved_players.length} unresolved player{syncResult.unresolved_players.length > 1 ? 's' : ''}
                    </p>
                    {syncResult.unresolved_players.map((name) => (
                      <p key={name} className="text-[10px] text-orange-300">{name}</p>
                    ))}
                    <p className="text-[10px] text-muted-foreground">Use Manual Override below to fill in their stats.</p>
                  </div>
                )}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* 4. Manual Override */}
      <FootballResultForm
        matchId={matchId}
        team1={match.team_1}
        team2={match.team_2}
        team1Players={team1Players}
        team2Players={team2Players}
        onSuccess={handleManualSuccess}
      />
    </div>
  );
}
